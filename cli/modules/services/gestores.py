"""Gestores de servicios del sistema: systemd (Linux) y NSSM (Windows).

NSSM convierte cualquier ejecutable en un servicio de Windows real (arranque
automatico, reinicio ante fallos, rotacion de logs) sin modificar el codigo
de la aplicacion. nssm.exe se copia a <DEPLOY_DIR>/tools porque el servicio
lo usa como binario.
"""
from __future__ import annotations

import io
import os
import re
import shutil
import time
import urllib.request
import zipfile
from pathlib import Path

from cli.core import env, shell, ui

from .definiciones import Servicio, dir_instalacion, dir_logs

NSSM_URL = "https://nssm.cc/release/nssm-2.24.zip"


def es_admin() -> bool:
    return shell.es_root()


def requerir_admin() -> None:
    """Windows: terminal de Administrador. Linux: root o sudo disponible."""
    if shell.ES_WINDOWS and not es_admin():
        raise ui.Fallo("Se requieren permisos de administrador: abra la terminal como Administrador.")
    if not shell.ES_WINDOWS and not es_admin() and not shell.which("sudo"):
        raise ui.Fallo("Se requieren privilegios de root: ejecute con sudo.")


class Gestor:
    nombre = "?"

    def existe(self, s: Servicio) -> bool: ...
    def instalar(self, s: Servicio, dependencias: list[str] | None = None) -> None: ...
    def desinstalar(self, s: Servicio) -> None: ...
    def iniciar(self, s: Servicio) -> None: ...
    def detener(self, s: Servicio) -> None: ...
    def estado(self, s: Servicio) -> dict: ...

    def reiniciar(self, s: Servicio) -> None:
        self.detener(s)
        time.sleep(1)
        self.iniciar(s)

    def actualizar_entorno(self, s: Servicio) -> None:
        """Vuelve a escribir las variables del .env en el servicio."""
        self.instalar(s)


