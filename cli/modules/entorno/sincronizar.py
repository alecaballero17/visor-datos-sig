"""Propaga el .env a lo que lo necesita (variables .NET, app movil)."""
from __future__ import annotations

import re

from cli.core import env, ui
from cli.core.paths import MOVIL, SETUP_DIR, asegurar, rel

MOVIL_ENV = MOVIL / ".env"
MOVIL_ENV_ASSET = MOVIL / ".env.example"   # main.dart carga este asset


def contenido_movil(cfg: dict[str, str] | None = None) -> str:
    cfg = cfg or env.cargar()
    return (f"API_URL_LOCAL={env.url_api_movil(cfg, android=False)}\n"
            f"API_URL_ANDROID={env.url_api_movil(cfg, android=True)}\n")


def movil() -> None:
    """Escribe Movil/.env con la URL publica de la API (API_DOMAIN o WEB_DOMAIN/api)."""
    MOVIL_ENV.write_text(contenido_movil(), encoding="utf-8", newline="\n")
    ui.ok(f"Escrito {rel(MOVIL_ENV)}")
    print("  " + contenido_movil().replace("\n", "\n  ").rstrip())


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
