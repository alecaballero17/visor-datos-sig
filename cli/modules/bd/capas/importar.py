"""Importa los shapefiles a SQL Server (pyshp + sqlcmd).

Replica el mapeo de Data/Seeders/GeoDataSeeder.cs. Las geometrias se corrigen
en el servidor: MakeValid y, para columnas geography, se normaliza la
orientacion de los anillos (truco STUnion con el punto inicial) y se reorienta
si la envolvente supera el hemisferio.
"""
from __future__ import annotations

from pathlib import Path

from cli.core import sql, ui
from cli.core.paths import TMP_DIR, asegurar

from .capas import CAPAS, POR_CLAVE, Capa, carpeta
from .espacial import indices, vincular

LOTE = 150


def _shapefile():
    try:
        import shapefile  # pyshp
        return shapefile
    except ImportError:
        raise ui.Fallo("Falta pyshp. Ejecute: arquis deps pip-cli  (y use arquis.cmd, que usa .venv)")


def _wkt(geo: dict) -> str | None:
    t, c = geo.get("type"), geo.get("coordinates")
    if not c:
        return None
    pt = lambda p: f"{p[0]:.9f} {p[1]:.9f}"
    linea = lambda ps: "(" + ", ".join(pt(p) for p in ps) + ")"
    poli = lambda rs: "(" + ", ".join(linea(r) for r in rs) + ")"
    if t == "Point":
        return f"POINT ({pt(c)})"
    if t == "MultiPoint":
        return "MULTIPOINT (" + ", ".join(f"({pt(p)})" for p in c) + ")"
    if t == "LineString":
        return "LINESTRING " + linea(c)
    if t == "MultiLineString":
        return "MULTILINESTRING (" + ", ".join(linea(l) for l in c) + ")"
    if t == "Polygon":
        return "POLYGON " + poli(c)
    if t == "MultiPolygon":
        return "MULTIPOLYGON (" + ", ".join(poli(p) for p in c) + ")"
    return None


def _valor(v, tipo: str) -> str:
    if v is None:
        return "NULL"
    texto = str(v).strip()
    if texto == "" or texto.lower() == "none":
        return "NULL"
    if tipo == "int":
        try:
            return str(int(float(texto)))
        except ValueError:
            return "NULL"
    return f"N'{sql.lit(texto)}'"


def _tipo_columna(tabla: str) -> str:
    return sql.escalar(f"""SELECT TYPE_NAME(c.user_type_id) FROM sys.columns c
                           WHERE c.object_id = OBJECT_ID(N'{tabla}') AND c.name = 'Geom'""") or "geography"


def _expr_geom(tipo_col: str) -> tuple[str, str]:
    """(CROSS APPLY, expresion final)."""
    if tipo_col == "geometry":
        return "CROSS APPLY (SELECT geometry::STGeomFromText(v.Wkt, 4326).MakeValid() AS G) g", "g.G"
    return ("CROSS APPLY (SELECT geometry::STGeomFromText(v.Wkt, 4326).MakeValid() AS G0) g0 "
            "CROSS APPLY (SELECT geography::STGeomFromWKB(g0.G0.STUnion(g0.G0.STStartPoint()).STAsBinary(), 4326) AS G1) g1",
            "CASE WHEN g1.G1.EnvelopeAngle() > 90 THEN g1.G1.ReorientObject() ELSE g1.G1 END")


