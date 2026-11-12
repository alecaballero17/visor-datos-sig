"""Librerias web del visor (CDN) descargadas a wwwroot/lib para funcionar sin Internet.

`descargar` baja los archivos; `modo-local` reescribe las referencias de
App.razor y wwwroot/js a /lib/...; `modo-cdn` lo deshace.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from cli.core import ui
from cli.core.paths import FRONTEND, WWWROOT, rel

DESTINO = WWWROOT / "lib"
MANIFIESTO = DESTINO / "arquis-libs.json"


@dataclass(frozen=True)
class Libreria:
    nombre: str
    version: str
    base: str                      # URL base real
    archivos: tuple[str, ...]
    prefijos_en_codigo: tuple[str, ...]   # como aparece la base en el codigo (p. ej. @@ en Razor)

    @property
    def local(self) -> str:
        return f"/lib/{self.nombre}/{self.version}/"


LIBRERIAS = [
    Libreria("leaflet", "1.9.4", "https://unpkg.com/leaflet@1.9.4/dist/",
             ("leaflet.js", "leaflet.css", "images/layers.png", "images/layers-2x.png", "images/marker-icon.png",
              "images/marker-icon-2x.png", "images/marker-shadow.png"),
             ("https://unpkg.com/leaflet@1.9.4/dist/",)),
    Libreria("bootstrap", "5.3.3", "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/",
             ("css/bootstrap.min.css", "js/bootstrap.bundle.min.js"),
             ("https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/",)),
    Libreria("bootstrap-icons", "1.11.3", "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/",
             ("bootstrap-icons.min.css", "fonts/bootstrap-icons.woff2", "fonts/bootstrap-icons.woff"),
             ("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/",)),
    Libreria("signalr", "10.0.0", "https://cdn.jsdelivr.net/npm/@microsoft/signalr@10.0.0/dist/browser/",
             ("signalr.min.js",),
             ("https://cdn.jsdelivr.net/npm/@@microsoft/signalr@10.0.0/dist/browser/",
              "https://cdn.jsdelivr.net/npm/@microsoft/signalr@10.0.0/dist/browser/")),
    Libreria("three", "r128", "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/",
             ("three.min.js",), ("https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/",)),
]


def _fuentes() -> list[Path]:
    return [p for p in [FRONTEND / "App.razor", *FRONTEND.rglob("*.razor"), *(WWWROOT / "js").glob("*.js")]
            if p.is_file()]


def estado() -> None:
    """Librerias, si estan descargadas y donde se referencian."""
    filas = []
    textos = {p: p.read_text(encoding="utf-8", errors="replace") for p in set(_fuentes())}
    for lib in LIBRERIAS:
        carpeta = DESTINO / lib.nombre / lib.version
        descargada = all((carpeta / a).exists() for a in lib.archivos)
        usos_cdn = [p.name for p, t in textos.items() if any(pre in t for pre in lib.prefijos_en_codigo)]
        usos_local = [p.name for p, t in textos.items() if lib.local in t]
        modo = "cdn" if usos_cdn else ("local" if usos_local else "-")
        filas.append([lib.nombre, lib.version, ui.c("si", ui.C.GREEN) if descargada else ui.c("no", ui.C.GRAY),
                      modo, ", ".join(sorted(set(usos_cdn or usos_local)))])
    ui.tabla(filas, ["Libreria", "Version", "Descargada", "Modo", "Usada en"])


def descargar() -> None:
    """Descarga todas las librerias a wwwroot/lib."""
    manifiesto = {}
    for lib in LIBRERIAS:
        carpeta = DESTINO / lib.nombre / lib.version
        for archivo in lib.archivos:
            destino = carpeta / archivo
            destino.parent.mkdir(parents=True, exist_ok=True)
            url = lib.base + archivo
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "arquis-cli"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    datos = r.read()
            except Exception as e:  # noqa: BLE001
                ui.error(f"{lib.nombre}/{archivo}: {e}")
                continue
            destino.write_bytes(datos)
            manifiesto[f"{lib.nombre}/{lib.version}/{archivo}"] = {
                "url": url, "sha256": hashlib.sha256(datos).hexdigest(), "bytes": len(datos)}
        ui.ok(f"{lib.nombre} {lib.version}")
    MANIFIESTO.write_text(json.dumps(manifiesto, indent=2), encoding="utf-8")
    ui.info(f"Manifiesto con hashes: {rel(MANIFIESTO)}")


def verificar() -> None:
    """Comprueba los hashes de los archivos descargados."""
    if not MANIFIESTO.exists():
        raise ui.Fallo("No hay librerias descargadas.")
    datos = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    malos = [k for k, v in datos.items()
             if not (DESTINO / k).exists() or hashlib.sha256((DESTINO / k).read_bytes()).hexdigest() != v["sha256"]]
    for k in malos:
        ui.error(f"Alterado o ausente: {k}")
    if not malos:
        ui.ok(f"{len(datos)} archivos verificados.")


def _reescribir(a_local: bool) -> None:
    cambios = 0
    for p in set(_fuentes()):
        texto = original = p.read_text(encoding="utf-8")
        for lib in LIBRERIAS:
            if a_local:
                for pre in lib.prefijos_en_codigo:
                    texto = texto.replace(pre, lib.local)
            else:
                pre = lib.prefijos_en_codigo[0] if p.suffix == ".razor" else lib.prefijos_en_codigo[-1]
                texto = texto.replace(lib.local, pre)
        if texto != original:
            p.write_text(texto, encoding="utf-8")
            ui.ok(f"Actualizado {rel(p)}")
            cambios += 1
    ui.info(f"{cambios} archivos modificados.")


def modo_local() -> None:
    """Usa las librerias locales (sin Internet). Modifica App.razor/js."""
    faltan = [l.nombre for l in LIBRERIAS if not all((DESTINO / l.nombre / l.version / a).exists() for a in l.archivos)]
    if faltan:
        ui.warn("Faltan: " + ", ".join(faltan) + ". Descargando...")
        descargar()
    if ui.confirmar("Se reescribiran las URLs CDN por /lib/... en el codigo del frontend. ¿Continuar?", True):
        _reescribir(True)


def modo_cdn() -> None:
    """Vuelve a las URLs de CDN."""
    _reescribir(False)
