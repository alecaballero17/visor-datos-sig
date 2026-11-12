"""Motor SQL Server: contenedor Docker (Linux/Windows) o servicio mssql-server (Linux)."""
from __future__ import annotations

import re
import secrets
import string
import subprocess
import time
from pathlib import Path

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
    clave = _clave_admin(cfg)
    puerto = ui.preguntar("Puerto en el host", "1433")
    memoria = ui.preguntar("Limite de memoria de SQL Server (MB)", "2048")
    shell.run([*d, "run", "-d", "--name", CONTENEDOR, "--restart", "unless-stopped",
               "-e", "ACCEPT_EULA=Y", "-e", f"MSSQL_SA_PASSWORD={clave}", "-e", "MSSQL_PID=Express",
               "-e", f"MSSQL_MEMORY_LIMIT_MB={memoria}",
               "-p", f"127.0.0.1:{puerto}:1433", "-v", f"{VOLUMEN}:/var/opt/mssql", IMAGEN], silencioso=True)
    ui.info(f"Contenedor {CONTENEDOR} creado (solo escucha en 127.0.0.1:{puerto}).")
    cfg["DB_SERVER"] = f"127.0.0.1,{puerto}" if puerto != "1433" else "127.0.0.1"
    _guardar_admin(cfg, clave)
    _esperar()
    _login_app()


def _clave_admin(cfg: dict[str, str]) -> str:
    """Reutiliza la contrasena de 'sa' si ya esta en el .env; si no, genera una."""
    if cfg.get("DB_ADMIN_USER") == "sa" and cfg.get("DB_ADMIN_PASSWORD"):
        return cfg["DB_ADMIN_PASSWORD"]
    if cfg.get("DB_USER") == "sa" and cfg.get("DB_PASSWORD"):
        return cfg["DB_PASSWORD"]
    return _clave_sa()


def _guardar_admin(cfg: dict[str, str], clave: str) -> None:
    """'sa' queda como cuenta administradora de la CLI; la app conserva su propio usuario."""
    cfg.update(DB_AUTH="sql", DB_TRUST_CERT="true", DB_ADMIN_USER="sa", DB_ADMIN_PASSWORD=clave)
    if not cfg.get("DB_USER") or cfg["DB_USER"] == "sa":
        cfg.update(DB_USER="sa", DB_PASSWORD=clave)
    elif not cfg.get("DB_PASSWORD"):
        from cli.modules.entorno.env_file import _generar_clave
        cfg["DB_PASSWORD"] = _generar_clave()
    env.escribir(cfg)
    ui.ok("Conexion guardada en el .env (administradora: sa" +
          (f"; la app usara '{cfg['DB_USER']}')." if cfg["DB_USER"] != "sa" else ")."))


def _login_app() -> None:
    """Crea la base y el login de la app si la app no usa 'sa'."""
    from . import conexion
    try:
        conexion.asegurar_login_app()
    except ui.Fallo as e:
        ui.warn(f"No se pudo crear el login de la app todavia: {e}")


def _esperar(segundos: int = 120) -> bool:
    """Espera a que SQL Server conteste a una consulta real, mostrando el avance."""
    import sys
    sql.olvidar_alcance()
    inicio = time.monotonic()
    ultimo = ""
    while (t := int(time.monotonic() - inicio)) < segundos:
        if sql.alcanzable(usar_cache=False)[0]:
            bien, detalle = sql.probar()
            if bien:
                if sys.stdout.isatty():
                    print()
                ui.ok(f"SQL Server listo ({t} s): {detalle}")
                return True
            ultimo = " ".join(detalle.split())
            if "contrasena incorrect" in ultimo.lower():
                break                       # no es cuestion de esperar
            estado = "puerto abierto, aun no contesta"
        else:
            estado = "puerto cerrado"
        _linea_temporal(f"· Esperando a SQL Server... {t:>3} s  ({estado})")
        time.sleep(2)
    if sys.stdout.isatty():
        print()
    ui.warn(f"SQL Server no contesto en {segundos} s. {ultimo[:200]}")
    ui.dim("    Diagnostico: arquis bd servidor diagnostico")
    return False


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
    """systemctl status mssql-server + ultimas lineas legibles del log."""
    shell.run(["systemctl", "status", "mssql-server", "--no-pager", "-l", "-n", "0"], check=False)
    if _estado_servicio() in ("deactivating", "activating"):
        ui.warn(f"mssql-server esta '{_estado_servicio()}' (atascado si dura mas de 1-2 minutos): "
                "arquis bd servidor mssql-reiniciar lo fuerza.")
    log = _leer_errorlog(15)
    if log:
        ui.seccion("Ultimas lineas del errorlog")
        for l in log:
            print("  " + l[:160])


