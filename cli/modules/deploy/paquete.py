"""Paquete portable para servidores sin SDK ni codigo fuente.

    (equipo de desarrollo)  arquis deploy paquete           → artifacts/arquis-<id>.zip
    (servidor)              descomprimir y ejecutar:
                            arquis.cmd entorno crear
                            arquis.cmd deploy instalar-paquete

El paquete incluye la version publicada, un efbundle (migraciones sin SDK),
la CLI, los scripts SQL y opcionalmente las capas SHP. En el servidor solo se
necesita el runtime ASP.NET Core 10, Python 3 y sqlcmd.
"""
from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from cli.core import env, shell, sql, ui
from cli.core.paths import ARTIFACTS, CLI_DIR, ROOT, SQL_SCRIPTS, rel

from ..bd.capas.capas import carpeta as carpeta_shp
from ..bd.migraciones import ef
from ..services import control
from ..services import definiciones as d
from ..services.gestores import gestor, requerir_admin
from ..services.nginx import nginx
from . import releases


def crear() -> Path:
    """Genera el .zip portable."""
    rid = datetime.now().strftime("%Y%m%d-%H%M%S")
    trabajo = ARTIFACTS / "paquete" / rid
    if trabajo.exists():
        shutil.rmtree(trabajo)
    from ..services.compilacion.compilar import publicar
    for clave in ("backend", "frontend"):
        publicar(clave, trabajo / "release" / clave)
    opciones = ["linux-x64", "linux-arm64", "win-x64"]
    runtime = opciones[ui.elegir("Sistema del servidor destino", opciones, 0)]
    bundle = Path(ef.bundle(runtime))
    shutil.copy2(bundle, trabajo / "release" / ("efbundle.exe" if runtime.startswith("win") else "efbundle"))
    shutil.copytree(CLI_DIR, trabajo / "cli", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(SQL_SCRIPTS, trabajo / "02_BaseDatos")
    for f in ("arquis.cmd", "arquis.sh", ".env.example"):
        if (ROOT / f).exists():
            shutil.copy2(ROOT / f, trabajo / f)
    if carpeta_shp().exists() and ui.confirmar("¿Incluir las capas SHP (datos personales)?", False):
        shutil.copytree(carpeta_shp(), trabajo / "03_DatosPrueba" / "DatosSIG_Reproj")
    meta = {"id": rid, "commit": shell.salida(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT),
            "fecha": datetime.now().isoformat(timespec="seconds")}
    (trabajo / "release" / "release.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    destino = ARTIFACTS / f"arquis-{rid}.zip"
    ejecutables = {"efbundle", "arquis.sh"}
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for p in trabajo.rglob("*"):
            if p.is_file():
                info = zipfile.ZipInfo.from_file(p, p.relative_to(trabajo).as_posix())
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = ((0o755 if p.name in ejecutables else 0o644) | 0o100000) << 16
                z.writestr(info, p.read_bytes())
    shutil.rmtree(trabajo)
    ui.ok(f"Paquete: {rel(destino)} ({destino.stat().st_size / 1_048_576:.1f} MB)")
    return destino


def instalar() -> None:
    """Instala en este servidor la version contenida en el paquete descomprimido."""
    origen = ROOT / "release"
    if not (origen / "release.json").exists():
        raise ui.Fallo("Ejecute este comando desde la carpeta de un paquete descomprimido (falta release/).")
    requerir_admin()
    shell.requerir_escritura(releases.dir_releases())
    meta = json.loads((origen / "release.json").read_text(encoding="utf-8"))
    destino = releases.dir_releases() / meta["id"]
    ui.paso(1, 5, f"Copiar version {meta['id']}")
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(origen, destino)
    ui.paso(2, 5, "Base de datos")
    if sql.existe_base() and env.es_verdad("DEPLOY_BACKUP_DB"):
        from ..bd.respaldos import respaldo
        respaldo.respaldar("pre-deploy")
    from ..bd import admin
    admin.crear()
    bundle = next(destino.glob("efbundle*"))
    if not shell.ES_WINDOWS:
        bundle.chmod(0o755)   # unzip no siempre conserva el bit de ejecucion
    shell.run([str(bundle), "--connection", env.cadena_conexion(admin=True)], silencioso=True)
    ui.ok("Migraciones aplicadas.")
    from ..bd.capas import importar
    if carpeta_shp().exists():
        importar.importar(reemplazar=False)
    ui.paso(3, 5, "nginx")
    if env.es_verdad("NGINX_ENABLED"):
        nginx.instalar_binarios()
        nginx.escribir_config()
    ui.paso(4, 5, "Servicios")
    anterior = releases.activa()
    control.detener_todo() if anterior else None
    releases.activar_ruta(destino)
    for s in d.todos():
        gestor(s).instalar(s, [d.backend().nombre] if s.clave == "frontend" else None)
    ui.paso(5, 5, "Arranque")
    if control.iniciar_todo():
        releases.registrar({"accion": "paquete", "version": meta["id"], "resultado": "ok"})
        ui.ok("Instalacion completada.")
    else:
        releases.registrar({"accion": "paquete", "version": meta["id"], "resultado": "fallo"})
        if anterior:
            ui.warn(f"Volviendo a {anterior}...")
            releases.cambiar_a(anterior)
        raise ui.Fallo("La version no arranco correctamente. Revise: arquis services errores")
