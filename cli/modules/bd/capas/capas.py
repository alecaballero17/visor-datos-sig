"""Definicion de las capas SIG y lectura de cabeceras SHP/DBF sin dependencias."""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from cli.core import env


@dataclass(frozen=True)
class Capa:
    clave: str
    archivo: str            # sin extension
    tabla: str
    tipo: str               # Polygon | Point | LineString
    campos: tuple[tuple[str, str, str], ...]   # (campo DBF, columna SQL, tipo: int|str)
    extra_cols: tuple[tuple[str, str], ...] = ()   # (columna, expresion SQL)


CAPAS = [
    Capa("manzanas", "Exp_MapaBase_MZA_4326", "dbo.Manzanas", "Polygon",
         (("Id", "IdOrigen", "int"), ("UV_MZA", "UV_MZA", "str"), ("UV", "UV", "str"), ("MZA", "MZA", "str"))),
    Capa("lotes", "Exp_MapaBase_LOTES_4326", "dbo.Lotes", "Polygon",
         (("Id", "IdOrigen", "int"), ("NroLote", "NroLote", "str"))),
    Capa("codigosfijos", "Exp_CodigoFijo_4326", "dbo.CodigosFijos", "Point",
         (("CodF_SQL", "CodF_SQL", "int"), ("CodF_SIG", "CodF_SIG", "str"), ("CodFijo", "CodFijo", "int"),
          ("Nombre", "Nombre", "str")),
         (("Estado", "1"), ("EstadoVerificado", "1"), ("FechaCambioEstado", "SYSUTCDATETIME()"))),
    Capa("vias", "Exp_MapaBase_VIAS_4326", "dbo.Vias", "LineString",
         (("OBJECTID", "OBJECTID", "int"), ("Nombre", "Nombre", "str"), ("type", "TipoVia", "str"), ("OSMID", "OSMID", "str"))),
]
POR_CLAVE = {c.clave: c for c in CAPAS}
EXTENSIONES = (".shp", ".shx", ".dbf", ".prj", ".cpg")
TIPOS_SHP = {0: "Null", 1: "Point", 3: "PolyLine", 5: "Polygon", 8: "MultiPoint", 11: "PointZ", 13: "PolyLineZ",
             15: "PolygonZ", 18: "MultiPointZ", 21: "PointM", 23: "PolyLineM", 25: "PolygonM"}


def carpeta() -> Path:
    return env.ruta_proyecto(env.get("SHP_DIR"))


@dataclass
class Cabecera:
    tipo: str
    bbox: tuple[float, float, float, float]
    registros: int
    campos: list[str]
    prj: str
    cpg: str


def leer_cabecera(base: Path) -> Cabecera:
    shp, dbf = base.with_suffix(".shp"), base.with_suffix(".dbf")
    with shp.open("rb") as f:
        h = f.read(100)
    codigo = struct.unpack(">i", h[0:4])[0]
    if codigo != 9994:
        raise ValueError(f"{shp.name} no es un shapefile valido")
    tipo = TIPOS_SHP.get(struct.unpack("<i", h[32:36])[0], "?")
    bbox = struct.unpack("<4d", h[36:68])
    with dbf.open("rb") as f:
        d = f.read(32)
        registros, largo_cab = struct.unpack("<IH", d[4:10])
        cab = f.read(largo_cab - 32)
    campos = []
    for i in range(0, len(cab), 32):
        if cab[i] == 0x0D:
            break
        campos.append(cab[i:i + 11].split(b"\x00")[0].decode("latin-1"))
    prj = base.with_suffix(".prj")
    cpg = base.with_suffix(".cpg")
    return Cabecera(tipo, bbox, registros, campos,
                    prj.read_text(errors="replace") if prj.exists() else "",
                    cpg.read_text(errors="replace").strip() if cpg.exists() else "")