def _estado_servicio() -> str:
    return shell.salida(["systemctl", "show", "-p", "ActiveState", "--value", "mssql-server"])


def _detener_servicio() -> None:
    """Detiene mssql-server; si se queda atascado ('deactivating') lo mata."""
    if _estado_servicio() in ("inactive", "failed", ""):
        return
    try:
        ui.info("Deteniendo mssql-server (si tarda mas de 30 s se fuerza)...")
        shell.run(shell.sudo(["systemctl", "stop", "mssql-server"]), check=False, capturar=True,
                  silencioso=True, timeout=30)
    except ui.Fallo:
        pass
    if _estado_servicio() not in ("inactive", "failed", ""):
        ui.warn("mssql-server no se detuvo a tiempo; se fuerza (SIGKILL).")
        shell.run(shell.sudo(["systemctl", "kill", "-s", "SIGKILL", "mssql-server"]), check=False, capturar=True)
        for _ in range(10):
            if _estado_servicio() in ("inactive", "failed", ""):
                break
            time.sleep(1)
    shell.run(shell.sudo(["systemctl", "reset-failed", "mssql-server"]), check=False, capturar=True, silencioso=True)


def servicio_reiniciar() -> None:
    _detener_servicio()
    if _arrancar():
        _esperar()


def servicio_logs() -> None:
    """Log de SQL Server en vivo (journalctl)."""
    try:
        shell.run(shell.sudo(["journalctl", "-a", "-u", "mssql-server", "-f", "-n", "50"]), check=False)
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


ERRORLOG = Path("/var/opt/mssql/log/errorlog")


def _ocupante_puerto(puerto: int = 1433) -> str:
    """Proceso que escucha en el puerto ('' si esta libre)."""
    if not shell.which("ss"):
        return ""
    linea = shell.salida(shell.sudo(["ss", "-ltnpH", f"sport = :{puerto}"]))
    if not linea.strip():
        return ""
    m = re.search(r'users:\(\("([^"]+)"', linea)
    return m.group(1) if m else "desconocido"


