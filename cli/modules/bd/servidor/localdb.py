"""Gestion de SQL Server LocalDB."""
from __future__ import annotations

import re

from cli.core import env, shell, ui


def _exe() -> str:
    return shell.requerir("SqlLocalDB", shell.LOCALDB_EXTRAS, "Instale SQL Server Express LocalDB.")


def _instancia() -> str:
    servidor = env.get("DB_SERVER")
    m = re.match(r"\(localdb\)\\(.+)", servidor, re.I)
    return m.group(1) if m else "MSSQLLocalDB"


def info() -> None:
    """Instancias LocalDB y su estado."""
    exe = _exe()
    for nombre in [n.strip() for n in shell.salida([exe, "info"]).splitlines() if n.strip()]:
        ui.seccion(nombre)
        print(shell.salida([exe, "info", nombre]))


def iniciar() -> None:
    shell.run([_exe(), "start", _instancia()])
    ui.ok(f"LocalDB '{_instancia()}' iniciada.")


def detener() -> None:
    shell.run([_exe(), "stop", _instancia()], check=False)
    ui.ok(f"LocalDB '{_instancia()}' detenida.")


def crear() -> None:
    """Crea una instancia LocalDB nueva."""
    nombre = ui.preguntar("Nombre de la instancia", "Arquis")
    shell.run([_exe(), "create", nombre, "-s"])
    if ui.confirmar(f"¿Usar (localdb)\\{nombre} en el .env?", True):
        cfg = env.cargar()
        cfg.update(DB_SERVER=rf"(localdb)\{nombre}", DB_AUTH="windows")
        env.escribir(cfg)
        ui.ok(".env actualizado.")


def eliminar() -> None:
    """Elimina una instancia LocalDB (sus bases quedan en disco)."""
    exe = _exe()
    nombres = [n.strip() for n in shell.salida([exe, "info"]).splitlines() if n.strip()]
    if not nombres:
        ui.warn("No hay instancias.")
        return
    i = ui.elegir("Instancia a eliminar", nombres)
    if ui.confirmar_peligro(f"Se eliminara la instancia {nombres[i]}.", nombres[i]):
        shell.run([exe, "stop", nombres[i], "-k"], check=False)
        shell.run([exe, "delete", nombres[i]])
        ui.ok("Instancia eliminada.")
