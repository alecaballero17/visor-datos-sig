"""Propaga el .env a lo que lo necesita (variables .NET, app movil)."""
from __future__ import annotations

import re

from cli.core import env, ui
from cli.core.paths import MOVIL, SETUP_DIR, asegurar, rel

MOVIL_ENV = MOVIL / ".env"
MOVIL_ENV_ASSET = MOVIL / ".env.example"   # main.dart carga este asset


_LOCAL = re.compile(r"//(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)")


def api_movil(cfg: dict[str, str] | None = None) -> tuple[str, str] | None:
    """(URL web/escritorio, URL Android) para la app, o None si hay que conservar la del asset.

    La app se compila en el equipo de desarrollo, cuyo .env apunta a localhost; sin
    MOVIL_API_URL no se pisa la API de produccion que trae Movil/.env.example.
    """
    cfg = cfg or env.cargar()
    explicita = cfg.get("MOVIL_API_URL", "").strip().rstrip("/")
    if explicita:
        return explicita, explicita
    local, android = env.url_api_movil(cfg, android=False), env.url_api_movil(cfg, android=True)
    if _LOCAL.search(local) and cfg.get("ARQUIS_ENV") != "Production":
        return None
    return local, android


def contenido_movil(cfg: dict[str, str] | None = None) -> str | None:
    urls = api_movil(cfg)
    if urls is None:
        return None
    return f"API_URL_LOCAL={urls[0]}\nAPI_URL_ANDROID={urls[1]}\n"


def api_del_asset() -> str:
    try:
        for linea in MOVIL_ENV_ASSET.read_text(encoding="utf-8").splitlines():
            if linea.startswith("API_URL_ANDROID="):
                return linea.split("=", 1)[1].strip()
    except OSError:
        pass
    return "?"


def movil() -> None:
    """Escribe Movil/.env con la URL publica de la API (API_DOMAIN o WEB_DOMAIN/api)."""
    contenido = contenido_movil()
    if contenido is None:
        ui.info(f"El .env es de desarrollo: la app sigue usando {api_del_asset()} (Movil/.env.example).")
        ui.dim("    Para otra API: arquis entorno set MOVIL_API_URL https://.../api")
        return
    MOVIL_ENV.write_text(contenido, encoding="utf-8", newline="\n")
    ui.ok(f"Escrito {rel(MOVIL_ENV)}")
    print("  " + contenido.replace("\n", "\n  ").rstrip())


def mostrar_dotnet() -> None:
    """Variables exactas que recibiran backend y frontend."""
    ui.seccion("Arquis.Backend")
    for k, v in env.entorno_backend().items():
        print(f"  {k}={re.sub(r'Password=[^;]*', 'Password=••••', v)}")
    ui.seccion("Arquis.Frontend")
    for k, v in env.entorno_frontend().items():
        print(f"  {k}={v}")


def exportar_shell() -> None:
    """Genera .setup/env.sh y .setup/env.ps1 para cargar las variables a mano."""
    asegurar(SETUP_DIR)
    variables = {**env.entorno_frontend(), **env.entorno_backend()}
    variables.pop("ASPNETCORE_URLS", None)
    sh = SETUP_DIR / "env.sh"
    sh.write_text("# source .setup/env.sh\n" + "".join(
        f"export {k}='{v.replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n" for k, v in variables.items()),
        encoding="utf-8", newline="\n")
    ps = SETUP_DIR / "env.ps1"
    ps.write_text("# . ./.setup/env.ps1\n" + "".join(
        f"$env:{k} = '{v.replace(chr(39), chr(39) * 2)}'\n" for k, v in variables.items()), encoding="utf-8")
    ui.ok(f"Generados {rel(sh)} y {rel(ps)} (contienen la contrasena: no los comparta)")
