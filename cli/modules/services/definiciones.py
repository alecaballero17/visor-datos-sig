"""Que es cada servicio: ejecutable, carpeta, puerto, logs y variables."""
from __future__ import annotations

import socket
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from cli.core import env, shell


def dir_instalacion() -> Path:
    return Path(env.get("DEPLOY_DIR"))


def dir_actual() -> Path:
    """Version activa (junction/symlink 'current' gestionado por el despliegue)."""
    return dir_instalacion() / "current"


def dir_logs() -> Path:
    return dir_instalacion() / "logs"


def dir_nginx() -> Path:
    return dir_instalacion() / "nginx"


@dataclass
class Servicio:
    clave: str                 # backend | frontend | nginx
    titulo: str
    puerto: int
    salud: str                 # ruta HTTP para comprobar
    texto_salud: str           # texto esperado en la respuesta
    carpeta: Path
    ejecutable: str
    argumentos: list[str] = field(default_factory=list)
    entorno: dict[str, str] = field(default_factory=dict)

    @property
    def nombre(self) -> str:
        prefijo = env.get("SERVICE_PREFIX") or "Arquis"
        return f"{prefijo}{self.clave.capitalize()}" if shell.ES_WINDOWS else f"{prefijo.lower()}-{self.clave}"

    @property
    def log_out(self) -> Path:
        return dir_logs() / f"{self.clave}.out.log"

    @property
    def log_err(self) -> Path:
        return dir_logs() / f"{self.clave}.err.log"

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.puerto}{self.salud}"

    def instalado_en_disco(self) -> bool:
        if self.clave == "nginx":
            return Path(self.ejecutable).exists()
        return (self.carpeta / self.argumentos[0]).exists() if self.argumentos else False


def _dotnet_app(clave: str, titulo: str, dll: str, puerto: int, salud: str, texto: str, entorno: dict) -> Servicio:
    return Servicio(clave, titulo, puerto, salud, texto, dir_actual() / clave,
                    shell.which("dotnet", shell.DOTNET_EXTRAS) or "dotnet", [dll], entorno)


def backend() -> Servicio:
    cfg = env.cargar()
    return _dotnet_app("backend", "API (Arquis.Backend)", "Arquis.Backend.dll", int(cfg["BACKEND_PORT"]),
                       "/health", "Arquis.Backend", env.entorno_backend(cfg))


def frontend() -> Servicio:
    cfg = env.cargar()
    return _dotnet_app("frontend", "Visor web (Arquis.Frontend)", "Arquis.Frontend.dll", int(cfg["FRONTEND_PORT"]),
                       "/", "Arquis", env.entorno_frontend(cfg))


def nginx() -> Servicio:
    cfg = env.cargar()
    if shell.ES_WINDOWS:
        d = dir_nginx()
        return Servicio("nginx", "Proxy nginx", int(cfg["NGINX_PORT"]), "/health", "Arquis.Backend", d,
                        str(d / "nginx.exe"), ["-p", str(d) + "\\", "-c", "conf/nginx.conf"])
    return Servicio("nginx", "Proxy nginx", int(cfg["NGINX_PORT"]), "/health", "Arquis.Backend",
                    Path("/etc/nginx"), shell.which("nginx") or "/usr/sbin/nginx")


def obtener(clave: str) -> Servicio:
    return {"backend": backend, "frontend": frontend, "nginx": nginx}[clave]()


def todos(incluir_nginx: bool | None = None) -> list[Servicio]:
    if incluir_nginx is None:
        incluir_nginx = env.es_verdad("NGINX_ENABLED")
    lista = [backend(), frontend()]
    if incluir_nginx:
        lista.append(nginx())
    return lista


# -- comprobaciones de red ----------------------------------------------------
def puerto_abierto(puerto: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, puerto), timeout=1):
            return True
    except OSError:
        return False


def _peticion_salud(s: Servicio) -> tuple[urllib.request.Request, object]:
    """nginx con HTTPS redirige el puerto 80 a https://<dominio>: se prueba directamente
    https://127.0.0.1 con el Host del visor (certificado local, sin verificar: es la misma maquina)."""
    if s.clave != "nginx":
        return urllib.request.Request(s.url), None
    cfg = env.cargar()
    dominio = cfg.get("WEB_DOMAIN", "")
    cabeceras = {"Host": dominio} if dominio and dominio != "_" else {}
    if cfg.get("NGINX_SSL_CERT") and cfg.get("HTTPS", "none") != "none":
        import ssl
        contexto = ssl.create_default_context()
        contexto.check_hostname = False
        contexto.verify_mode = ssl.CERT_NONE
        return urllib.request.Request("https://127.0.0.1" + s.salud, headers=cabeceras), contexto
    return urllib.request.Request(s.url, headers=cabeceras), None


def salud(s: Servicio, timeout: float = 3) -> tuple[bool, str]:
    try:
        peticion, contexto = _peticion_salud(s)
        with urllib.request.urlopen(peticion, timeout=timeout, context=contexto) as r:
            cuerpo = r.read(4096).decode("utf-8", "replace")
            ok = r.status == 200 and s.texto_salud in cuerpo
            return ok, f"HTTP {r.status}" + ("" if ok else " (respuesta inesperada)")
    except Exception as e:  # noqa: BLE001
        return False, str(getattr(e, "reason", e))
