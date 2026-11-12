"""Versiones instaladas en <DEPLOY_DIR>/releases/<id> y enlace 'current'.

    C:\\Arquis\\
      current  →  releases\\20261112-153000   (junction / symlink)
      releases\\20261112-153000\\{backend,frontend,release.json}
      logs\\  nginx\\  tools\\  deploys.jsonl
"""
from __future__ import annotations

import getpass
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from cli.core import env, shell, ui
from cli.core.paths import ARTIFACTS, ROOT

from ..services.compilacion.compilar import publicar
from ..services.definiciones import dir_actual, dir_instalacion


def dir_releases() -> Path:
    return dir_instalacion() / "releases"


def _git(*args: str) -> str:
    return shell.salida(["git", *args], cwd=ROOT) if shell.which("git") else ""


def listar_ids() -> list[str]:
    d = dir_releases()
    return sorted((p.name for p in d.iterdir() if p.is_dir()), reverse=True) if d.exists() else []


def activa() -> str | None:
    c = dir_actual()
    if not c.exists():
        return None
    try:
        return Path(os.path.realpath(c)).name
    except OSError:
        return None


def crear() -> Path:
    """Publica backend y frontend en una version nueva (no la activa)."""
    rid = datetime.now().strftime("%Y%m%d-%H%M%S")
    destino = dir_releases() / rid
    shell.requerir_escritura(dir_instalacion())
    destino.mkdir(parents=True, exist_ok=True)
    if shell.usuario_original():
        # Bajo sudo: dotnet publish como el usuario del repo en artifacts/ y copia como root
        for clave in ("backend", "frontend"):
            temporal = publicar(clave, ARTIFACTS / "stage" / clave)
            shutil.copytree(temporal, destino / clave)
        shutil.rmtree(ARTIFACTS / "stage", ignore_errors=True)
    else:
        for clave in ("backend", "frontend"):
            publicar(clave, destino / clave)
    meta = {"id": rid, "fecha": datetime.now().isoformat(timespec="seconds"),
            "commit": _git("rev-parse", "--short", "HEAD"), "rama": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "cambios_sin_commit": bool(_git("status", "--porcelain")), "usuario": getpass.getuser(),
            "entorno": env.get("ARQUIS_ENV")}
    (destino / "release.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    ui.ok(f"Version {rid} creada en {destino}")
    return destino


def activar_ruta(destino: Path) -> None:
    """Apunta 'current' a la version indicada (los servicios deben estar detenidos)."""
    actual = dir_actual()
    if actual.is_symlink() or _es_junction(actual):
        os.rmdir(actual) if shell.ES_WINDOWS else actual.unlink()
    elif actual.exists():
        raise ui.Fallo(f"{actual} existe y no es un enlace; muevalo antes de continuar.")
    if shell.ES_WINDOWS:
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(actual), str(destino)], capture_output=True, text=True)
        if r.returncode != 0:
            raise ui.Fallo(f"No se pudo crear el enlace: {r.stderr or r.stdout}")
    else:
        tmp = actual.with_name("current.tmp")
        tmp.unlink(missing_ok=True)
        tmp.symlink_to(destino, target_is_directory=True)
        tmp.replace(actual)
    ui.ok(f"current → {destino.name}")


def _es_junction(p: Path) -> bool:
    try:
        return bool(os.readlink(p))
    except (OSError, ValueError):
        return False


def registrar(evento: dict) -> None:
    dir_instalacion().mkdir(parents=True, exist_ok=True)
    evento = {"fecha": datetime.now().isoformat(timespec="seconds"), **evento}
    with (dir_instalacion() / "deploys.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")


def listar() -> None:
    """Versiones instaladas."""
    act = activa()
    filas = []
    for rid in listar_ids():
        meta_f = dir_releases() / rid / "release.json"
        meta = json.loads(meta_f.read_text(encoding="utf-8")) if meta_f.exists() else {}
        marca = ui.c("● activa", ui.C.GREEN) if rid == act else ""
        filas.append([rid, meta.get("rama", ""), meta.get("commit", "") + (" *" if meta.get("cambios_sin_commit") else ""),
                      meta.get("usuario", ""), marca])
    ui.tabla(filas, ["Version", "Rama", "Commit", "Usuario", ""])
    ui.dim(f"Carpeta: {dir_releases()}")


def historial() -> None:
    """Historial de despliegues."""
    f = dir_instalacion() / "deploys.jsonl"
    if not f.exists():
        ui.info("Sin despliegues registrados.")
        return
    filas = []
    for linea in f.read_text(encoding="utf-8").splitlines()[-25:]:
        e = json.loads(linea)
        res = e.get("resultado", "")
        color = ui.C.GREEN if res == "ok" else ui.C.RED if res in ("fallo", "rollback") else ui.C.YELLOW
        filas.append([e.get("fecha", ""), e.get("accion", ""), e.get("version", ""), ui.c(res, color), e.get("detalle", "")[:60]])
    ui.tabla(filas, ["Fecha", "Accion", "Version", "Resultado", "Detalle"])


def cambiar_a(rid: str) -> bool:
    """Detiene servicios, cambia 'current' y reinicia comprobando salud."""
    from ..services import control
    control.detener_todo()
    activar_ruta(dir_releases() / rid)
    return control.iniciar_todo()


def rollback() -> None:
    """Vuelve a la version anterior (o a una elegida)."""
    ids = listar_ids()
    act = activa()
    candidatos = [r for r in ids if r != act]
    if not candidatos:
        raise ui.Fallo("No hay otra version a la que volver.")
    i = ui.elegir("Version destino", candidatos, 0)
    if not ui.confirmar(f"¿Activar {candidatos[i]} (actual: {act})?", True):
        return
    bien = cambiar_a(candidatos[i])
    registrar({"accion": "rollback", "version": candidatos[i], "resultado": "ok" if bien else "fallo", "detalle": f"desde {act}"})
    ui.warn("La base de datos NO se revierte. Si hubo migraciones nuevas, use: arquis bd migraciones ir  "
            "o restaure el respaldo previo: arquis bd respaldos restaurar")


def purgar(conservar: int | None = None) -> None:
    """Borra versiones antiguas (conserva DEPLOY_KEEP_RELEASES)."""
    conservar = conservar or int(env.get("DEPLOY_KEEP_RELEASES") or 5)
    act = activa()
    viejas = [r for r in listar_ids()[conservar:] if r != act]
    for rid in viejas:
        shutil.rmtree(dir_releases() / rid, ignore_errors=True)
    ui.ok(f"{len(viejas)} versiones antiguas eliminadas (se conservan {conservar}).")