def _leer_errorlog(lineas: int = 25) -> list[str]:
    """Ultimas lineas del errorlog de SQL Server (esta en UTF-16)."""
    try:
        datos = ERRORLOG.read_bytes()
    except PermissionError:
        p = subprocess.run(shell.sudo(["cat", str(ERRORLOG)]), capture_output=True)
        datos = p.stdout
    except OSError:
        return []
    texto = datos.decode("utf-16", errors="replace") if datos[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00" in datos[:200] \
        else datos.decode("utf-8", errors="replace")
    return [l for l in texto.splitlines() if l.strip()][-lineas:]


def diagnostico() -> None:
    """Por que SQL Server no arranca o no contesta: RAM, puerto, servicio, contenedor y errorlog."""
    if shell.ES_WINDOWS:
        raise ui.Fallo("Diagnostico disponible en Linux; en Windows revise el servicio en services.msc.")
    mem = _memoria_mb()
    filas = [["RAM total", f"{mem} MB" + ("  ✖ SQL Server necesita 2 GB" if mem and mem < 2000 else "")]]
    ocupante = _ocupante_puerto()
    filas.append(["Puerto 1433", f"en uso por: {ocupante}" if ocupante else "libre"])
    if shell.which("systemctl"):
        estado = _estado_servicio() or "no instalado"
        filas.append(["mssql-server", estado + ("  ✖ atascado: arquis bd servidor mssql-reiniciar"
                                                 if estado in ("deactivating", "activating") else "")])
        filas.append(["Reinicios", shell.salida(["systemctl", "show", "-p", "NRestarts", "--value", "mssql-server"]) or "-"])
    if shell.which("docker"):
        cont = shell.salida([*_docker(), "ps", "-a", "--filter", "publish=1433", "--format", "{{.Names}} ({{.Status}})"])
        filas.append(["Docker en 1433", cont.replace("\n", ", ") or "ninguno"])
    filas.append(["Configurado", "si" if Path("/var/opt/mssql/mssql.conf").exists() or Path("/var/opt/mssql/data/master.mdf").exists()
                  else "no (falta mssql-conf setup)"])
    ui.tabla(filas, ["Comprobacion", "Resultado"])
    log = _leer_errorlog()
    if log:
        ui.seccion(f"Ultimas lineas de {ERRORLOG}")
        for l in log:
            print("  " + l[:160])
    elif shell.which("journalctl"):
        ui.seccion("journalctl -u mssql-server")
        print(shell.salida(shell.sudo(["journalctl", "-a", "-u", "mssql-server", "-n", "25", "--no-pager"])))
    if ocupante and ocupante not in ("sqlservr",):
        ui.warn(f"El puerto 1433 lo ocupa '{ocupante}', no mssql-server. "
                + ("Es el contenedor Docker: use docker-iniciar/docker-estado, o eliminelo si va a usar el nativo."
                   if "docker" in ocupante else "Detenga ese programa o use otro puerto."))
    if mem and mem < 2000:
        ui.warn("Con menos de 2 GB de RAM SQL Server no arranca: amplie la RAM o use un SQL Server remoto.")


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

    _configurar_nativo()


def _configurado() -> bool:
    """¿mssql-conf setup ya se ejecuto alguna vez? (existe la base master)."""
    return shell.run(shell.sudo(["test", "-f", "/var/opt/mssql/data/master.mdf"]), check=False,
                     capturar=True, silencioso=True).returncode == 0


def _esperar_puerto_libre(segundos: int = 20) -> str:
    """Tras detener el servicio el puerto tarda unos segundos en liberarse."""
    ocupante = ""
    for _ in range(segundos):
        ocupante = _ocupante_puerto()
        if not ocupante:
            return ""
        time.sleep(1)
    return ocupante


def _linea_temporal(texto: str) -> None:
    import sys
    if sys.stdout.isatty():
        sys.stdout.write(chr(13) + "  " + texto[:110].ljust(110))
        sys.stdout.flush()


def _arrancar(limite: int = 180) -> bool:
    """Arranca mssql-server SIN esperar a systemd (SQL Server 2025 puede no avisarle nunca que esta listo)
    y comprueba el mismo si ya acepta conexiones, mostrando el avance."""
    import sys
    shell.run(shell.sudo(["systemctl", "enable", "mssql-server"]), check=False, capturar=True, silencioso=True)
    shell.run(shell.sudo(["systemctl", "start", "--no-block", "mssql-server"]), check=False)
    sql.olvidar_alcance()
    inicio = time.monotonic()
    while (transcurrido := int(time.monotonic() - inicio)) < limite:
        if sql.alcanzable(usar_cache=False)[0]:
            if sys.stdout.isatty():
                print()
            ui.ok(f"SQL Server acepta conexiones ({transcurrido} s).")
            return True
        estado = _estado_servicio()
        if estado == "failed":
            break
        ultima = (_leer_errorlog(1) or [""])[-1]
        _linea_temporal(f"· Arrancando SQL Server... {transcurrido:>3} s  [{estado}]  {ultima[23:]}")
        time.sleep(1)
    if sys.stdout.isatty():
        print()
    ui.error(f"SQL Server no acepto conexiones en {limite} s (estado: {_estado_servicio()}).")
    diagnostico()
    return False


def _conecta_con(cfg: dict[str, str], usuario: str, clave: str) -> bool:
    prueba = dict(cfg, DB_SERVER="127.0.0.1", DB_AUTH="sql", DB_ADMIN_USER=usuario, DB_ADMIN_PASSWORD=clave)
    sql.olvidar_alcance()
    try:
        r = shell.run(sql._args("master", prueba) + ["-Q", "SET NOCOUNT ON; SELECT 1"],
                      check=False, capturar=True, silencioso=True, timeout=20)
        return r.returncode == 0
    except ui.Fallo:
        return False


def _configurar_nativo() -> None:
    """Deja mssql-server configurado, escuchando en 127.0.0.1 y con la clave de 'sa' conocida por la CLI."""
    cfg = env.cargar()
    # mssql-conf arranca SQL Server y espera a que conteste: si el puerto esta ocupado se queda colgado
    _detener_servicio()
    ocupante = _esperar_puerto_libre()
    if ocupante:
        diagnostico()
        raise ui.Fallo(f"El puerto 1433 sigue en uso por '{ocupante}'; mssql-server no podria arrancar. "
                       "Libere el puerto (p. ej. arquis bd servidor docker-eliminar) y reintente.")
    # Solo escuchar en la maquina (la app esta en el mismo servidor)
    shell.run(shell.sudo(["/opt/mssql/bin/mssql-conf", "set", "network.ipaddress", "127.0.0.1"]),
              check=False, capturar=True, silencioso=True)
    if _configurado():
        ui.info("SQL Server ya estaba configurado: se arranca y se comprueba la cuenta 'sa'.")
        if not _arrancar():
            raise ui.Fallo("SQL Server no arranco: revise el diagnostico de arriba.")
        clave_actual = cfg.get("DB_ADMIN_PASSWORD") if cfg.get("DB_ADMIN_USER", "sa") in ("", "sa") else ""
        if clave_actual and _conecta_con(cfg, "sa", clave_actual):
            clave = clave_actual
        else:
            ui.info("La clave de 'sa' no esta en el .env (o no coincide): se restablece.")
            clave = _clave_admin(dict(cfg, DB_ADMIN_PASSWORD=""))
            _detener_servicio()
            _esperar_puerto_libre()
            _mssql_conf(["set-sa-password"], clave, "Restableciendo la clave de 'sa' (1-2 minutos; limite 5)...")
            _arrancar()
    else:
        clave = _clave_admin(cfg)
        edicion = ui.elegir("Edicion", ["Express (gratis, hasta 10 GB por base)", "Developer (gratis, no produccion)"], 0)
        _mssql_conf(["setup"], clave, "Configurando SQL Server (1-3 minutos; limite 6)...",
                    {"MSSQL_PID": "Express" if edicion == 0 else "Developer"}, 360)
        _detener_servicio()   # aplicar network.ipaddress
        _arrancar()
    cfg["DB_SERVER"] = "127.0.0.1"
    _guardar_admin(cfg, clave)
    sql.olvidar_alcance()
    _esperar()
    if not sql.probar()[0]:
        diagnostico()
        raise ui.Fallo("SQL Server no contesta con la cuenta 'sa' configurada. Revise el diagnostico.")
    ui.ok("SQL Server listo (solo escucha en 127.0.0.1).")
    _login_app()


def _mssql_conf(accion: list[str], clave: str, mensaje: str, extra: dict[str, str] | None = None,
                limite: int = 300) -> None:
    ui.info(mensaje)
    variables = [f"{k}={v}" for k, v in {"MSSQL_SA_PASSWORD": clave, "ACCEPT_EULA": "Y", **(extra or {})}.items()]
    try:
        shell.run(shell.sudo(["env", *variables, "/opt/mssql/bin/mssql-conf", "-n", *accion]),
                  silencioso=True, timeout=limite)
    except ui.Fallo as e:
        ui.error(f"mssql-conf {accion[0]} no termino: {str(e).splitlines()[0]}")
        _detener_servicio()
        diagnostico()
        raise ui.Fallo("SQL Server no quedo configurado. Revise el diagnostico de arriba; alternativa: "
                       "arquis bd servidor instalar → Docker.")


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
