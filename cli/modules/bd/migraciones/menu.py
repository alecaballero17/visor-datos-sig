from cli.core.menu import Menu

from . import ef

MENU = Menu("migraciones", "Migraciones (EF Core)", "dotnet ef sobre Arquis.Backend", orden=20)
MENU.agregar("estado", "Estado de migraciones", ef.estado)
MENU.agregar("aplicar", "Aplicar pendientes", ef.actualizar, "database update")
MENU.agregar("ir", "Migrar a una version (rollback)", ef.ir_a)
MENU.agregar("revertir", "Revertir la ultima", ef.revertir_ultima)
MENU.agregar("nueva", "Crear migracion nueva", ef.agregar)
MENU.agregar("quitar", "Quitar ultima migracion del codigo", ef.quitar_ultima)
MENU.agregar("cambios", "¿Modelo con cambios sin migrar?", ef.cambios_pendientes)
MENU.agregar("script", "Generar script SQL idempotente", ef.script)
MENU.agregar("bundle", "Generar efbundle ejecutable", ef.bundle)
MENU.agregar("contexto", "Info del DbContext", ef.informacion_contexto)
