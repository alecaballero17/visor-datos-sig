"""Motor SQL Server: contenedor Docker (Linux/Windows) o servicio mssql-server (Linux)."""
from __future__ import annotations

import secrets
import string
import time

from cli.core import env, shell, sql, ui

CONTENEDOR = "arquis-sql"
IMAGEN = "mcr.microsoft.com/mssql/server:2022-latest"
VOLUMEN = "arquis-sql-data"


def _docker() -> list[str]:
    exe = shell.requerir("docker", ayuda="Instale Docker: arquis deps una → Docker")
    return shell.sudo([exe]) if not shell.ES_WINDOWS and not _docker_sin_sudo(exe) else [exe]


def _docker_sin_sudo(exe: str) -> bool:
    return shell.run([exe, "info"], check=False, capturar=True, silencioso=True).returncode == 0


def _clave_sa() -> str:
    alfabeto = string.ascii_letters + string.digits
    return "Sa9!" + "".join(secrets.choice(alfabeto) for _ in range(20))


def docker_crear() -> None:
    """Crea SQL Server 2022 en Docker con volumen persistente y lo configura en el .env."""
    d = _docker()
    existe = shell.run([*d, "inspect", CONTENEDOR], check=False, capturar=True, silencioso=True).returncode == 0
    if existe:
        ui.info(f"El contenedor {CONTENEDOR} ya existe.")
        docker_iniciar()
        return
    cfg = env.cargar()
    clave = cfg["DB_PASSWORD"] if cfg["DB_USER"] == "sa" and cfg["DB_PASSWORD"] else _clave_sa()
    puerto = ui.preguntar("Puerto en el host", "1433")
    memoria = ui.preguntar("Limite de memoria de SQL Server (MB)", "2048")
    shell.run([*d, "run", "-d", "--name", CONTENEDOR, "--restart", "unless-stopped",
               "-e", "ACCEPT_EULA=Y", "-e", f"MSSQL_SA_PASSWORD={clave}", "-e", "MSSQL_PID=Express",
               "-e", f"MSSQL_MEMORY_LIMIT_MB={memoria}",
               "-p", f"127.0.0.1:{puerto}:1433", "-v", f"{VOLUMEN}:/var/opt/mssql", IMAGEN], silencioso=True)
    ui.info(f"Contenedor {CONTENEDOR} creado (solo escucha en 127.0.0.1:{puerto}).")
    cfg.update(DB_SERVER=f"localhost,{puerto}" if puerto != "1433" else "localhost", DB_AUTH="sql",
               DB_USER="sa", DB_PASSWORD=clave, DB_TRUST_CERT="true")
    env.escribir({k: v for k, v in cfg.items() if k in env.leer() or k.startswith("DB_")})
    ui.ok(".env actualizado con la conexion al contenedor.")
    _esperar()


