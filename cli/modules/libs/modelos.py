"""Modelo de IA local (GGUF) que usa la app movil (core/ai/local_llm_manager.dart)."""
from __future__ import annotations

import os
import urllib.request
from pathlib import Path

from cli.core import shell, ui
from cli.core.paths import MODELS_DIR, asegurar, rel

PAQUETE_APP = "com.example.movil"
# Mismo modelo que Movil/lib/core/ai/local_llm_manager.dart (no es configuracion del servidor)
MODELO_URL = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf?download=true"
MODELO_ARCHIVO = "qwen_0.5b_q4.gguf"


def ruta() -> Path:
    return MODELS_DIR / MODELO_ARCHIVO


def descargar() -> None:
    """Descarga el modelo con reanudacion (Range) a .setup/models."""
    asegurar(MODELS_DIR)
    destino = ruta()
    parcial = destino.with_suffix(destino.suffix + ".part")
    url = MODELO_URL
    inicio = parcial.stat().st_size if parcial.exists() else 0
    if destino.exists():
        ui.ok(f"Ya descargado: {rel(destino)} ({destino.stat().st_size / 1_048_576:.0f} MB)")
        return
    req = urllib.request.Request(url, headers={"User-Agent": "arquis-cli", **({"Range": f"bytes={inicio}-"} if inicio else {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        total = int(r.headers.get("Content-Length") or 0) + (inicio if r.status == 206 else 0)
        if r.status != 206:
            inicio = 0
        with parcial.open("ab" if inicio else "wb") as f:
            hecho = inicio
            while True:
                bloque = r.read(1 << 20)
                if not bloque:
                    break
                f.write(bloque)
                hecho += len(bloque)
                ui.barra(hecho, total, "modelo")
    print()
    parcial.replace(destino)
    ui.ok(f"Modelo en {rel(destino)}")


def enviar_dispositivo() -> None:
    """Copia el modelo al almacenamiento de la app (build debug) para no descargarlo en el telefono."""
    if not ruta().exists():
        descargar()
    adb = shell.requerir("adb", ayuda="winget install Google.PlatformTools")
    dev = os.environ.get("ANDROID_DEVICE", "")
    pre = [adb, *(["-s", dev] if dev else [])]
    nombre = ruta().name
    shell.run([*pre, "push", ruta(), f"/data/local/tmp/{nombre}"])
    shell.run([*pre, "shell", "run-as", PAQUETE_APP, "sh", "-c",
               f"mkdir -p app_flutter && cp /data/local/tmp/{nombre} app_flutter/{nombre}"])
    shell.run([*pre, "shell", "rm", f"/data/local/tmp/{nombre}"], check=False)
    ui.ok("Modelo copiado a la app.")


def eliminar() -> None:
    for p in MODELS_DIR.glob("*") if MODELS_DIR.exists() else []:
        if ui.confirmar(f"¿Eliminar {p.name} ({p.stat().st_size / 1_048_576:.0f} MB)?"):
            p.unlink()
