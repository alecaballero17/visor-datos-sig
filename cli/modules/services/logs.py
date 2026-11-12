"""Logs: seguimiento en tiempo real (tail -f), ultimas lineas, busqueda de errores."""
from __future__ import annotations

import re
import time
from pathlib import Path

from cli.core import ui

COLORES = [ui.C.CYAN, ui.C.MAGENTA, ui.C.BLUE, ui.C.GREEN, ui.C.YELLOW]
PATRON_ERROR = re.compile(r"\b(fail|error|exception|crit|fatal|unhandled)\b", re.I)
PATRON_WARN = re.compile(r"\b(warn|warning)\b", re.I)


def _colorear(linea: str) -> str:
    if PATRON_ERROR.search(linea):
        return ui.c(linea, ui.C.RED)
    if PATRON_WARN.search(linea):
        return ui.c(linea, ui.C.YELLOW)
    return linea


def ultimas(ruta: Path, n: int = 40) -> list[str]:
    if not ruta.exists():
        return []
    with ruta.open("rb") as f:
        f.seek(0, 2)
        tam = f.tell()
        f.seek(max(0, tam - 200_000))
        return f.read().decode("utf-8", "replace").splitlines()[-n:]


def mostrar_ultimas(archivos: dict[str, Path], n: int = 40) -> None:
    for i, (etiqueta, ruta) in enumerate(archivos.items()):
        ui.seccion(f"{etiqueta}  ({ruta})")
        lineas = ultimas(ruta, n)
        if not lineas:
            ui.dim("(vacio o inexistente)")
        for l in lineas:
            print("  " + _colorear(l))


def seguir(archivos: dict[str, Path], historial: int = 15, filtro: str | None = None) -> None:
    """Muestra las lineas nuevas de varios archivos a la vez. Ctrl+C para salir."""
    patron = re.compile(filtro, re.I) if filtro else None
    ancho = max(len(e) for e in archivos)
    estado: dict[str, tuple[int, int]] = {}   # etiqueta -> (posicion, inode/tamano)
    for i, (etiqueta, ruta) in enumerate(archivos.items()):
        color = COLORES[i % len(COLORES)]
        for l in ultimas(ruta, historial):
            if not patron or patron.search(l):
                print(ui.c(f"{etiqueta:<{ancho}} │ ", color) + _colorear(l))
        estado[etiqueta] = (ruta.stat().st_size if ruta.exists() else 0, 0)
    print(ui.c(f"── siguiendo {len(archivos)} archivo(s) en tiempo real · Ctrl+C para salir ──", ui.C.GRAY))
    restos = {e: "" for e in archivos}
    try:
        while True:
            hubo = False
            for i, (etiqueta, ruta) in enumerate(archivos.items()):
                if not ruta.exists():
                    continue
                pos, _ = estado[etiqueta]
                tam = ruta.stat().st_size
                if tam < pos:          # rotado o truncado
                    pos = 0
                if tam == pos:
                    continue
                with ruta.open("rb") as f:
                    f.seek(pos)
                    datos = f.read()
                estado[etiqueta] = (pos + len(datos), 0)
                texto = restos[etiqueta] + datos.decode("utf-8", "replace")
                *lineas, restos[etiqueta] = texto.split("\n")
                color = COLORES[i % len(COLORES)]
                for l in lineas:
                    l = l.rstrip("\r")
                    if patron and not patron.search(l):
                        continue
                    print(ui.c(f"{etiqueta:<{ancho}} │ ", color) + _colorear(l), flush=True)
                hubo = True
            if not hubo:
                time.sleep(0.4)
    except KeyboardInterrupt:
        print()
        ui.info("Fin del seguimiento.")


def buscar_errores(archivos: dict[str, Path], n: int = 60) -> None:
    encontrados = 0
    for etiqueta, ruta in archivos.items():
        lineas = [l for l in ultimas(ruta, 5000) if PATRON_ERROR.search(l)]
        if lineas:
            ui.seccion(f"{etiqueta}: {len(lineas)} lineas con error")
            for l in lineas[-n:]:
                print("  " + ui.c(l, ui.C.RED))
            encontrados += len(lineas)
    if not encontrados:
        ui.ok("Sin errores en los logs recientes.")


def limpiar(archivos: dict[str, Path]) -> None:
    if not ui.confirmar("¿Vaciar estos archivos de log?"):
        return
    for etiqueta, ruta in archivos.items():
        if ruta.exists():
            try:
                ruta.write_text("", encoding="utf-8")
                ui.ok(f"{etiqueta} vaciado.")
            except PermissionError:
                ui.warn(f"{etiqueta}: en uso por el servicio (detengalo o use la rotacion).")
