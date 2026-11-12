"""Instalacion de herramientas del sistema.

Linux (apt/dnf): agrega el repositorio oficial de Microsoft (para mssql-tools18
y .NET) y usa dotnet-install.sh si el paquete dotnet-sdk-10.0 no esta disponible.
Windows: winget.
"""
from __future__ import annotations

from cli.core import shell, ui

from .requisitos import Herramienta, aplicables, faltantes

DOTNET_INSTALL = "https://dot.net/v1/dotnet-install.sh"


# ── Linux ───────────────────────────────────────────────────────────────────────
def _repo_microsoft() -> None:
    """Registra packages.microsoft.com segun la distribucion."""
    os_r = shell.os_release()
    distro, version = os_r.get("ID", ""), os_r.get("VERSION_ID", "")
    gestor = shell.gestor_paquetes()
    if gestor == "apt-get":
        if shell.salida(["sh", "-c", "ls /etc/apt/sources.list.d/ | grep -i microsoft"]):
            return
        familia = distro if distro in ("ubuntu", "debian") else ("ubuntu" if "ubuntu" in os_r.get("ID_LIKE", "") else "debian")
        if familia == "debian":
            version = version.split(".")[0]
        url = f"https://packages.microsoft.com/config/{familia}/{version}/packages-microsoft-prod.deb"
        ui.info(f"Registrando repositorio de Microsoft ({familia} {version})")
        shell.run(["curl", "-fsSL", "-o", "/tmp/packages-microsoft-prod.deb", url])
        shell.run(shell.sudo(["dpkg", "-i", "/tmp/packages-microsoft-prod.deb"]))
        shell.run(shell.sudo(["apt-get", "update"]))
    elif gestor in ("dnf", "yum"):
        if shell.salida(["sh", "-c", "ls /etc/yum.repos.d/ | grep -i -E 'microsoft|mssql'"]):
            return
        mayor = version.split(".")[0] or "9"
        url = f"https://packages.microsoft.com/config/rhel/{mayor}/prod.repo"
        ui.info(f"Registrando repositorio de Microsoft (rhel {mayor})")
        shell.run(shell.sudo(["curl", "-fsSL", "-o", "/etc/yum.repos.d/microsoft-prod.repo", url]))


def _instalar_paquetes(paquetes: list[str]) -> bool:
    gestor = shell.gestor_paquetes()
    if not gestor:
        raise ui.Fallo("No se encontro apt ni dnf. Instale manualmente: " + " ".join(paquetes))
    cmd = [gestor, "install", "-y", *paquetes]
    # mssql-tools18 exige aceptar la licencia
    cmd = ["env", "ACCEPT_EULA=Y", *cmd]
    return shell.run(shell.sudo(cmd), check=False).returncode == 0


def _dotnet_script() -> None:
    """Instala .NET 10 con el script oficial en /usr/share/dotnet."""
    ui.info("Instalando .NET 10 con dotnet-install.sh")
    shell.run(["curl", "-fsSL", "-o", "/tmp/dotnet-install.sh", DOTNET_INSTALL])
    shell.run(shell.sudo(["bash", "/tmp/dotnet-install.sh", "--channel", "10.0", "--install-dir", "/usr/share/dotnet"]))
    shell.run(shell.sudo(["ln", "-sf", "/usr/share/dotnet/dotnet", "/usr/bin/dotnet"]))


def _instalar_linux(lista: list[Herramienta]) -> None:
    gestor = shell.gestor_paquetes()
    if any(h.clave in ("dotnet", "sqlcmd") for h in lista):
        if not shell.which("curl"):
            _instalar_paquetes(["curl", "ca-certificates"])
        _repo_microsoft()
    for h in lista:
        paquetes = h.apt if gestor == "apt-get" else h.dnf
        if not paquetes:
            ui.warn(f"{h.nombre}: instalacion manual → {h.url}")
            continue
        ui.seccion(h.nombre)
        bien = _instalar_paquetes(paquetes)
        if h.clave == "dotnet" and (not bien or not h.ruta()):
            _dotnet_script()
        elif h.clave == "sqlcmd" and bien:
            for exe in ("sqlcmd", "bcp"):
                shell.run(shell.sudo(["ln", "-sf", f"/opt/mssql-tools18/bin/{exe}", f"/usr/local/bin/{exe}"]), check=False)
        elif h.clave == "docker" and bien:
            shell.run(shell.sudo(["systemctl", "enable", "--now", "docker"]), check=False)
        elif not bien:
            ui.error(f"No se pudo instalar {h.nombre}.")


# ── Windows ─────────────────────────────────────────────────────────────────────
def _instalar_windows(lista: list[Herramienta]) -> None:
    winget = shell.requerir("winget", ayuda="Instale 'App Installer' desde Microsoft Store.")
    for h in lista:
        if not h.winget:
            ui.warn(f"{h.nombre}: instalacion manual → {h.url}")
            continue
        shell.run([winget, "install", "--id", h.winget, "-e", "--accept-source-agreements",
                   "--accept-package-agreements", "--silent"], check=False)
    ui.info("Abra una terminal nueva para que el PATH se actualice.")


def _instalar(lista: list[Herramienta]) -> None:
    if not lista:
        ui.ok("No falta nada.")
        return
    ui.info("Se instalara: " + ", ".join(h.nombre for h in lista))
    if not ui.confirmar("¿Continuar?", True):
        return
    (_instalar_windows if shell.ES_WINDOWS else _instalar_linux)(lista)


def instalar_servidor() -> None:
    """Instala lo necesario para un servidor (obligatorias + nginx + fuentes)."""
    lista = [h for h in faltantes(solo_servidor=True) if h.obligatoria or h.clave in ("nginx", "fc-list")]
    _instalar(lista)


def instalar_faltantes() -> None:
    """Instala todas las herramientas que falten (incluye las de desarrollo)."""
    lista = faltantes()
    if not ui.AUTO_YES:
        lista = [h for h in lista if h.obligatoria or ui.confirmar(f"¿Instalar {h.nombre} (opcional)?", False)]
    _instalar(lista)


def instalar_una() -> None:
    """Instala o actualiza una herramienta concreta."""
    opciones = aplicables()
    i = ui.elegir("Herramienta", [f"{h.nombre}  — {h.para}" for h in opciones])
    _instalar([opciones[i]])


def actualizar_sistema() -> None:
    """Actualiza los paquetes del sistema (apt upgrade / dnf upgrade / winget upgrade)."""
    if shell.ES_WINDOWS:
        shell.run(["winget", "upgrade", "--all", "--accept-source-agreements", "--accept-package-agreements"], check=False)
        return
    gestor = shell.gestor_paquetes()
    if gestor == "apt-get":
        shell.run(shell.sudo(["apt-get", "update"]))
        shell.run(shell.sudo(["env", "ACCEPT_EULA=Y", "apt-get", "upgrade", "-y"]))
    elif gestor:
        shell.run(shell.sudo(["env", "ACCEPT_EULA=Y", gestor, "upgrade", "-y"]))
