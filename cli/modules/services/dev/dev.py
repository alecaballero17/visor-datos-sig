"""Modo desarrollo: backend y frontend desde el codigo fuente, en segundo plano.

Sustituye a iniciar.ps1 / LEVANTAR_ARQUIS.cmd. Usa el .env, guarda PIDs en
.setup/pids y logs en .setup/logs (seguibles en vivo).
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from cli.core import env, shell, ui
from cli.core.paths import BACKEND, FRONTEND, LOGS_DIR, PIDS_DIR, ROOT, asegurar

from ..definiciones import puerto_abierto
from ..logs import mostrar_ultimas, seguir

APPS = {
    "backend": (BACKEND, "/health", "Arquis.Backend"),
    "frontend": (FRONTEND, "/", "Arquis"),
}


def _puerto(clave: str) -> int:
    return int(env.get("BACKEND_PORT" if clave == "backend" else "FRONTEND_PORT"))


def _env(clave: str) -> dict[str, str]:
    return env.entorno_backend() if clave == "backend" else env.entorno_frontend()


def _pid(clave: str) -> int | None:
    f = PIDS_DIR / f"{clave}.pid"
    try:
        return int(f.read_text().strip())
    except (OSError, ValueError):
        return None


def _vivo(pid: int | None) -> bool:
    if not pid:
        return False
    if shell.ES_WINDOWS:
        return str(pid) in shell.salida(["tasklist", "/FI", f"PID eq {pid}", "/NH"])
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _logs() -> dict[str, Path]:
    return {c: LOGS_DIR / f"dev-{c}.log" for c in APPS}



def _sano(clave: str) -> bool:
    import urllib.request
    _, ruta, texto = APPS[clave]
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{_puerto(clave)}{ruta}", timeout=2) as r:
            return r.status == 200 and texto in r.read(4096).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return False


def iniciar_uno(clave: str) -> None:
    asegurar(LOGS_DIR, PIDS_DIR)
    proyecto, _, _ = APPS[clave]
    if _vivo(_pid(clave)) or _sano(clave):
        ui.info(f"{clave} ya esta en ejecucion en el puerto {_puerto(clave)}.")
        return
    if puerto_abierto(_puerto(clave)):
        raise ui.Fallo(f"El puerto {_puerto(clave)} esta ocupado por otra aplicacion.")
    shell.run([shell.dotnet(), "build", proyecto, "--nologo", "-v", "q"])
    log = (LOGS_DIR / f"dev-{clave}.log").open("w", encoding="utf-8")
    entorno = dict(os.environ)
    entorno.update(_env(clave))
    flags = 0
    if shell.ES_WINDOWS:
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
    p = subprocess.Popen([shell.dotnet(), "run", "--no-build", "--no-launch-profile", "--project", str(proyecto)],
                         cwd=str(ROOT), env=entorno, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         creationflags=flags, start_new_session=not shell.ES_WINDOWS)
    (PIDS_DIR / f"{clave}.pid").write_text(str(p.pid))
    for _ in range(90):
        if p.poll() is not None:
            mostrar_ultimas({clave: LOGS_DIR / f"dev-{clave}.log"}, 25)
            raise ui.Fallo(f"{clave} termino inesperadamente (codigo {p.returncode}).")
        if _sano(clave):
            ui.ok(f"{clave} listo → {env.url_local(clave)}")
            return
        time.sleep(1)
    raise ui.Fallo(f"{clave} no respondio en 90 s. Revise: arquis services dev logs")


def detener_uno(clave: str) -> None:
    pid = _pid(clave)
    if not _vivo(pid):
        ui.info(f"{clave} no esta en ejecucion (segun PID).")
    else:
        if shell.ES_WINDOWS:
            shell.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, capturar=True, silencioso=True)
        else:
            os.killpg(pid, 15)
        ui.ok(f"{clave} detenido.")
    (PIDS_DIR / f"{clave}.pid").unlink(missing_ok=True)


def iniciar() -> None:
    """Inicia backend y frontend desde el codigo."""
    for c in APPS:
        iniciar_uno(c)
    ui.info(f"Visor: {env.url_local('frontend')}   API: {env.url_local('backend')}/health")


def detener() -> None:
    """Detiene los procesos de desarrollo."""
    for c in reversed(list(APPS)):
        detener_uno(c)


def reiniciar() -> None:
    detener()
    iniciar()


def estado() -> None:
    """PID, puerto y salud de cada proceso."""
    filas = []
    for c in APPS:
        pid = _pid(c)
        filas.append([c, pid if _vivo(pid) else "-", _puerto(c),
                      ui.c("abierto", ui.C.GREEN) if puerto_abierto(_puerto(c)) else ui.c("cerrado", ui.C.GRAY),
                      ui.c("ok", ui.C.GREEN) if _sano(c) else ui.c("sin respuesta", ui.C.RED)])
    ui.tabla(filas, ["App", "PID", "Puerto", "Escucha", "Salud"])


def logs_vivo() -> None:
    """Sigue los logs de desarrollo en tiempo real."""
    seguir(_logs())


def watch() -> None:
    """dotnet watch (recarga en caliente) en ventanas nuevas."""
    for c in APPS:
        proyecto, _, _ = APPS[c]
        shell.nueva_consola([shell.dotnet(), "watch", "--no-launch-profile", "--project", str(proyecto)],
                            env=_env(c), titulo=f"Arquis {c} (watch)")
    ui.ok("Ventanas de dotnet watch abiertas.")


def abrir_navegador() -> None:
    import webbrowser
    webbrowser.open(env.url_local("frontend"))
