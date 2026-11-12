"""Verificacion y copia de los shapefiles."""
from __future__ import annotations

import shutil
from pathlib import Path

from cli.core import sql, ui
from cli.core.paths import rel

from .capas import CAPAS, EXTENSIONES, carpeta, leer_cabecera

# San Ignacio de Velasco aprox.: lon -61.2..-60.7, lat -16.6..-16.2
ZONA = (-62.0, -17.5, -60.0, -15.5)


def verificar() -> bool:
    """Comprueba archivos, WGS 84, tipo de geometria, extension y campos."""
    base = carpeta()
    ui.info(f"Carpeta: {rel(base)}")
    if not base.exists():
        ui.error("La carpeta no existe. Copie las capas (arquis bd capas copiar) o ajuste SHP_DIR.")
        return False
    todo_ok = True
    filas = []
    for capa in CAPAS:
        p = base / capa.archivo
        faltan = [e for e in EXTENSIONES[:3] if not p.with_suffix(e).exists()]
        if faltan:
            filas.append([capa.clave, "-", "-", ui.c("faltan " + " ".join(faltan), ui.C.RED)])
            todo_ok = False
            continue
        try:
            cab = leer_cabecera(p)
        except Exception as e:  # noqa: BLE001
            filas.append([capa.clave, "-", "-", ui.c(str(e), ui.C.RED)])
            todo_ok = False
            continue
        avisos = []
        if cab.prj and "WGS" not in cab.prj.upper() and "4326" not in cab.prj:
            avisos.append("PRJ no es WGS84")
        if not cab.prj:
            avisos.append("sin .prj")
        x0, y0, x1, y1 = cab.bbox
        if not (ZONA[0] <= x0 and x1 <= ZONA[2] and ZONA[1] <= y0 and y1 <= ZONA[3]):
            avisos.append(f"extension fuera de zona ({x0:.3f},{y0:.3f})")
        esperado = {"Polygon": "Polygon", "Point": "Point", "LineString": "PolyLine"}[capa.tipo]
        if not cab.tipo.startswith(esperado):
            avisos.append(f"tipo {cab.tipo} ≠ {esperado}")
        campos_lower = {c.lower() for c in cab.campos}
        sin = [c for c, _, _ in capa.campos if c.lower() not in campos_lower]
        if sin:
            avisos.append("sin campos: " + ",".join(sin))
        estado = ui.c("ok", ui.C.GREEN) if not avisos else ui.c("; ".join(avisos), ui.C.YELLOW)
        filas.append([capa.clave, cab.tipo, f"{cab.registros:,}".replace(",", "."), estado])
    ui.tabla(filas, ["Capa", "Tipo", "Registros", "Estado"])
    return todo_ok


def detalle() -> None:
    """Campos y metadatos de cada capa."""
    for capa in CAPAS:
        p = carpeta() / capa.archivo
        if not p.with_suffix(".shp").exists():
            continue
        cab = leer_cabecera(p)
        ui.seccion(f"{capa.clave} ({p.name})")
        ui.info(f"Tipo {cab.tipo} · {cab.registros} registros · codificacion {cab.cpg or '?'}")
        ui.info("BBox: " + ", ".join(f"{v:.6f}" for v in cab.bbox))
        ui.info("Campos: " + ", ".join(cab.campos))


def copiar() -> None:
    """Copia las capas desde otra carpeta (USB, descarga) a SHP_DIR."""
    origen = Path(ui.preguntar("Carpeta de origen con los .shp"))
    if not origen.is_dir():
        raise ui.Fallo("Carpeta invalida.")
    destino = carpeta()
    destino.mkdir(parents=True, exist_ok=True)
    n = 0
    for capa in CAPAS:
        for ext in EXTENSIONES:
            src = next(iter(origen.rglob(capa.archivo + ext)), None)
            if src:
                shutil.copy2(src, destino / src.name)
                n += 1
    ui.ok(f"{n} archivos copiados a {rel(destino)}")
    verificar()


def comparar() -> None:
    """Compara registros del SHP contra filas en la base."""
    filas = []
    for capa in CAPAS:
        p = carpeta() / capa.archivo
        shp = leer_cabecera(p).registros if p.with_suffix(".shp").exists() else None
        try:
            bd = int(sql.escalar(f"SELECT COUNT(*) FROM {capa.tabla}") or 0)
        except ui.Fallo:
            bd = None
        estado = ui.c("igual", ui.C.GREEN) if shp == bd else ui.c("difiere", ui.C.YELLOW)
        filas.append([capa.clave, shp if shp is not None else "-", bd if bd is not None else "-", estado])
    ui.tabla(filas, ["Capa", "SHP", "Base", ""])