# ── NSSM ─────────────────────────────────────────────────────────────────────
class Nssm(Gestor):
    nombre = "nssm"

    def exe(self) -> str:
        destino = dir_instalacion() / "tools" / "nssm.exe"
        if destino.exists():
            return str(destino)
        origen = shell.which("nssm")
        destino.parent.mkdir(parents=True, exist_ok=True)
        if origen:
            shutil.copy2(origen, destino)
            return str(destino)
        ui.info(f"Descargando NSSM desde {NSSM_URL} ...")
        try:
            with urllib.request.urlopen(NSSM_URL, timeout=60) as r:
                datos = r.read()
            with zipfile.ZipFile(io.BytesIO(datos)) as z:
                miembro = next(n for n in z.namelist() if n.endswith("win64/nssm.exe"))
                destino.write_bytes(z.read(miembro))
            return str(destino)
        except Exception as e:  # noqa: BLE001
            raise ui.Fallo(f"No se pudo obtener NSSM ({e}). Instale con: winget install NSSM.NSSM")

    def _run(self, *args, check=True, capturar=True):
        return shell.run([self.exe(), *args], check=check, capturar=capturar, silencioso=True)

    def existe(self, s: Servicio) -> bool:
        return shell.run(["sc.exe", "query", s.nombre], check=False, capturar=True, silencioso=True).returncode == 0

    def instalar(self, s: Servicio, dependencias: list[str] | None = None) -> None:
        requerir_admin()
        dir_logs().mkdir(parents=True, exist_ok=True)
        if not self.existe(s):
            self._run("install", s.nombre, s.ejecutable, *s.argumentos)
        else:
            self._run("set", s.nombre, "Application", s.ejecutable)
            self._run("set", s.nombre, "AppParameters", " ".join(f'"{a}"' if " " in a else a for a in s.argumentos))
        cfg = env.cargar()
        ajustes = {
            "AppDirectory": str(s.carpeta),
            "DisplayName": f"Arquis · {s.titulo}",
            "Description": f"Arquis SIG - {s.titulo}. Gestionado por la CLI de Arquis.",
            "Start": "SERVICE_AUTO_START" if env.es_verdad("DEPLOY_AUTOSTART", cfg) else "SERVICE_DEMAND_START",
            "AppStdout": str(s.log_out),
            "AppStderr": str(s.log_err),
            "AppRotateFiles": "1",
            "AppRotateOnline": "1",
            "AppRotateBytes": str(10 * 1024 * 1024),
            "AppExit": "Default Restart",
            "AppRestartDelay": "5000",
            "AppStopMethodConsole": "15000",
        }
        for k, v in ajustes.items():
            self._run("set", s.nombre, k, v)
        if s.entorno:
            self._run("set", s.nombre, "AppEnvironmentExtra", *[f"{k}={v}" for k, v in s.entorno.items()])
        else:
            self._run("reset", s.nombre, "AppEnvironmentExtra", check=False)
        if dependencias:
            self._run("set", s.nombre, "DependOnService", *dependencias)
        if cfg.get("SERVICE_USER"):
            clave = ui.preguntar(f"Contrasena de {cfg['SERVICE_USER']}", secreto=True)
            self._run("set", s.nombre, "ObjectName", cfg["SERVICE_USER"], clave)
        ui.ok(f"Servicio {s.nombre} registrado (NSSM).")

    def desinstalar(self, s: Servicio) -> None:
        requerir_admin()
        if self.existe(s):
            self._run("stop", s.nombre, check=False)
            self._run("remove", s.nombre, "confirm")
            ui.ok(f"Servicio {s.nombre} eliminado.")
        else:
            ui.info(f"{s.nombre} no estaba registrado.")

    def iniciar(self, s: Servicio) -> None:
        r = self._run("start", s.nombre, check=False)
        texto = ((r.stdout or "") + (r.stderr or "")).replace("\x00", "").strip()
        if r.returncode != 0 and "already running" not in texto.lower():
            raise ui.Fallo(f"No se pudo iniciar {s.nombre}: {texto}")
        ui.ok(f"{s.nombre} iniciado.")

    def detener(self, s: Servicio) -> None:
        if s.clave == "nginx" and Path(s.ejecutable).exists():
            shell.run([s.ejecutable, *s.argumentos, "-s", "quit"], cwd=s.carpeta, check=False, capturar=True, silencioso=True)
        self._run("stop", s.nombre, check=False)
        ui.ok(f"{s.nombre} detenido.")

    def estado(self, s: Servicio) -> dict:
        if not self.existe(s):
            return {"estado": "no instalado"}
        q = shell.salida(["sc.exe", "queryex", s.nombre])
        conf = shell.salida(["sc.exe", "qc", s.nombre])
        estado = re.search(r"STATE\s*:\s*\d+\s+(\w+)", q)
        pid = re.search(r"PID\s*:\s*(\d+)", q)
        inicio = re.search(r"START_TYPE\s*:\s*\d+\s+(\w+)", conf)
        datos = {"estado": (estado.group(1).lower() if estado else "?"),
                 "pid": pid.group(1) if pid and pid.group(1) != "0" else "",
                 "inicio": inicio.group(1).lower() if inicio else ""}
        if datos["pid"]:
            datos.update(_proceso_hijo_windows(datos["pid"]))
        return datos


def _proceso_hijo_windows(pid_padre: str) -> dict:
    """Memoria/inicio del proceso real (hijo de nssm.exe)."""
    ps = ("$p = Get-CimInstance Win32_Process -Filter \"ParentProcessId=%s\" | Where-Object Name -ne 'conhost.exe' | "
          "Select-Object -First 1; if ($p) { '{0}|{1}|{2}|{3}' -f $p.ProcessId, $p.Name, "
          "[math]::Round($p.WorkingSetSize/1MB,1), $p.CreationDate.ToString('yyyy-MM-dd HH:mm:ss') }") % pid_padre
    texto = shell.salida(["powershell", "-NoProfile", "-Command", ps])
    if "|" not in texto:
        return {}
    pid, nombre, mem, inicio = texto.split("|")[:4]
    return {"proceso": f"{nombre} (PID {pid})", "memoria_mb": mem, "desde": inicio}


# ── systemd ──────────────────────────────────────────────────────────────────
ENV_DIR = Path("/etc/arquis")


def _escapar_env(valor: str) -> str:
    return '"' + valor.replace("\\", "\\\\").replace('"', '\\"') + '"'


