"""Migraciones de Entity Framework Core (src/Arquis.Backend/Migrations)."""
from __future__ import annotations

import json
import re
from datetime import datetime

from cli.core import env, shell, ui
from cli.core.paths import ARTIFACTS, BACKEND, asegurar, rel

PROYECTO = ["--project", str(BACKEND), "--startup-project", str(BACKEND), "--context", "ArquisDbContext"]
_COMPILADO = False


def _env() -> dict[str, str]:
    return env.entorno_backend()


def _desactualizado() -> bool:
    """¿Hay codigo del backend mas nuevo que el ultimo build? (evita 'dotnet build' innecesarios)."""
    dll = BACKEND / "bin" / "Debug" / "net10.0" / "Arquis.Backend.dll"
    if not dll.exists():
        return True
    limite = dll.stat().st_mtime
    for patron in ("*.cs", "*.csproj", "*.json"):
        for f in BACKEND.rglob(patron):
            if "bin" in f.parts or "obj" in f.parts:
                continue
            if f.stat().st_mtime > limite:
                return True
    return False


def _compilar() -> None:
    global _COMPILADO
    if not _COMPILADO:
        from ...dependencias.restaurar import ef_disponible, herramientas_dotnet
        if not ef_disponible():
            herramientas_dotnet()
        if _desactualizado():
            ui.info("Compilando el backend (hubo cambios en el codigo)...")
            shell.run([shell.dotnet(), "build", BACKEND, "--nologo", "-v", "q"], env=_env(), como_usuario=True)
        _COMPILADO = True


def _ef(*args: str, capturar: bool = False, conexion: bool = False, check: bool = True):
    _compilar()
    cmd = [shell.dotnet(), "ef", *args, *PROYECTO, "--no-build"]
    if conexion:
        cmd += ["--connection", env.cadena_conexion(admin=True)]
    return shell.run(cmd, env=_env(), capturar=capturar, check=check, como_usuario=True,
                     silencioso=conexion)  # no mostrar la cadena de conexion


def lista() -> list[dict]:
    p = _ef("migrations", "list", "--json", "--prefix-output", capturar=True, conexion=True, check=False)
    texto = p.stdout or ""
    datos = "\n".join(l[6:] if l.startswith("data:") else "" for l in texto.splitlines()).strip()
    if p.returncode != 0 or not datos:
        # Sin conexion: lista sin estado
        p2 = _ef("migrations", "list", "--json", "--prefix-output", capturar=True, check=False)
        datos = "\n".join(l[6:] for l in (p2.stdout or "").splitlines() if l.startswith("data:")).strip()
        if not datos:
            raise ui.Fallo("No se pudieron listar las migraciones:\n" + ((p.stderr or "") + texto)[-1500:])
        ui.warn("Sin conexion a la base: no se muestra el estado aplicado.")
    return json.loads(datos)


def lista_rapida() -> list[dict]:
    """Migraciones del codigo vs __EFMigrationsHistory, sin ejecutar dotnet (instantaneo)."""
    from cli.core import sql
    archivos = sorted(f.stem for f in (BACKEND / "Migrations").glob("*.cs")
                      if not f.name.endswith(".Designer.cs") and f.stem[:14].isdigit())
    filas = sql.filas("IF OBJECT_ID('dbo.__EFMigrationsHistory') IS NOT NULL "
                      "SELECT MigrationId FROM dbo.__EFMigrationsHistory")
    aplicadas = {f[0] for f in filas}
    ids = sorted(set(archivos) | aplicadas)
    return [{"id": i, "name": i[15:], "applied": i in aplicadas, "huerfana": i not in archivos} for i in ids]


def estado() -> list[dict]:
    """Migraciones aplicadas y pendientes."""
    migs = lista_rapida()
    for m in migs:
        if m["huerfana"]:
            ui.warn(f"{m['id']} esta aplicada en la base pero no existe en el codigo.")
    filas = []
    for m in migs:
        aplicada = m.get("applied")
        marca = ui.c("aplicada", ui.C.GREEN) if aplicada else (ui.c("pendiente", ui.C.YELLOW) if aplicada is False else "?")
        filas.append([m["id"][:14], m["name"], marca])
    ui.tabla(filas, ["Fecha", "Migracion", "Estado"])
    pend = [m for m in migs if m.get("applied") is False]
    ui.info(f"{len(migs)} migraciones, {len(pend)} pendientes.")
    return migs


