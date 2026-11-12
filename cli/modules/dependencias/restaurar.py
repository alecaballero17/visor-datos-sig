"""Dependencias de cada subproyecto (NuGet, dotnet-ef local, pip, pub)."""
from __future__ import annotations

import json
import venv

from cli.core import shell, ui
from cli.core.paths import MOVIL, REQUIREMENTS, ROOT, VENV, proyectos_dotnet, rel

# dotnet-ef como herramienta LOCAL del repositorio (.config/dotnet-tools.json):
# funciona igual con cualquier usuario, tambien bajo sudo en el servidor.
MANIFIESTO = ROOT / ".config" / "dotnet-tools.json"
DOTNET_TOOLS = {"dotnet-ef": "10.0.12"}


def nuget() -> None:
    """dotnet restore (en Linux: backend, frontend y pruebas; el migrador WPF es solo Windows)."""
    for proyecto in proyectos_dotnet():
        shell.run([shell.dotnet(), "restore", proyecto, "--nologo"], como_usuario=True)
    ui.ok("Paquetes NuGet restaurados.")


def _escribir_manifiesto() -> None:
    datos = {"version": 1, "isRoot": True, "tools": {}}
    if MANIFIESTO.exists():
        datos = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    for tool, version in DOTNET_TOOLS.items():
        datos["tools"].setdefault(tool, {"version": version, "commands": [tool], "rollForward": False})
        datos["tools"][tool]["version"] = version
    MANIFIESTO.parent.mkdir(exist_ok=True)
    MANIFIESTO.write_text(json.dumps(datos, indent=2) + "\n", encoding="utf-8", newline="\n")


def herramientas_dotnet() -> None:
    """Instala dotnet-ef como herramienta local (dotnet tool restore)."""
    _escribir_manifiesto()
    shell.run([shell.dotnet(), "tool", "restore"], cwd=ROOT, como_usuario=True)
    ui.ok(f"Herramientas dotnet listas ({rel(MANIFIESTO)}).")


def ef_rapido() -> tuple[bool, str]:
    """Comprobacion sin ejecutar dotnet: manifiesto + paquete restaurado en la cache de NuGet."""
    import os
    from pathlib import Path
    if not MANIFIESTO.exists():
        return False, "falta .config/dotnet-tools.json"
    usuario = shell.usuario_original()
    home = Path(os.path.expanduser(f"~{usuario}")) if usuario else Path.home()
    cache = Path(os.environ.get("NUGET_PACKAGES") or home / ".nuget" / "packages")
    version = DOTNET_TOOLS["dotnet-ef"]
    if not (cache / "dotnet-ef" / version).exists():
        return False, f"dotnet-ef {version} sin restaurar"
    return True, version


def ef_disponible() -> bool:
    if ef_rapido()[0]:
        return True
    if not MANIFIESTO.exists():
        return False
    shell.run([shell.dotnet(), "tool", "restore"], cwd=ROOT, check=False, capturar=True, silencioso=True)
    return ef_rapido()[0]


def crear_venv() -> None:
    """Crea .venv en la raiz del proyecto."""
    if VENV.exists():
        ui.info(f"{rel(VENV)} ya existe.")
        return
    ui.info(f"Creando {rel(VENV)}...")
    try:
        venv.EnvBuilder(with_pip=True).create(VENV)
    except Exception as e:  # noqa: BLE001
        raise ui.Fallo(f"No se pudo crear el entorno virtual ({e}). En Debian/Ubuntu: sudo apt install python3-venv")
    ui.ok("Entorno virtual creado; arquis.sh / arquis.cmd lo usan automaticamente.")


def _pip(archivo: str) -> None:
    shell.run([shell.python(), "-m", "pip", "install", "--disable-pip-version-check", "-r", REQUIREMENTS / archivo])


def python_cli() -> None:
    """Dependencias de la CLI (pyshp para importar capas)."""
    crear_venv()
    _pip("cli.txt")
    ui.ok("Dependencias de la CLI instaladas.")


def python_editor() -> None:
    """Dependencias de SIG Vector Studio (PyQt6, OpenCV; solo escritorio)."""
    crear_venv()
    _pip("editor.txt")
    ui.ok("Dependencias del editor instaladas.")


def flutter_pub() -> None:
    """flutter pub get en Movil/."""
    flutter = shell.requerir("flutter", ayuda="Instale Flutter SDK.")
    shell.run([flutter, "pub", "get"], cwd=MOVIL)
    ui.ok("Paquetes Dart restaurados.")


def _correr(pasos) -> None:
    fallos = []
    for i, (nombre, fn) in enumerate(pasos, 1):
        ui.paso(i, len(pasos), nombre)
        try:
            fn()
        except ui.Fallo as e:
            ui.error(str(e))
            fallos.append(nombre)
    if fallos:
        raise ui.Fallo("Fallaron: " + ", ".join(fallos))
    ui.ok("Dependencias restauradas.")


def servidor() -> None:
    """Lo necesario para compilar y desplegar (NuGet, dotnet-ef, pyshp)."""
    _correr([("NuGet", nuget), ("dotnet-ef", herramientas_dotnet), ("Python CLI", python_cli)])


def todo() -> None:
    """Todo, incluidas dependencias de desarrollo (editor, Flutter)."""
    pasos = [("NuGet", nuget), ("dotnet-ef", herramientas_dotnet), ("Python CLI", python_cli)]
    if ui.AUTO_YES or ui.confirmar("¿Instalar tambien el editor de escritorio (PyQt6, OpenCV)?", False):
        pasos.append(("Python editor", python_editor))
    if shell.which("flutter"):
        pasos.append(("Flutter", flutter_pub))
    _correr(pasos)