def _esperar(segundos: int = 90) -> None:
    ui.info("Esperando a que SQL Server acepte conexiones...")
    for _ in range(segundos // 3):
        bien, detalle = sql.probar()
        if bien:
            ui.ok(f"SQL Server listo: {detalle}")
            return
        time.sleep(3)
    ui.warn("SQL Server aun no responde; revise: arquis bd servidor docker-logs")


def docker_iniciar() -> None:
    shell.run([*_docker(), "start", CONTENEDOR])
    _esperar()


def docker_detener() -> None:
    shell.run([*_docker(), "stop", CONTENEDOR], check=False)


def docker_logs() -> None:
    """Logs del contenedor en vivo (Ctrl+C para salir)."""
    try:
        shell.run([*_docker(), "logs", "-f", "--tail", "50", CONTENEDOR], check=False)
    except KeyboardInterrupt:
        pass


def docker_estado() -> None:
    shell.run([*_docker(), "ps", "-a", "--filter", f"name={CONTENEDOR}",
               "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"], check=False)


def docker_eliminar() -> None:
    """Elimina el contenedor (el volumen con los datos se conserva salvo que se pida)."""
    if not ui.confirmar_peligro(f"Se eliminara el contenedor {CONTENEDOR}.", CONTENEDOR):
        return
    d = _docker()
    shell.run([*d, "rm", "-f", CONTENEDOR], check=False)
    if ui.confirmar(f"¿Eliminar TAMBIEN el volumen {VOLUMEN} con todas las bases?", False):
        shell.run([*d, "volume", "rm", VOLUMEN], check=False)


# ── SQL Server instalado como servicio en Linux ───────────────────────────────────
def servicio_estado() -> None:
    """systemctl status mssql-server."""
    shell.run(["systemctl", "status", "mssql-server", "--no-pager", "-l"], check=False)


def servicio_reiniciar() -> None:
    shell.run(shell.sudo(["systemctl", "restart", "mssql-server"]))
    _esperar()


def servicio_logs() -> None:
    """Log de SQL Server en vivo (journalctl)."""
    try:
        shell.run(shell.sudo(["journalctl", "-u", "mssql-server", "-f", "-n", "50"]), check=False)
    except KeyboardInterrupt:
        pass


# ── Instalacion de SQL Server ─────────────────────────────────────────────────────
def _memoria_mb() -> int:
    try:
        for linea in open("/proc/meminfo", encoding="utf-8"):
            if linea.startswith("MemTotal:"):
                return int(linea.split()[1]) // 1024
    except OSError:
        pass
    return 0


def _url_existe(url: str) -> bool:
    return shell.run(["curl", "-fsIL", "-o", "/dev/null", url], check=False, capturar=True, silencioso=True).returncode == 0


def nativo_instalar() -> None:
    """Instala SQL Server (mssql-server) como servicio de Linux y guarda la conexion en el .env."""
    if shell.ES_WINDOWS:
        raise ui.Fallo("En Windows use LocalDB o el instalador de SQL Server Express.")
    if shell.which("systemctl") and shell.salida(["systemctl", "is-active", "mssql-server"]) == "active":
        ui.info("mssql-server ya esta instalado y activo.")
        return
    mem = _memoria_mb()
    if mem and mem < 2000:
        ui.warn(f"El servidor tiene {mem} MB de RAM; SQL Server necesita al menos 2 GB. Considere un SQL remoto.")
        if not ui.confirmar("¿Continuar igualmente?", False):
            return
    os_r = shell.os_release()
    distro, version = os_r.get("ID", ""), os_r.get("VERSION_ID", "")
    gestor = shell.gestor_paquetes()
    if not shell.which("curl"):
        shell.run(shell.sudo([gestor or "apt-get", "install", "-y", "curl"]))
    if gestor == "apt-get":
        if distro != "ubuntu":
            raise ui.Fallo(f"Microsoft no publica mssql-server para {distro or 'esta distro'}: use Docker (bd servidor docker-crear).")
        lista = next((u for u in (f"https://packages.microsoft.com/config/ubuntu/{version}/mssql-server-{v}.list"
                                  for v in ("2025", "2022")) if _url_existe(u)), None)
        if not lista:
            raise ui.Fallo(f"No hay paquete mssql-server para Ubuntu {version}: use Docker (bd servidor docker-crear).")
        shell.run(shell.sudo(["sh", "-c",
                              "test -f /usr/share/keyrings/microsoft-prod.gpg || curl -fsSL "
                              "https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg"]))
        shell.run(shell.sudo(["curl", "-fsSL", "-o", "/etc/apt/sources.list.d/mssql-server.list", lista]))
        shell.run(shell.sudo(["apt-get", "update"]))
        shell.run(shell.sudo(["env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y", "mssql-server"]))
    elif gestor in ("dnf", "yum"):
        mayor = version.split(".")[0]
        repo = next((u for u in (f"https://packages.microsoft.com/config/rhel/{mayor}/mssql-server-{v}.repo"
                                 for v in ("2025", "2022")) if _url_existe(u)), None)
        if not repo:
            raise ui.Fallo(f"No hay paquete mssql-server para RHEL {mayor}: use Docker (bd servidor docker-crear).")
        shell.run(shell.sudo(["curl", "-fsSL", "-o", "/etc/yum.repos.d/mssql-server.repo", repo]))
        shell.run(shell.sudo([gestor, "install", "-y", "mssql-server"]))
    else:
        raise ui.Fallo("Gestor de paquetes no soportado: use Docker (bd servidor docker-crear).")

    cfg = env.cargar()
    clave = cfg["DB_PASSWORD"] if cfg["DB_USER"] == "sa" and cfg["DB_PASSWORD"] else _clave_sa()
    edicion = ui.elegir("Edicion", ["Express (gratis, hasta 10 GB por base)", "Developer (gratis, no produccion)"], 0)
    shell.run(shell.sudo(["env", f"MSSQL_SA_PASSWORD={clave}", f"MSSQL_PID={'Express' if edicion == 0 else 'Developer'}",
                          "ACCEPT_EULA=Y", "/opt/mssql/bin/mssql-conf", "-n", "setup"]), silencioso=True)
    # Solo escuchar en la maquina (la app esta en el mismo servidor)
    shell.run(shell.sudo(["/opt/mssql/bin/mssql-conf", "set", "network.ipaddress", "127.0.0.1"]), check=False, capturar=True)
    shell.run(shell.sudo(["systemctl", "enable", "--now", "mssql-server"]), check=False)
    shell.run(shell.sudo(["systemctl", "restart", "mssql-server"]), check=False)
    cfg.update(DB_SERVER="localhost", DB_AUTH="sql", DB_USER="sa", DB_PASSWORD=clave, DB_TRUST_CERT="true")
    env.escribir(cfg)
    ui.ok("SQL Server instalado (solo escucha en 127.0.0.1). Conexion guardada en el .env.")
    _esperar()


def instalar() -> None:
    """Elige como obtener SQL Server: Docker, servicio nativo o un servidor existente."""
    opciones = ["Docker (recomendado: cualquier distro, aislado, facil de actualizar)",
                "Servicio nativo mssql-server (Ubuntu / RHEL)",
                "Ya tengo un SQL Server (local o remoto): configurar la conexion"]
    if shell.ES_WINDOWS:
        opciones = [opciones[0], opciones[2]]
    i = ui.elegir("SQL Server", opciones, 0)
    eleccion = opciones[i]
    if eleccion.startswith("Docker"):
        if not shell.which("docker"):
            from cli.modules.dependencias import instalar as inst, requisitos
            inst._instalar([h for h in requisitos.HERRAMIENTAS if h.clave == "docker"])
        docker_crear()
    elif eleccion.startswith("Servicio"):
        nativo_instalar()
    else:
        from . import conexion
        conexion.elegir_instancia()
