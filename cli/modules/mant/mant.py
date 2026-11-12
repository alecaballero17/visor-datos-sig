"""Mantenimiento: limpieza, puertos e informacion del proyecto."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from cli.core import env, shell, ui
from cli.core.paths import ARTIFACTS, LOGS_DIR, ROOT, TMP_DIR


def _tam(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.exists() else 0


def limpiar() -> None:
    """Borra temporales, logs de desarrollo, artifacts y __pycache__."""
    objetivos = [("Temporales (.setup/tmp)", TMP_DIR), ("Logs de desarrollo (.setup/logs)", LOGS_DIR),
                 ("Artefactos (artifacts/)", ARTIFACTS)]
    pycache = [p for p in ROOT.rglob("__pycache__") if ".venv" not in p.parts]
    for nombre, ruta in objetivos:
        if ruta.exists() and ui.confirmar(f"¿Borrar {nombre} ({_tam(ruta) / 1_048_576:.1f} MB)?", True):
            shutil.rmtree(ruta, ignore_errors=True)
            ui.ok(f"{nombre} eliminado.")
    for p in pycache:
        shutil.rmtree(p, ignore_errors=True)
    ui.ok(f"{len(pycache)} carpetas __pycache__ eliminadas.")


def puertos() -> None:
    """Que proceso usa los puertos de Arquis (y permite liberarlos)."""
    cfg = env.cargar()
    lista = [cfg["BACKEND_PORT"], cfg["FRONTEND_PORT"], cfg["NGINX_PORT"]]
    if not shell.ES_WINDOWS:
        for p in lista:
            print(shell.salida(["sh", "-c", f"ss -ltnp 'sport = :{p}'"]))
        return
    texto = shell.salida(["netstat", "-ano", "-p", "TCP"])
    filas, pids = [], {}
    for linea in texto.splitlines():
        m = re.search(r"TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)", linea)
        if m and m.group(1) in lista:
            pid = m.group(2)
            nombre = shell.salida(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"]).split(",")[0].strip('"')
            filas.append([m.group(1), pid, nombre])
            pids[m.group(1)] = pid
    if not filas:
        ui.ok("Ningun puerto de Arquis esta ocupado.")
        return
    ui.tabla(sorted(set(map(tuple, filas))), ["Puerto", "PID", "Proceso"])
    if ui.confirmar("¿Terminar alguno de estos procesos?"):
        p = ui.preguntar("Puerto a liberar")
        if p in pids:
            shell.run(["taskkill", "/PID", pids[p], "/T", "/F"], check=False)


def info() -> None:
    """Version, rama, tamanos y componentes del proyecto."""
    git = lambda *a: shell.salida(["git", *a], cwd=ROOT)
    filas = [
        ["Rama", git("rev-parse", "--abbrev-ref", "HEAD")],
        ["Commit", git("log", "-1", "--format=%h %s (%cr)")],
        ["Cambios sin commit", str(len(git("status", "--porcelain").splitlines()))],
        ["Entorno", env.get("ARQUIS_ENV")],
        [".NET SDK", shell.salida([shell.dotnet(), "--version"])],
    ]
    for nombre, patron, carpeta in [("C# (backend/frontend)", "*.cs", "src"), ("Razor", "*.razor", "src"),
                                     ("Dart (movil)", "*.dart", "Movil/lib"), ("Python (editor)", "*.py", "sig_vector_studio"),
                                     ("SQL", "*.sql", "02_BaseDatos")]:
        archivos = [p for p in (ROOT / carpeta).rglob(patron) if "bin" not in p.parts and "obj" not in p.parts]
        lineas = sum(len(p.read_text(encoding="utf-8", errors="ignore").splitlines()) for p in archivos)
        filas.append([nombre, f"{len(archivos)} archivos · {lineas:,} lineas".replace(",", ".")])
    ui.tabla(filas, ["", ""])
