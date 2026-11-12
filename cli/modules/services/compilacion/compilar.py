"""Compilacion y publicacion de backend, frontend y migrador."""
from __future__ import annotations

import shutil
from pathlib import Path

from cli.core import shell, ui
from cli.core.paths import ARTIFACTS, BACKEND, FRONTEND, MIGRADOR, ROOT, proyectos_dotnet, rel

PROYECTOS = {"backend": BACKEND, "frontend": FRONTEND}


def _config() -> str:
    return "Release" if ui.elegir("Configuracion", ["Debug", "Release"], 0) == 1 else "Debug"


def solucion() -> None:
    """dotnet build de toda la solucion."""
    config = _config()
    for proyecto in proyectos_dotnet():
        shell.run([shell.dotnet(), "build", proyecto, "-c", config, "--nologo"], como_usuario=True)
    ui.ok("Solucion compilada.")


def compilar(clave: str, config: str = "Debug") -> None:
    shell.run([shell.dotnet(), "build", PROYECTOS[clave], "-c", config, "--nologo"], como_usuario=True)
    ui.ok(f"{clave} compilado ({config}).")


def backend() -> None:
    """Compila Arquis.Backend."""
    compilar("backend", _config())


def frontend() -> None:
    """Compila Arquis.Frontend (Razor + wwwroot)."""
    compilar("frontend", _config())


def publicar(clave: str, destino: Path | None = None, runtime: str | None = None) -> Path:
    """dotnet publish Release a artifacts/publish/<clave> (o al destino indicado)."""
    destino = destino or ARTIFACTS / "publish" / clave
    if destino.exists():
        shutil.rmtree(destino)
    cmd = [shell.dotnet(), "publish", PROYECTOS[clave], "-c", "Release", "-o", destino, "--nologo",
           "-p:UseAppHost=false", "-p:DebugType=none"]
    if runtime:
        cmd += ["-r", runtime, "--self-contained", "false"]
    shell.run(cmd, como_usuario=True)   # bajo sudo compila como el dueño del repositorio
    # appsettings.Development.json no debe viajar a produccion
    (destino / "appsettings.Development.json").unlink(missing_ok=True)
    ui.ok(f"{clave} publicado en {rel(destino)}")
    return destino


def publicar_backend() -> None:
    publicar("backend")


def publicar_frontend() -> None:
    publicar("frontend")


def publicar_todo() -> None:
    """Publica backend y frontend."""
    for clave in PROYECTOS:
        publicar(clave)


def migrador() -> None:
    """Publica el migrador WPF como un unico .exe (win-x64)."""
    destino = ARTIFACTS / "publish" / "migrador"
    shell.run([shell.dotnet(), "publish", MIGRADOR, "-c", "Release", "-r", "win-x64", "--self-contained", "true",
               "-p:PublishSingleFile=true", "-p:IncludeNativeLibrariesForSelfExtract=true", "-o", destino, "--nologo"])
    ui.ok(f"Migrador: {rel(destino)}")


def limpiar() -> None:
    """dotnet clean y borra carpetas bin/ y obj/."""
    for proyecto in proyectos_dotnet():
        shell.run([shell.dotnet(), "clean", proyecto, "--nologo", "-v", "q"], check=False, como_usuario=True)
    n = 0
    for carpeta in list((ROOT / "src").rglob("bin")) + list((ROOT / "src").rglob("obj")) + list((ROOT / "tests").rglob("bin")) + list((ROOT / "tests").rglob("obj")):
        if carpeta.is_dir():
            shutil.rmtree(carpeta, ignore_errors=True)
            n += 1
    ui.ok(f"{n} carpetas bin/obj eliminadas.")


def formato() -> None:
    """dotnet format (verificar o aplicar)."""
    aplicar = ui.elegir("Accion", ["Solo verificar", "Aplicar formato"]) == 1
    cmd = [shell.dotnet(), "format", proyectos_dotnet()[0]]
    if not aplicar:
        cmd.append("--verify-no-changes")
    r = shell.run(cmd, check=False)
    ui.ok("Formato correcto.") if r.returncode == 0 else ui.warn("Hay diferencias de formato.")


def paquetes_obsoletos() -> None:
    """dotnet list package --outdated."""
    [shell.run([shell.dotnet(), "list", p_, "package", "--outdated"], check=False) for p_ in proyectos_dotnet()]


def vulnerabilidades() -> None:
    """dotnet list package --vulnerable --include-transitive."""
    [shell.run([shell.dotnet(), "list", p_, "package", "--vulnerable", "--include-transitive"], check=False) for p_ in proyectos_dotnet()]
