from cli.core import shell, ui
from cli.core.menu import Menu
from cli.core.paths import EDITOR, ROOT

from . import espacial, importar, verificar


def abrir_editor() -> None:
    """Abre SIG Vector Studio (requiere: arquis deps pip-editor)."""
    shell.nueva_consola([shell.python(), str(EDITOR / "main.py")], cwd=ROOT, titulo="SIG Vector Studio")
    ui.ok("Editor lanzado en otra ventana.")


MENU = Menu("capas", "Capas SIG (shapefiles)", "Verificar, importar y mantener datos espaciales", orden=70, requiere=("base",))
MENU.agregar("verificar", "Verificar shapefiles", verificar.verificar, requiere=("shp",))
MENU.agregar("detalle", "Detalle de campos", verificar.detalle, requiere=("shp",))
MENU.agregar("copiar", "Copiar capas desde otra carpeta", verificar.copiar, requiere=())
MENU.agregar("importar", "Importar todas las capas", importar.importar, requiere=("base", "shp", "pyshp"))
MENU.agregar("importar-una", "Importar una capa", importar.importar_una, requiere=("base", "shp", "pyshp"))
MENU.agregar("comparar", "Comparar SHP vs base", verificar.comparar, requiere=("base", "shp"))
MENU.agregar("stats", "Estadisticas espaciales", espacial.estadisticas)
MENU.agregar("vincular", "Vincular lotes/manzanas/codigos", espacial.vincular)
MENU.agregar("reparar", "Reparar geometrias invalidas", espacial.reparar)
MENU.agregar("indices", "Reconstruir indices espaciales", espacial.indices)
MENU.agregar("vaciar", "Vaciar una capa", espacial.vaciar_capa)
MENU.agregar("editor", "Abrir SIG Vector Studio", abrir_editor, requiere=())