def actualizar() -> None:
    """Aplica todas las migraciones pendientes."""
    _ef("database", "update", conexion=True)
    ui.ok("Base de datos actualizada a la ultima migracion.")


def ir_a() -> None:
    """Migra (adelante o atras/rollback) hasta una migracion concreta."""
    migs = lista()
    opciones = ["0 (revertir TODO)"] + [m["id"] for m in migs]
    i = ui.elegir("Migracion destino", opciones, defecto=len(opciones) - 1)
    destino = "0" if i == 0 else migs[i - 1]["id"]
    ultima_aplicada = max((k for k, m in enumerate(migs) if m.get("applied")), default=-1)
    hacia_atras = (i - 1) < ultima_aplicada   # i-1 = indice del destino (-1 para "0")
    if hacia_atras:
        if not ui.confirmar_peligro("Esto revierte migraciones y puede borrar datos.", "REVERTIR"):
            return
    _ef("database", "update", destino, conexion=True)
    ui.ok(f"Base en la migracion {destino}.")


def revertir_ultima() -> None:
    """Revierte solo la ultima migracion aplicada."""
    aplicadas = [m for m in lista() if m.get("applied")]
    if not aplicadas:
        ui.warn("No hay migraciones aplicadas.")
        return
    destino = aplicadas[-2]["id"] if len(aplicadas) > 1 else "0"
    if not ui.confirmar_peligro(f"Se revertira {aplicadas[-1]['name']}.", "REVERTIR"):
        return
    _ef("database", "update", destino, conexion=True)
    ui.ok(f"Revertida. Migracion actual: {destino}")


def agregar() -> None:
    """Crea una migracion nueva a partir de los cambios del modelo."""
    nombre = ui.preguntar("Nombre (PascalCase, ej. AgregarCampoX)")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", nombre or ""):
        raise ui.Fallo("Nombre invalido.")
    global _COMPILADO
    _COMPILADO = False
    _ef("migrations", "add", nombre, "--output-dir", "Migrations")
    ui.ok(f"Migracion {nombre} creada en {rel(BACKEND / 'Migrations')}. Revisela antes de aplicarla.")


def quitar_ultima() -> None:
    """Elimina el archivo de la ultima migracion (si no esta aplicada)."""
    if not ui.confirmar("¿Eliminar la ultima migracion del codigo?"):
        return
    _ef("migrations", "remove", conexion=True)
    ui.ok("Migracion eliminada.")


def cambios_pendientes() -> None:
    """Indica si el modelo tiene cambios sin migracion."""
    p = _ef("migrations", "has-pending-model-changes", capturar=True, check=False)
    texto = ((p.stdout or "") + (p.stderr or "")).strip()
    if p.returncode == 0:
        ui.ok("El modelo coincide con la ultima migracion.")
    else:
        ui.warn("Hay cambios en el modelo sin migracion (arquis bd migraciones nueva).")
        ui.dim(texto[-500:])


def script() -> None:
    """Genera un script SQL idempotente (para aplicar a mano en un servidor)."""
    asegurar(ARTIFACTS / "sql")
    destino = ARTIFACTS / "sql" / f"migraciones-{datetime.now():%Y%m%d-%H%M%S}.sql"
    _ef("migrations", "script", "--idempotent", "--output", str(destino))
    ui.ok(f"Script generado: {rel(destino)}")


def bundle(runtime: str | None = None) -> str:
    """Genera un ejecutable que aplica las migraciones sin SDK (efbundle)."""
    if runtime is None:
        opciones = ["linux-x64", "linux-arm64", "win-x64"]
        runtime = opciones[ui.elegir("Sistema del servidor destino", opciones, 0)]
    asegurar(ARTIFACTS / "efbundle")
    destino = ARTIFACTS / "efbundle" / (f"efbundle-{runtime}" + (".exe" if runtime.startswith("win") else ""))
    _ef("migrations", "bundle", "--self-contained", "--target-runtime", runtime, "--force", "--output", str(destino))
    ui.ok(f"Bundle: {rel(destino)}")
    ui.dim(f'Uso: ./{destino.name} --connection "<cadena>"')
    return str(destino)


def informacion_contexto() -> None:
    """dotnet ef dbcontext info."""
    _ef("dbcontext", "info", conexion=True)
