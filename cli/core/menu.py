"""Motor de menus.

Cada carpeta de `cli/modules/` (y cualquier subcarpeta) que tenga un `menu.py`
con una variable `MENU` se registra sola. Las subcarpetas con su propio
`menu.py` aparecen como submenus del modulo que las contiene:

    cli/modules/<modulo>/menu.py                 -> MENU del modulo
    cli/modules/<modulo>/<herramienta>.py        -> funciones de la herramienta
    cli/modules/<modulo>/<submodulo>/menu.py     -> submenu (se descubre solo)

El mismo arbol se usa en modo interactivo y en modo comando:
    arquis db migraciones actualizar --yes
"""
from __future__ import annotations

import importlib
import pkgutil
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import ui


@dataclass
class Accion:
    clave: str
    titulo: str
    fn: Callable[[], object]
    descripcion: str = ""


@dataclass
class Menu:
    clave: str
    titulo: str
    descripcion: str = ""
    orden: int = 100
    items: list = field(default_factory=list)   # Accion | Menu
    _paquete: str | None = None

    # -- registro -----------------------------------------------------------
    def agregar(self, clave: str, titulo: str, fn: Callable[[], object], descripcion: str = "") -> "Menu":
        self.items.append(Accion(clave, titulo, fn, descripcion))
        return self

    def accion(self, clave: str, titulo: str, descripcion: str = ""):
        def deco(fn):
            self.agregar(clave, titulo, fn, descripcion)
            return fn
        return deco

    def submenu(self, menu: "Menu") -> "Menu":
        self.items.append(menu)
        return self

    def descubrir(self, paquete: str) -> "Menu":
        """Agrega como submenus las subcarpetas de `paquete` que tengan menu.py."""
        self._paquete = paquete
        pkg = importlib.import_module(paquete)
        encontrados = []
        for m in pkgutil.iter_modules(pkg.__path__):
            if not m.ispkg:
                continue
            ruta = Path(pkg.__path__[0]) / m.name / "menu.py"
            if not ruta.exists():
                continue
            mod = importlib.import_module(f"{paquete}.{m.name}.menu")
            sub = getattr(mod, "MENU", None)
            if isinstance(sub, Menu):
                encontrados.append(sub)
        for sub in sorted(encontrados, key=lambda s: (s.orden, s.titulo)):
            self.submenu(sub)
        return self

    # -- busqueda -----------------------------------------------------------
    def buscar(self, clave: str):
        for it in self.items:
            if it.clave == clave:
                return it
        return None

    # -- ejecucion ----------------------------------------------------------
    def ejecutar(self, ruta: list[str] | None = None) -> None:
        while True:
            ui.titulo(" › ".join((ruta or []) + [self.titulo]))
            if self.descripcion:
                ui.dim(self.descripcion)
            print()
            for i, it in enumerate(self.items, 1):
                es_menu = isinstance(it, Menu)
                marca = ui.c("▸", ui.C.BLUE) if es_menu else ui.c("•", ui.C.GRAY)
                nombre = ui.c(it.titulo, ui.C.BOLD) if es_menu else it.titulo
                desc = ui.c(f"  {it.descripcion}", ui.C.GRAY) if it.descripcion else ""
                print(f"  {ui.c(f'{i:>2}', ui.C.CYAN)}) {marca} {nombre}{desc}")
            print(f"  {ui.c(' 0', ui.C.CYAN)}) {'Volver' if ruta else 'Salir'}")
            try:
                r = input(ui.c("\n  › ", ui.C.CYAN)).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not r:
                continue
            if r in ("0", "q", "salir"):
                return
            it = None
            if r.isdigit() and 1 <= int(r) <= len(self.items):
                it = self.items[int(r) - 1]
            else:
                it = self.buscar(r)
            if it is None:
                ui.warn("Opcion invalida.")
                continue
            if isinstance(it, Menu):
                it.ejecutar((ruta or []) + [self.titulo])
            else:
                correr(it)
                ui.pausa()

    def arbol(self, prefijo: str = "", nivel: int = 0) -> None:
        for it in self.items:
            ruta = f"{prefijo} {it.clave}".strip()
            if isinstance(it, Menu):
                print("  " * nivel + ui.c(f"{ruta}", ui.C.BLUE, ui.C.BOLD) + ui.c(f"  — {it.titulo}", ui.C.GRAY))
                it.arbol(ruta, nivel + 1)
            else:
                print("  " * nivel + ui.c(ruta, ui.C.CYAN) + f"  {it.titulo}"
                      + (ui.c(f" ({it.descripcion})", ui.C.GRAY) if it.descripcion else ""))


def correr(accion: Accion) -> bool:
    """Ejecuta una accion capturando errores. Devuelve True si termino bien."""
    ui.seccion(accion.titulo)
    try:
        r = accion.fn()
        return r is not False
    except ui.Fallo as e:
        ui.error(str(e))
    except KeyboardInterrupt:
        print()
        ui.warn("Cancelado por el usuario.")
    except Exception as e:  # noqa: BLE001
        ui.error(f"{type(e).__name__}: {e}")
        ui.dim(traceback.format_exc().strip().splitlines()[-3] if traceback.format_exc() else "")
    return False


def menu_raiz() -> Menu:
    raiz = Menu("arquis", "ARQUIS · Herramientas del proyecto",
                "Configuracion, dependencias, base de datos, compilacion, pruebas y despliegue.")
    raiz.descubrir("cli.modules")
    return raiz
