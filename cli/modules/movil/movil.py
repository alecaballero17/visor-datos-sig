"""App movil Flutter (Movil/)."""
from __future__ import annotations

import contextlib
import os
import shutil
from datetime import datetime
from pathlib import Path

from cli.core import env, shell, ui
from cli.core.paths import ARTIFACTS, MOVIL, asegurar, rel

from ..entorno.sincronizar import MOVIL_ENV_ASSET, contenido_movil


def _flutter() -> str:
    return shell.requerir("flutter", ayuda="Instale Flutter SDK (arquis deps doctor).")


@contextlib.contextmanager
def _env_temporal():
    """main.dart carga el asset '.env.example': se sustituye durante la compilacion y se restaura."""
    original = MOVIL_ENV_ASSET.read_bytes() if MOVIL_ENV_ASSET.exists() else None
    MOVIL_ENV_ASSET.write_text(contenido_movil(), encoding="utf-8")
    ui.dim(f"API para la app: {env.url_api_movil()}")
    try:
        yield
    finally:
        if original is not None:
            MOVIL_ENV_ASSET.write_bytes(original)


def _dispositivo() -> list[str]:
    dev = os.environ.get("ANDROID_DEVICE", "")   # opcional: elegir dispositivo
    return ["-d", dev] if dev else []


def compilar_apk(release: bool | None = None) -> Path:
    if release is None:
        release = ui.elegir("Tipo", ["Release (firmado/optimizado)", "Debug"], 0) == 0
    modo = "--release" if release else "--debug"
    with _env_temporal():
        shell.run([_flutter(), "build", "apk", modo], cwd=MOVIL)
    nombre = "app-release.apk" if release else "app-debug.apk"
    apk = MOVIL / "build" / "app" / "outputs" / "flutter-apk" / nombre
    asegurar(ARTIFACTS / "movil")
    destino = ARTIFACTS / "movil" / f"arquis-{'release' if release else 'debug'}-{datetime.now():%Y%m%d-%H%M}.apk"
    shutil.copy2(apk, destino)
    ui.ok(f"APK: {rel(destino)} ({destino.stat().st_size / 1_048_576:.1f} MB)")
    return destino


def apk() -> None:
    """Compila el APK con la URL de la API del .env."""
    compilar_apk()


def appbundle() -> None:
    """Compila .aab para Google Play."""
    with _env_temporal():
        shell.run([_flutter(), "build", "appbundle", "--release"], cwd=MOVIL)
    ui.ok("AAB en Movil/build/app/outputs/bundle/release/")


def windows() -> None:
    """Compila la app para escritorio Windows."""
    with _env_temporal():
        shell.run([_flutter(), "build", "windows", "--release"], cwd=MOVIL)


def dispositivos() -> None:
    """Dispositivos y emuladores conectados."""
    shell.run([_flutter(), "devices"], cwd=MOVIL, check=False)


def instalar() -> None:
    """Instala el APK mas reciente en el dispositivo (adb)."""
    apks = sorted((ARTIFACTS / "movil").glob("*.apk"), key=lambda p: p.stat().st_mtime, reverse=True) \
        if (ARTIFACTS / "movil").exists() else []
    if not apks:
        raise ui.Fallo("No hay APK compilado (arquis movil apk).")
    adb = shell.requerir("adb", ayuda="winget install Google.PlatformTools")
    dev = os.environ.get("ANDROID_DEVICE", "")
    shell.run([adb, *(["-s", dev] if dev else []), "install", "-r", apks[0]])
    ui.ok(f"{apks[0].name} instalado.")


def ejecutar() -> None:
    """flutter run en otra ventana (hot reload)."""
    # La consola nueva corre en paralelo: el asset no se puede restaurar automaticamente.
    MOVIL_ENV_ASSET.write_text(contenido_movil(), encoding="utf-8")
    shell.nueva_consola([_flutter(), "run", *_dispositivo()], cwd=MOVIL, titulo="Arquis movil")
    ui.warn("Movil/.env.example quedo con las URLs del .env; restaurelo con git checkout si no desea commitearlo.")


def limpiar() -> None:
    """flutter clean + pub get."""
    shell.run([_flutter(), "clean"], cwd=MOVIL)
    shell.run([_flutter(), "pub", "get"], cwd=MOVIL)


def logs_dispositivo() -> None:
    """Logs del dispositivo en tiempo real (flutter logs)."""
    try:
        shell.run([_flutter(), "logs", *_dispositivo()], cwd=MOVIL, check=False)
    except KeyboardInterrupt:
        pass


def doctor() -> None:
    shell.run([_flutter(), "doctor", "-v"], check=False)