def asegurar_usuario(usuario: str) -> None:
    """Crea el usuario de sistema del servicio (sin shell ni login) si no existe."""
    if not usuario or usuario == "root":
        return
    if shell.run(["id", "-u", usuario], check=False, capturar=True, silencioso=True).returncode == 0:
        return
    nologin = shell.which("nologin", ["/usr/sbin/nologin", "/sbin/nologin"]) or "/bin/false"
    shell.run(shell.sudo(["useradd", "--system", "--no-create-home", "--home-dir", str(dir_instalacion() / "data"),
                          "--shell", nologin, usuario]))
    ui.ok(f"Usuario de sistema '{usuario}' creado.")


def preparar_carpetas(usuario: str) -> None:
    """DEPLOY_DIR legible; data/ (HOME: claves de Data Protection) y logs/ escribibles por el servicio."""
    base = dir_instalacion()
    for d in (base, base / "releases", dir_logs(), base / "data"):
        shell.run(shell.sudo(["mkdir", "-p", str(d)]), silencioso=True)
    if usuario and usuario != "root":
        shell.run(shell.sudo(["chown", "-R", f"{usuario}:{usuario}", str(base / "data"), str(dir_logs())]), silencioso=True)
        shell.run(shell.sudo(["chmod", "750", str(base / "data")]), silencioso=True)


class Systemd(Gestor):
    nombre = "systemd"

    def _unidad(self, s: Servicio) -> Path:
        return Path(f"/etc/systemd/system/{s.nombre}.service")

    def _envfile(self, s: Servicio) -> Path:
        return ENV_DIR / f"{s.clave}.env"

    def existe(self, s: Servicio) -> bool:
        return self._unidad(s).exists()

    def _escribir_root(self, ruta: Path, contenido: str, modo: str) -> None:
        import tempfile
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", prefix="arquis-") as f:
            f.write(contenido)
            tmp = f.name
        os.chmod(tmp, 0o600)
        try:
            shell.run(shell.sudo(["install", "-D", "-m", modo, "-o", "root", "-g", "root", tmp, str(ruta)]),
                      silencioso=True)
        finally:
            os.unlink(tmp)

    def instalar(self, s: Servicio, dependencias: list[str] | None = None) -> None:
        usuario = env.get("SERVICE_USER") or "arquis"
        asegurar_usuario(usuario)
        preparar_carpetas(usuario)
        datos = dir_instalacion() / "data"
        variables = {"HOME": str(datos), "DOTNET_CLI_TELEMETRY_OPTOUT": "1", **s.entorno}
        # Secretos (cadena de conexion) en un EnvironmentFile 0600 de root, no en la unidad
        self._escribir_root(self._envfile(s), "".join(f"{k}={_escapar_env(v)}\n" for k, v in variables.items()), "600")
        after = " ".join(["network-online.target"] + [f"{d}.service" for d in dependencias or []])
        lineas = [
            f"# Generado por la CLI de Arquis. Regenerar con: arquis services {s.clave} instalar",
            "[Unit]", f"Description=Arquis - {s.titulo}", f"After={after}", "Wants=network-online.target",
            *(f"Wants={d}.service" for d in dependencias or []),
            "StartLimitIntervalSec=60", "StartLimitBurst=5",
            "", "[Service]", "Type=simple", f"User={usuario}", f"Group={usuario}",
            f"WorkingDirectory={s.carpeta}",
            f"ExecStart={s.ejecutable} {' '.join(s.argumentos)}",
            f"EnvironmentFile={self._envfile(s)}",
            "Restart=always", "RestartSec=5", "KillSignal=SIGINT", "TimeoutStopSec=20",
            f"SyslogIdentifier={s.nombre}",
            f"StandardOutput=append:{s.log_out}", f"StandardError=append:{s.log_err}",
            "NoNewPrivileges=true", "PrivateTmp=true", "ProtectSystem=full", "ProtectHome=read-only",
            "", "[Install]", "WantedBy=multi-user.target", "",
        ]
        self._escribir_root(self._unidad(s), "\n".join(lineas), "644")
        shell.run(shell.sudo(["systemctl", "daemon-reload"]))
        if env.es_verdad("DEPLOY_AUTOSTART"):
            shell.run(shell.sudo(["systemctl", "enable", s.nombre]), check=False, capturar=True)
        ui.ok(f"Servicio {s.nombre} instalado ({self._unidad(s)}, usuario {usuario}).")

    def desinstalar(self, s: Servicio) -> None:
        shell.run(shell.sudo(["systemctl", "disable", "--now", s.nombre]), check=False)
        shell.run(shell.sudo(["rm", "-f", str(self._unidad(s)), str(self._envfile(s))]))
        shell.run(shell.sudo(["systemctl", "daemon-reload"]))
        ui.ok(f"{s.nombre} eliminado.")

    def iniciar(self, s: Servicio) -> None:
        shell.run(shell.sudo(["systemctl", "start", s.nombre]))
        ui.ok(f"{s.nombre} iniciado.")

    def detener(self, s: Servicio) -> None:
        shell.run(shell.sudo(["systemctl", "stop", s.nombre]), check=False)
        ui.ok(f"{s.nombre} detenido.")

    def reiniciar(self, s: Servicio) -> None:
        shell.run(shell.sudo(["systemctl", "restart", s.nombre]))

    def estado(self, s: Servicio) -> dict:
        if not self.existe(s):
            return {"estado": "no instalado"}
        props = dict(l.split("=", 1) for l in shell.salida(
            ["systemctl", "show", s.nombre, "-p",
             "ActiveState,SubState,MainPID,ActiveEnterTimestamp,UnitFileState,MemoryCurrent,NRestarts"]
        ).splitlines() if "=" in l)
        mem = props.get("MemoryCurrent", "")
        return {"estado": f"{props.get('ActiveState', '?')} ({props.get('SubState', '')})",
                "pid": props.get("MainPID", "") if props.get("MainPID") != "0" else "",
                "inicio": props.get("UnitFileState", ""), "desde": props.get("ActiveEnterTimestamp", ""),
                "reinicios": props.get("NRestarts", ""),
                "memoria_mb": f"{int(mem) / 1_048_576:.1f}" if mem.isdigit() else ""}