def generar_sql(capa: Capa, destino: Path) -> int:
    shapefile = _shapefile()
    base = carpeta() / capa.archivo
    cpg = base.with_suffix(".cpg")
    codificacion = cpg.read_text().strip() if cpg.exists() else "utf-8"
    if codificacion.upper() in ("UTF8", "UTF-8"):
        codificacion = "utf-8"
    r = shapefile.Reader(str(base), encoding=codificacion, encodingErrors="replace")
    nombres = [f[0] for f in r.fields[1:]]
    idx = {n.lower(): i for i, n in enumerate(nombres)}
    cols = [col for _, col, _ in capa.campos]
    es_punto = capa.tipo == "Point"
    if es_punto:
        cols += ["Longitud", "Latitud"]
    apply_, expr = _expr_geom(_tipo_columna(capa.tabla))
    extra_c = "".join(f", {c}" for c, _ in capa.extra_cols)
    extra_v = "".join(f", {e}" for _, e in capa.extra_cols)
    total = 0
    filas: list[str] = []
    with destino.open("w", encoding="utf-8") as f:
        f.write("SET NOCOUNT ON;\nSET XACT_ABORT ON;\nGO\n")

        def volcar():
            if not filas:
                return
            v_cols = ", ".join(cols + ["Wkt"])
            f.write(f"INSERT INTO {capa.tabla} ({', '.join(cols)}{extra_c}, Geom)\n"
                    f"SELECT {', '.join('v.' + c for c in cols)}{extra_v}, {expr}\n"
                    f"FROM (VALUES\n  " + ",\n  ".join(filas) + f"\n) AS v({v_cols})\n{apply_};\nGO\n")
            filas.clear()

        for sr in r.iterShapeRecords():
            wkt = _wkt(sr.shape.__geo_interface__) if sr.shape.shapeType != 0 else None
            if not wkt:
                continue
            rec = list(sr.record)
            valores = [_valor(rec[idx[c.lower()]] if c.lower() in idx else None, t) for c, _, t in capa.campos]
            if es_punto:
                x, y = sr.shape.points[0][:2]
                valores += [f"{x:.9f}", f"{y:.9f}"]
            filas.append("(" + ", ".join(valores + [f"N'{wkt}'"]) + ")")
            total += 1
            if len(filas) >= LOTE:
                volcar()
        volcar()
    return total


def importar(claves: list[str] | None = None, reemplazar: bool | None = None) -> None:
    """Importa las capas a la base (por defecto solo las tablas vacias)."""
    if not sql.existe_base():
        raise ui.Fallo("La base no existe. Ejecute: arquis bd inicializar")
    capas = [POR_CLAVE[k] for k in claves] if claves else CAPAS
    if reemplazar is None:
        reemplazar = ui.elegir("Si la tabla ya tiene datos", ["Omitirla (seguro)", "Vaciarla y reimportar"]) == 1
    if reemplazar and not ui.confirmar_peligro(
            "Vaciar tablas borra estados de servicio, vinculos de rutas, etc.", "REEMPLAZAR"):
        return
    asegurar(TMP_DIR)
    if reemplazar:
        # orden por claves foraneas: hijos primero
        for capa in sorted(capas, key=lambda c: ["codigosfijos", "lotes", "manzanas", "vias"].index(c.clave)):
            sql.ejecutar(f"DELETE FROM {capa.tabla}", mostrar=False)
            ui.info(f"{capa.tabla} vaciada.")
    importadas = 0
    for capa in capas:
        if not (carpeta() / f"{capa.archivo}.shp").exists():
            ui.warn(f"{capa.clave}: no se encontro {capa.archivo}.shp")
            continue
        existentes = int(sql.escalar(f"SELECT COUNT(*) FROM {capa.tabla}") or 0)
        if existentes and not reemplazar:
            ui.info(f"{capa.clave}: ya tiene {existentes} filas, se omite.")
            continue
        destino = TMP_DIR / f"importar-{capa.clave}.sql"
        ui.info(f"{capa.clave}: generando SQL...")
        n = generar_sql(capa, destino)
        ui.info(f"{capa.clave}: insertando {n} registros...")
        sql.archivo(destino)
        destino.unlink(missing_ok=True)
        ui.ok(f"{capa.clave}: {sql.escalar(f'SELECT COUNT(*) FROM {capa.tabla}')} filas en {capa.tabla}")
        importadas += 1
    if importadas:
        ui.info("Creando indices espaciales (aceleran la vinculacion)...")
        indices(usar_sp=False)
        vincular()


def importar_una() -> None:
    """Importa una sola capa."""
    i = ui.elegir("Capa", [c.clave for c in CAPAS])
    importar([CAPAS[i].clave])
