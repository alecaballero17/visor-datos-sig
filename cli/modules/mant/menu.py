from cli.core.menu import Menu

from . import mant

MENU = Menu("mant", "Mantenimiento", "Limpieza, puertos e informacion del proyecto", orden=90)
MENU.agregar("info", "Informacion del proyecto", mant.info)
MENU.agregar("puertos", "Puertos ocupados", mant.puertos)
MENU.agregar("limpiar", "Limpiar temporales y artefactos", mant.limpiar)
