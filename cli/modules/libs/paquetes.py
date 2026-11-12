"""Revision de paquetes desactualizados en todos los ecosistemas."""
from __future__ import annotations

from cli.core import shell, ui
from cli.core.paths import MOVIL, proyectos_dotnet


def nuget() -> None:
    """NuGet desactualizados."""
    for proyecto in proyectos_dotnet():
        shell.run([shell.dotnet(), "list", proyecto, "package", "--outdated"], check=False)


def pub() -> None:
    """Dart/Flutter desactualizados."""
    fl = shell.which("flutter")
    if fl:
        shell.run([fl, "pub", "outdated"], cwd=MOVIL, check=False)
    else:
        ui.warn("Flutter no instalado.")


def pip() -> None:
    """pip desactualizados (.venv)."""
    shell.run([shell.python(), "-m", "pip", "list", "--outdated"], check=False)


def todos() -> None:
    """Revisa NuGet, pub y pip."""
    for nombre, fn in (("NuGet", nuget), ("Flutter pub", pub), ("pip", pip)):
        ui.seccion(nombre)
        fn()
