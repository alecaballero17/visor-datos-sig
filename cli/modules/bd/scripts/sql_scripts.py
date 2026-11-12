"""Scripts SQL manuales de 02_BaseDatos/ con control de cuales se ejecutaron.

Se registra cada ejecucion en dbo.__ArquisScripts (nombre + checksum) para no
repetirlos y detectar si un script cambio despues de aplicarse.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from cli.core import sql, ui
from cli.core.paths import SQL_SCRIPTS, TESTS, rel

TABLA = "dbo.__ArquisScripts"
# 01_CrearBD crea el esquema legado (geometry); en bases gestionadas por EF (geography) no aplica.
LEGADO = {"01_CrearBD.sql"}


def _asegurar_tabla() -> None:
    sql.ejecutar(f"""IF OBJECT_ID(N'{TABLA}') IS NULL
        CREATE TABLE {TABLA}(Nombre nvarchar(260) NOT NULL PRIMARY KEY, Checksum char(64) NOT NULL,
                             Fecha datetime2 NOT NULL DEFAULT SYSDATETIME(), Usuario nvarchar(128) NOT NULL DEFAULT SUSER_SNAME());""",
                 mostrar=False)


def _scripts() -> list[Path]:
    return sorted(SQL_SCRIPTS.glob("*.sql"))


def _checksum(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _aplicados() -> dict[str, str]:
    if not sql.existe_base():
        return {}
    _asegurar_tabla()
    return {f[0]: f[1] for f in sql.filas(f"SELECT Nombre, Checksum FROM {TABLA}")}


def _gestionada_por_ef() -> bool:
    return sql.existe_base() and sql.escalar("SELECT CASE WHEN OBJECT_ID(N'dbo.__EFMigrationsHistory') IS NULL THEN 0 ELSE 1 END") == "1"


def listar() -> None:
    """Scripts disponibles y su estado."""
    aplicados = _aplicados()
    filas = []
    for p in _scripts():
        if p.name in aplicados:
            estado = ui.c("aplicado", ui.C.GREEN) if aplicados[p.name] == _checksum(p) else ui.c("modificado", ui.C.YELLOW)
        else:
            estado = ui.c("pendiente", ui.C.GRAY)
        if p.name in LEGADO:
            estado += ui.c(" (legado)", ui.C.GRAY)
        filas.append([p.name, f"{p.stat().st_size / 1024:.1f} KB", estado])
    ui.tabla(filas, ["Script", "Tamano", "Estado"])
    if _gestionada_por_ef():
        ui.info("La base esta gestionada por migraciones EF; los scripts son complementarios.")


def _ejecutar(p: Path) -> None:
    ui.info(f"Ejecutando {p.name}...")
    salida = sql.archivo(p)
    if salida.strip():
        for linea in salida.strip().splitlines()[-8:]:
            ui.dim(linea)
    sql.ejecutar(f"""MERGE {TABLA} AS t USING (SELECT N'{sql.lit(p.name)}' AS Nombre) s ON t.Nombre = s.Nombre
        WHEN MATCHED THEN UPDATE SET Checksum = '{_checksum(p)}', Fecha = SYSDATETIME()
        WHEN NOT MATCHED THEN INSERT (Nombre, Checksum) VALUES (s.Nombre, '{_checksum(p)}');""", mostrar=False)
    ui.ok(f"{p.name} aplicado.")


def pendientes() -> None:
    """Ejecuta en orden los scripts que no se aplicaron."""
    if not sql.existe_base():
        raise ui.Fallo("La base no existe. Creela primero: arquis bd crear")
    aplicados = _aplicados()
    ef = _gestionada_por_ef()
    lista = [p for p in _scripts() if p.name not in aplicados and not (ef and p.name in LEGADO)]
    if not lista:
        ui.ok("No hay scripts pendientes.")
        return
    ui.info("Pendientes: " + ", ".join(p.name for p in lista))
    if not ui.confirmar("¿Ejecutarlos?", True):
        return
    for p in lista:
        _ejecutar(p)


def uno() -> None:
    """Ejecuta un script concreto (aunque ya este aplicado)."""
    lista = _scripts()
    i = ui.elegir("Script", [p.name for p in lista])
    if lista[i].name in LEGADO and _gestionada_por_ef():
        if not ui.confirmar_peligro("Script legado sobre una base EF: puede fallar o duplicar objetos.", "SI"):
            return
    _asegurar_tabla()
    _ejecutar(lista[i])


def archivo_libre() -> None:
    """Ejecuta cualquier archivo .sql indicando su ruta."""
    ruta = Path(ui.preguntar("Ruta del archivo .sql"))
    if not ruta.exists():
        raise ui.Fallo("No existe el archivo.")
    print(sql.archivo(ruta))


def marcar() -> None:
    """Marca un script como aplicado sin ejecutarlo."""
    lista = _scripts()
    i = ui.elegir("Script a marcar", [p.name for p in lista])
    _asegurar_tabla()
    p = lista[i]
    sql.ejecutar(f"""IF NOT EXISTS (SELECT 1 FROM {TABLA} WHERE Nombre = N'{sql.lit(p.name)}')
        INSERT {TABLA}(Nombre, Checksum) VALUES (N'{sql.lit(p.name)}', '{_checksum(p)}');""", mostrar=False)
    ui.ok(f"{p.name} marcado.")


def nuevo() -> None:
    """Crea un script numerado en 02_BaseDatos/ con plantilla idempotente."""
    numeros = [int(m.group(1)) for p in _scripts() if (m := re.match(r"(\d+)_", p.name))]
    n = (max(numeros) if numeros else 0) + 1
    nombre = ui.preguntar("Descripcion (ej. Agregar_Indice_X)").strip().replace(" ", "_")
    if not nombre:
        return
    destino = SQL_SCRIPTS / f"{n:02d}_{nombre}.sql"
    destino.write_text(f"""-- {destino.name}
-- Escribir el script de forma idempotente (se puede volver a ejecutar sin error).
SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

-- IF COL_LENGTH('dbo.Tabla', 'Columna') IS NULL
--     ALTER TABLE dbo.Tabla ADD Columna nvarchar(100) NULL;
GO
""", encoding="utf-8")
    ui.ok(f"Creado {rel(destino)}")


def verificacion_estados() -> None:
    """Ejecuta tests/service-state-checks.sql (no deja cambios)."""
    print(sql.archivo(TESTS / "service-state-checks.sql"))
