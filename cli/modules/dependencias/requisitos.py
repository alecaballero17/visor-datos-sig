"""Herramientas externas que necesita el proyecto y diagnostico de versiones."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from cli.core import shell, ui
from cli.core.paths import VENV
from cli.core.sql import SQLCMD_EXTRAS


@dataclass
class Herramienta:
    clave: str
    nombre: str
    comando: str
    args_version: list[str]
    para: str
    obligatoria: bool = True
    extras: list[str] = field(default_factory=list)
    minimo: str | None = None
    solo: str | None = None               # "linux" | "windows" | None (ambos)
    servidor: bool = True                 # hace falta en un servidor de produccion
    apt: list[str] = field(default_factory=list)
    dnf: list[str] = field(default_factory=list)
    winget: str | None = None
    url: str = ""

    def aplica(self) -> bool:
        return self.solo is None or (self.solo == "windows") == shell.ES_WINDOWS

    def ruta(self) -> str | None:
        return shell.which(self.comando, self.extras)

    def version(self) -> str:
        exe = self.ruta()
        if not exe:
            return ""
        texto = shell.salida([exe, *self.args_version])
        m = re.search(r"\d+\.\d+(\.\d+)?", texto)
        return m.group(0) if m else ("ok" if texto or exe else "?")


HERRAMIENTAS = [
    Herramienta("dotnet", ".NET SDK 10", "dotnet", ["--version"], "compilar/ejecutar backend y frontend, migraciones",
                extras=shell.DOTNET_EXTRAS, minimo="10.", apt=["dotnet-sdk-10.0"], dnf=["dotnet-sdk-10.0"],
                winget="Microsoft.DotNet.SDK.10", url="https://dotnet.microsoft.com/download/dotnet/10.0"),
    Herramienta("sqlcmd", "sqlcmd (mssql-tools18)", "sqlcmd", ["-?"], "migrar capas, scripts, respaldos, consultas",
                extras=SQLCMD_EXTRAS, apt=["mssql-tools18", "unixodbc-dev"], dnf=["mssql-tools18", "unixODBC-devel"],
                winget="Microsoft.Sqlcmd", url="https://learn.microsoft.com/sql/linux/sql-server-linux-setup-tools"),
    Herramienta("python", "Python 3 + venv", "python3" if not shell.ES_WINDOWS else "python", ["--version"],
                "esta CLI e importador SHP", apt=["python3", "python3-venv", "python3-pip"], dnf=["python3", "python3-pip"],
                winget="Python.Python.3.12", url="https://www.python.org/downloads/"),
    Herramienta("nginx", "nginx", "nginx", ["-v"], "proxy inverso publico", obligatoria=False, solo="linux",
                apt=["nginx"], dnf=["nginx"]),
    Herramienta("fc-list", "fontconfig + fuentes", "fc-list", ["--version"], "PDF de reportes (QuestPDF usa fuentes del sistema)",
                obligatoria=False, solo="linux", apt=["fontconfig", "fonts-dejavu-core"], dnf=["fontconfig", "dejavu-sans-fonts"]),
    Herramienta("curl", "curl", "curl", ["--version"], "descargas e instalacion de repositorios", solo="linux",
                apt=["curl", "ca-certificates", "gnupg"], dnf=["curl", "ca-certificates"]),
    Herramienta("git", "Git", "git", ["--version"], "actualizar codigo (deploy actualizar)", obligatoria=False,
                apt=["git"], dnf=["git"], winget="Git.Git"),
    Herramienta("docker", "Docker", "docker", ["--version"], "SQL Server en contenedor (opcional)", obligatoria=False,
                apt=["docker.io"], dnf=["docker"], url="https://docs.docker.com/engine/install/"),
    Herramienta("localdb", "SQL Server LocalDB", "SqlLocalDB", ["v"], "base local de desarrollo", obligatoria=False,
                solo="windows", servidor=False, extras=shell.LOCALDB_EXTRAS,
                url="https://learn.microsoft.com/sql/database-engine/configure-windows/sql-server-express-localdb"),
    Herramienta("node", "Node.js", "node", ["--version"], "pruebas realtime", obligatoria=False, servidor=False,
                apt=["nodejs"], dnf=["nodejs"], winget="OpenJS.NodeJS.LTS"),
    Herramienta("flutter", "Flutter SDK", "flutter", ["--version"], "app movil", obligatoria=False, servidor=False,
                url="https://docs.flutter.dev/get-started/install"),
    Herramienta("adb", "Android platform-tools", "adb", ["version"], "instalar APK", obligatoria=False, servidor=False,
                apt=["adb"], dnf=["android-tools"], winget="Google.PlatformTools"),
]


def aplicables() -> list[Herramienta]:
    return [h for h in HERRAMIENTAS if h.aplica()]


def faltantes(solo_obligatorias: bool = False, solo_servidor: bool = False) -> list[Herramienta]:
    return [h for h in aplicables()
            if not h.ruta() and (h.obligatoria or not solo_obligatorias) and (h.servidor or not solo_servidor)]


def _sql_server_local() -> str:
    if shell.ES_LINUX and shell.which("systemctl"):
        estado = shell.salida(["systemctl", "is-active", "mssql-server"])
        if estado:
            return f"mssql-server: {estado}"
    if shell.which("docker"):
        nombres = shell.salida(["docker", "ps", "--format", "{{.Names}} {{.Image}}"])
        sql = [l for l in nombres.splitlines() if "mssql" in l]
        if sql:
            return "contenedor: " + ", ".join(l.split()[0] for l in sql)
    return "no detectado en este equipo (puede ser remoto)"


def diagnostico() -> bool:
    """Revisa las herramientas necesarias en este sistema."""
    so = "Windows" if shell.ES_WINDOWS else (shell.os_release().get("PRETTY_NAME") or "Linux")
    ui.info(f"Sistema: {so}")
    filas, faltan = [], []
    for h in aplicables():
        ruta = h.ruta()
        ver = h.version() if ruta else ""
        if not ruta:
            estado = ui.c("falta", ui.C.RED if h.obligatoria else ui.C.YELLOW)
            faltan += [h] if h.obligatoria else []
        elif h.minimo and not ver.startswith(h.minimo):
            estado = ui.c(f"requiere {h.minimo}x", ui.C.YELLOW)
            faltan += [h] if h.obligatoria else []
        else:
            estado = ui.c("ok", ui.C.GREEN)
        uso = h.para + ("" if h.servidor else ui.c("  (solo desarrollo)", ui.C.GRAY))
        filas.append([h.nombre, ver or "-", estado, uso])
    ui.tabla(filas, ["Herramienta", "Version", "Estado", "Uso"])

    ui.seccion("Detalles")
    dn = shell.which("dotnet", shell.DOTNET_EXTRAS)
    if dn:
        ui.info("SDKs .NET: " + (", ".join(l.split()[0] for l in shell.salida([dn, "--list-sdks"]).splitlines()) or "ninguno"))
        ui.info("Runtimes ASP.NET: " + (", ".join(l.split()[1] for l in shell.salida([dn, "--list-runtimes"]).splitlines()
                                               if "AspNetCore" in l) or "ninguno"))
    ui.info(f"SQL Server local: {_sql_server_local()}")
    ui.info(f"Entorno virtual .venv: {'si' if VENV.exists() else 'no'} → {shell.python()}")
    if faltan:
        ui.warn("Faltan obligatorias: " + ", ".join(h.nombre for h in faltan) + ". Ejecute: arquis deps instalar")
        return False
    ui.ok("Requisitos obligatorios presentes.")
    return True


def requerir_obligatorias() -> None:
    faltan = [h.nombre for h in faltantes(solo_obligatorias=True)]
    if faltan:
        raise ui.Fallo("Faltan herramientas: " + ", ".join(faltan) + ". Ejecute: arquis deps instalar")
