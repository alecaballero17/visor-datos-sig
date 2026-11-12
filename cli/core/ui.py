"""Salida con color y preguntas interactivas (solo biblioteca estandar)."""
from __future__ import annotations

import getpass
import os
import re
import sys
from typing import Iterable, Sequence

# Activa secuencias ANSI en la consola de Windows y fuerza UTF-8.
if os.name == "nt":
    os.system("")
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

AUTO_YES = False          # --yes: confirmaciones aceptadas y preguntas con su valor por defecto
NO_COLOR = bool(os.environ.get("NO_COLOR"))


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"


def c(texto: str, *estilos: str) -> str:
    if NO_COLOR or not estilos:
        return texto
    return "".join(estilos) + texto + C.RESET


def titulo(texto: str) -> None:
    linea = "─" * (len(texto) + 4)
    print()
    print(c(f"┌{linea}┐", C.CYAN))
    print(c(f"│  {texto}  │", C.CYAN, C.BOLD))
    print(c(f"└{linea}┘", C.CYAN))


def seccion(texto: str) -> None:
    print()
    print(c(f"▸ {texto}", C.BLUE, C.BOLD))


def info(texto: str) -> None:
    print(c("  · ", C.GRAY) + texto)


def ok(texto: str) -> None:
    print(c("  ✔ ", C.GREEN) + texto)


def warn(texto: str) -> None:
    print(c("  ! ", C.YELLOW) + c(texto, C.YELLOW))


def error(texto: str) -> None:
    print(c("  ✖ ", C.RED) + c(texto, C.RED), file=sys.stderr)


def dim(texto: str) -> None:
    print(c(f"    {texto}", C.GRAY))


def paso(n: int, total: int, texto: str) -> None:
    print()
    print(c(f"[{n}/{total}] ", C.MAGENTA, C.BOLD) + c(texto, C.BOLD))


def preguntar(texto: str, defecto: str | None = None, secreto: bool = False) -> str:
    if AUTO_YES:
        return defecto or ""
    sufijo = f" [{defecto}]" if defecto not in (None, "") and not secreto else ""
    prompt = c("  ? ", C.CYAN) + texto + sufijo + ": "
    try:
        valor = getpass.getpass(prompt) if secreto else input(prompt)
    except EOFError:
        valor = ""
    valor = valor.strip()
    return valor if valor else (defecto or "")


def confirmar(texto: str, defecto: bool = False) -> bool:
    if AUTO_YES:
        return True
    opciones = "S/n" if defecto else "s/N"
    try:
        r = input(c("  ? ", C.CYAN) + f"{texto} ({opciones}): ").strip().lower()
    except EOFError:
        r = ""
    if not r:
        return defecto
    return r in ("s", "si", "sí", "y", "yes")


def confirmar_peligro(texto: str, palabra: str) -> bool:
    """Confirmacion fuerte: el usuario debe escribir `palabra`."""
    warn(texto)
    if AUTO_YES:
        return True
    try:
        r = input(c("  ? ", C.RED) + f"Escriba '{palabra}' para continuar: ").strip()
    except EOFError:
        r = ""
    return r == palabra


def elegir(texto: str, opciones: Sequence[str], defecto: int = 0) -> int:
    """Devuelve el indice elegido."""
    if AUTO_YES:
        return defecto
    print(c("  ? ", C.CYAN) + texto)
    for i, o in enumerate(opciones, 1):
        marca = c("›", C.CYAN) if i - 1 == defecto else " "
        print(f"   {marca} {c(str(i), C.BOLD)}) {o}")
    while True:
        r = preguntar("Opcion", str(defecto + 1))
        if r.isdigit() and 1 <= int(r) <= len(opciones):
            return int(r) - 1
        warn("Opcion invalida.")


_ANSI = re.compile(r"\033\[[0-9;]*m")


def _visible(texto: str) -> int:
    return len(_ANSI.sub("", texto))


def _recortar(texto: str, maximo: int = 70) -> str:
    return texto if _visible(texto) <= maximo or "\033" in texto else texto[: maximo - 1] + "…"


def tabla(filas: Iterable[Sequence[object]], encabezados: Sequence[str] | None = None) -> None:
    filas = [[_recortar("" if v is None else str(v)) for v in f] for f in filas]
    if encabezados:
        filas_all = [list(encabezados)] + filas
    else:
        filas_all = filas
    if not filas_all:
        info("(sin filas)")
        return
    ncols = max(len(f) for f in filas_all)
    anchos = [max(_visible(f[i]) if i < len(f) else 0 for f in filas_all) for i in range(ncols)]
    def fmt(f):
        return "  " + "  ".join(v + " " * (anchos[i] - _visible(v)) for i, v in enumerate(f))
    if encabezados:
        print(c(fmt(encabezados), C.BOLD))
        print(c("  " + "  ".join("─" * a for a in anchos), C.GRAY))
    for f in filas:
        print(fmt(f))


def pausa() -> None:
    if AUTO_YES:
        return
    try:
        input(c("\n  Presione Enter para continuar...", C.GRAY))
    except EOFError:
        pass


def barra(actual: int, total: int, prefijo: str = "") -> None:
    if total <= 0:
        sys.stdout.write(f"\r  {prefijo} {actual / 1_048_576:.1f} MB")
    else:
        pct = actual / total
        llenos = int(30 * pct)
        sys.stdout.write(f"\r  {prefijo} [{'█' * llenos}{'·' * (30 - llenos)}] {pct * 100:5.1f}%")
    sys.stdout.flush()


class Fallo(Exception):
    """Error esperado de una herramienta: se muestra sin traza."""
