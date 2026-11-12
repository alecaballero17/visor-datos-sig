"""Ejecucion de comandos externos (Linux y Windows)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence

from . import ui
from .paths import LOGS_DIR, ROOT, VENV

ES_WINDOWS = os.name == "nt"
ES_LINUX = sys.platform.startswith("linux")

DOTNET_EXTRAS = ([r"C:\Program Files\dotnet\dotnet.exe"] if ES_WINDOWS
                 else ["/usr/bin/dotnet", "/usr/share/dotnet/dotnet", "/usr/lib/dotnet/dotnet",
                       str(Path.home() / ".dotnet" / "dotnet")])
LOCALDB_EXTRAS = [rf"C:\Program Files\Microsoft SQL Server\{v}\Tools\Binn\SqlLocalDB.exe" for v in (170, 160, 150)]


def which(nombre: str, extras: Sequence[str] = ()) -> str | None:
    """Busca un ejecutable en PATH y luego en rutas conocidas."""
    r = shutil.which(nombre)
    if r:
        return r
    for e in extras:
        if Path(e).exists():
            return e
    return None


def dotnet() -> str:
    exe = which("dotnet", DOTNET_EXTRAS)
    if not exe:
        raise ui.Fallo("No se encontro el SDK de .NET 10. Ejecute: arquis deps instalar")
    return exe


def python() -> str:
    """Python del entorno virtual del proyecto si existe; si no, el actual."""
    venv_py = VENV / ("Scripts/python.exe" if ES_WINDOWS else "bin/python")
    return str(venv_py) if venv_py.exists() else sys.executable


def requerir(nombre: str, extras: Sequence[str] = (), ayuda: str = "") -> str:
    exe = which(nombre, extras)
    if not exe:
        raise ui.Fallo(f"No se encontro '{nombre}'. {ayuda}".strip())
    return exe


# -- privilegios -------------------------------------------------------------------
def es_root() -> bool:
    if ES_WINDOWS:
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:  # noqa: BLE001
            return False
    return os.geteuid() == 0


def sudo(cmd: Sequence[str]) -> list[str]:
    """Antepone sudo en Linux si no somos root."""
    cmd = [str(c) for c in cmd]
    if ES_WINDOWS or es_root():
        return cmd
    if not which("sudo"):
        raise ui.Fallo("Se requieren privilegios de root y no hay sudo.")
    return ["sudo", *cmd]


def usuario_original() -> str | None:
    """Usuario que invoco sudo (para no compilar como root dentro del repositorio)."""
    if ES_WINDOWS or not es_root():
        return None
    u = os.environ.get("SUDO_USER")
    return u if u and u != "root" else None


def requerir_escritura(carpeta: Path) -> None:
    """Falla con un mensaje claro si no se puede escribir en `carpeta` (p. ej. /opt/arquis sin sudo)."""
    d = Path(carpeta)
    while not d.exists() and d.parent != d:
        d = d.parent
    if not os.access(d, os.W_OK):
        raise ui.Fallo(f"Sin permiso de escritura en {carpeta}. "
                       + ("Abra la terminal como Administrador." if ES_WINDOWS else "Ejecute con sudo: sudo ./arquis.sh ..."))


def _mostrar(cmd: Sequence[str]) -> None:
    texto = " ".join(f'"{a}"' if " " in str(a) else str(a) for a in cmd)
    texto = texto if len(texto) < 400 else texto[:400] + "…"
    ui.dim(f"$ {texto}")


def run(cmd: Sequence[str], cwd: Path | str | None = None, env: Mapping[str, str] | None = None,
        check: bool = True, capturar: bool = False, silencioso: bool = False,
        entrada: str | None = None, timeout: float | None = None,
        como_usuario: bool = False) -> subprocess.CompletedProcess:
    """Ejecuta un comando.

    `como_usuario`: si la CLI corre con sudo, ejecuta el comando como el usuario
    original (compilaciones dentro del repositorio, caches de NuGet del usuario).
    """
    cmd = [str(a) for a in cmd]
    entorno = dict(os.environ)
    if env:
        entorno.update(env)
    if not silencioso:
        _mostrar(cmd)
    usuario = usuario_original() if como_usuario else None
    if usuario:
        extra = [f"{k}={v}" for k, v in (env or {}).items()]
        cmd = ["sudo", "-u", usuario, "-H", "env", *extra, *cmd]
    try:
        p = subprocess.run(
            cmd, cwd=str(cwd or ROOT), env=entorno, input=entrada, timeout=timeout,
            text=True, encoding="utf-8", errors="replace",
            stdout=subprocess.PIPE if capturar else None,
            stderr=subprocess.PIPE if capturar else None,
        )
    except FileNotFoundError:
        raise ui.Fallo(f"No se encontro el programa: {cmd[0]}")
    except subprocess.TimeoutExpired:
        raise ui.Fallo(f"Tiempo agotado ejecutando: {cmd[0]}")
    if check and p.returncode != 0:
        detalle = ""
        if capturar:
            detalle = "\n" + ((p.stderr or "") + (p.stdout or "")).strip()[-1500:]
        raise ui.Fallo(f"El comando termino con codigo {p.returncode}: {' '.join(cmd[:4])}...{detalle}")
    return p


def salida(cmd: Sequence[str], cwd: Path | str | None = None, env: Mapping[str, str] | None = None) -> str:
    """Devuelve stdout (o cadena vacia si falla)."""
    try:
        p = run(cmd, cwd=cwd, env=env, check=False, capturar=True, silencioso=True, timeout=60)
        return (p.stdout or "").strip() if p.returncode == 0 else ""
    except ui.Fallo:
        return ""


def en_segundo_plano(cmd: Sequence[str], log: Path, cwd: Path | str | None = None,
                     env: Mapping[str, str] | None = None) -> subprocess.Popen:
    """Lanza un proceso desacoplado de la terminal con su salida en `log`."""
    entorno = dict(os.environ)
    if env:
        entorno.update(env)
    log.parent.mkdir(parents=True, exist_ok=True)
    f = log.open("w", encoding="utf-8")
    flags = 0
    if ES_WINDOWS:
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
    return subprocess.Popen([str(c) for c in cmd], cwd=str(cwd or ROOT), env=entorno, stdout=f,
                            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=flags,
                            start_new_session=not ES_WINDOWS)


def nueva_consola(cmd: Sequence[str], cwd: Path | str | None = None, env: Mapping[str, str] | None = None,
                  titulo: str = "Arquis") -> None:
    """Ventana nueva en Windows / escritorio Linux; en un servidor sin entorno grafico
    corre en segundo plano con log en .setup/logs."""
    entorno = dict(os.environ)
    if env:
        entorno.update(env)
    _mostrar(cmd)
    if ES_WINDOWS:
        subprocess.Popen(["cmd", "/c", "start", titulo, "cmd", "/k", *map(str, cmd)],
                         cwd=str(cwd or ROOT), env=entorno)
        return
    terminal = which("x-terminal-emulator") or which("gnome-terminal") or which("konsole")
    if os.environ.get("DISPLAY") and terminal:
        subprocess.Popen([terminal, "--", *map(str, cmd)], cwd=str(cwd or ROOT), env=entorno)
        return
    nombre = "".join(ch if ch.isalnum() else "-" for ch in titulo.lower())
    log = LOGS_DIR / f"{nombre}.log"
    en_segundo_plano(cmd, log, cwd, env)
    ui.info(f"Sin entorno grafico: corriendo en segundo plano. Log: {log}")


def gestor_paquetes() -> str | None:
    """apt | dnf | yum (Linux)."""
    for g in ("apt-get", "dnf", "yum"):
        if which(g):
            return g
    return None


def os_release() -> dict[str, str]:
    datos = {}
    try:
        for linea in Path("/etc/os-release").read_text().splitlines():
            if "=" in linea:
                k, v = linea.split("=", 1)
                datos[k] = v.strip().strip('"')
    except OSError:
        pass
    return datos