class SystemdNginx(Systemd):
    """nginx del sistema (paquete de la distribucion): se controla su unidad 'nginx'."""

    def existe(self, s: Servicio) -> bool:
        return bool(shell.which("nginx", ["/usr/sbin/nginx"]))

    def instalar(self, s: Servicio, dependencias=None) -> None:
        if not self.existe(s):
            raise ui.Fallo("nginx no esta instalado: arquis services nginx descargar")
        shell.run(shell.sudo(["systemctl", "enable", "nginx"]), check=False, capturar=True)
        ui.ok("nginx habilitado al arranque.")

    def desinstalar(self, s: Servicio) -> None:
        ui.info("nginx es del sistema; solo se quita la configuracion de Arquis: arquis services nginx quitar-config")

    def iniciar(self, s: Servicio) -> None:
        shell.run(shell.sudo(["systemctl", "start", "nginx"]))
        ui.ok("nginx iniciado.")

    def detener(self, s: Servicio) -> None:
        shell.run(shell.sudo(["systemctl", "stop", "nginx"]), check=False)
        ui.ok("nginx detenido.")

    def reiniciar(self, s: Servicio) -> None:
        shell.run(shell.sudo(["systemctl", "reload-or-restart", "nginx"]))

    def estado(self, s: Servicio) -> dict:
        if not self.existe(s):
            return {"estado": "no instalado"}
        props = dict(l.split("=", 1) for l in shell.salida(
            ["systemctl", "show", "nginx", "-p", "ActiveState,SubState,MainPID,ActiveEnterTimestamp,UnitFileState"]
        ).splitlines() if "=" in l)
        return {"estado": f"{props.get('ActiveState', '?')} ({props.get('SubState', '')})",
                "pid": props.get("MainPID", "") if props.get("MainPID") != "0" else "",
                "inicio": props.get("UnitFileState", ""), "desde": props.get("ActiveEnterTimestamp", "")}


def gestor(s: Servicio | None = None) -> Gestor:
    elegido = env.get("SERVICE_MANAGER") or "auto"
    if elegido == "auto":
        elegido = "nssm" if shell.ES_WINDOWS else "systemd"
    if elegido == "systemd":
        return SystemdNginx() if s is not None and s.clave == "nginx" else Systemd()
    return Nssm()
