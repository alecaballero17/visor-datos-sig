"""Punto de entrada.

    python -m cli                       menu interactivo
    python -m cli --list                arbol de comandos
    python -m cli db migraciones estado comando directo
    python -m cli deploy completo --yes sin preguntas (usa valores por defecto)
"""
from __future__ import annotations

import sys

from cli import __version__
from cli.core import ui
from cli.core.menu import Menu, correr, menu_raiz

AYUDA = __doc__


def main(argv: list[str]) -> int:
    banderas = {a for a in argv if a.startswith("-")}
    ruta = [a for a in argv if not a.startswith("-")]
    if "--yes" in banderas or "-y" in banderas:
        ui.AUTO_YES = True
    if "--no-color" in banderas:
        ui.NO_COLOR = True
    if "--version" in banderas:
        print(f"arquis-cli {__version__}")
        return 0
    if "-h" in banderas or "--help" in banderas:
        print(AYUDA)
        return 0

    raiz = menu_raiz()
    if "--list" in banderas or "-l" in banderas:
        ui.titulo("Comandos disponibles")
        raiz.arbol()
        return 0

    if not ruta:
        print(ui.c(BANNER, ui.C.CYAN, ui.C.BOLD))
        try:
            from cli.modules.inicio.preparacion import aviso_inicial
            aviso_inicial()
        except Exception:  # noqa: BLE001  (el aviso nunca impide abrir el menu)
            pass
        raiz.ejecutar()
        return 0

    nodo: Menu | object = raiz
    recorrido = []
    for clave in ruta:
        if not isinstance(nodo, Menu):
            ui.error(f"'{' '.join(recorrido)}' es una accion; sobra '{clave}'.")
            return 2
        sig = nodo.buscar(clave)
        if sig is None:
            ui.error(f"No existe '{clave}' en '{' '.join(recorrido) or 'arquis'}'. Opciones:")
            for it in nodo.items:
                print(f"    {it.clave:<14} {it.titulo}")
            return 2
        recorrido.append(clave)
        nodo = sig
    if isinstance(nodo, Menu):
        if sys.stdin.isatty() and not ui.AUTO_YES:
            nodo.ejecutar(recorrido[:-1])
        else:
            nodo.arbol(" ".join(recorrido))
        return 0
    return 0 if correr(nodo) else 1


BANNER = r"""
     _                    _
    / \   _ __ __ _ _   _(_)___     Visor de datos SIG
   / _ \ | '__/ _` | | | | / __|    San Ignacio de Velasco
  / ___ \| | | (_| | |_| | \__ \
 /_/   \_\_|  \__, |\__,_|_|___/    CLI de herramientas
                 |_|
"""

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print()
        sys.exit(130)
