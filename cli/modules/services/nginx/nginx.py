"""nginx como proxy inverso, con dominio unico o subdominios para visor y API.

Modo subdominios (WEB_DOMAIN + API_DOMAIN):

    sig.midominio.com   /         → frontend (Blazor Server, WebSocket /_blazor)
                        /api/     → backend por 127.0.0.1 (mismo origen para el JS
                        /hubs/    → backend    del navegador: sin CORS, cookies propias)
                        /health   → backend
    api.midominio.com   /         → backend (API + SignalR + swagger) → app movil

Modo dominio unico (solo WEB_DOMAIN): igual que el primer bloque, mas /swagger.

El servidor del frontend llama al backend por http://127.0.0.1:BACKEND_PORT
(BackendBaseUrl) y el JavaScript del navegador por el mismo origen
(PublicApiUrl="/"). HTTPS: Let's Encrypt (un certificado para ambos nombres,
renovacion automatica de certbot) o certificados propios.
"""
from __future__ import annotations

import io
import os
import re
import shutil
import socket
import urllib.request
import zipfile
from pathlib import Path

from cli.core import env, shell, ui

from .. import definiciones as d

CONF_LINUX = Path("/etc/nginx/conf.d/arquis.conf")
SSL_DIR = Path("/etc/arquis/ssl")

# https://www.cloudflare.com/ips/  (proxy "nube naranja")
CLOUDFLARE = ["173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22", "141.101.64.0/18",
              "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20", "197.234.240.0/22", "198.41.128.0/17",
              "162.158.0.0/15", "104.16.0.0/13", "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
              "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32", "2405:b500::/32", "2405:8100::/32",
              "2a06:98c0::/29", "2c0f:f248::/32"]


def es_cloudflare(ip: str) -> bool:
    import ipaddress
    try:
        direccion = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(direccion in ipaddress.ip_network(r) for r in CLOUDFLARE)


def _resolver(nombre: str) -> list[str]:
    try:
        return sorted({i[4][0] for i in socket.getaddrinfo(nombre, 80, proto=socket.IPPROTO_TCP)})
    except socket.gaierror:
        return []


def usa_cloudflare(cfg: dict[str, str] | None = None) -> bool:
    """¿Algun dominio configurado resuelve a la red de Cloudflare (proxy activado)?"""
    cfg = cfg or env.cargar()
    if cfg.get("HTTPS") == "cloudflare":
        return True
    nombres = [n for n in (cfg.get("WEB_DOMAIN"), cfg.get("API_DOMAIN")) if n and es_dominio(n)]
    return any(es_cloudflare(ip) for n in nombres for ip in _resolver(n))
ACME_DIR = "/var/www/arquis-acme"
CERT_NOMBRE = "arquis"
LE_DIR = Path("/etc/letsencrypt/live") / CERT_NOMBRE

_PROXY = """
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade           $http_upgrade;
        proxy_set_header Connection        $connection_upgrade;"""


# ── generacion ──────────────────────────────────────────────────────────────────
def _comunes(cfg: dict[str, str], logs: Path, nombre: str) -> str:
    log = lambda n: str(logs / n).replace("\\", "/")
    return f"""
    client_max_body_size {cfg.get('NGINX_MAX_BODY', '50m')};
    access_log {log(f'nginx-{nombre}.access.log')};
    error_log  {log(f'nginx-{nombre}.error.log')} warn;

    gzip on;
    gzip_types text/css application/javascript application/json application/geo+json image/svg+xml;
    gzip_min_length 1024;
"""


def _ubicaciones_web(cfg: dict[str, str], logs: Path, con_swagger: bool) -> str:
    swagger = f"\n    location /swagger   {{ proxy_pass http://arquis_backend;{_PROXY} }}" if con_swagger else ""
    return _comunes(cfg, logs, "web") + f"""
    location /api/ {{
        proxy_pass http://arquis_backend;{_PROXY}
        proxy_read_timeout 300s;
    }}
    location /hubs/ {{
        proxy_pass http://arquis_backend;{_PROXY}
        proxy_read_timeout 1h;
        proxy_buffering off;
    }}
    location = /health  {{ proxy_pass http://arquis_backend;{_PROXY} }}{swagger}
    location / {{
        proxy_pass http://arquis_frontend;{_PROXY}
        proxy_read_timeout 1h;
        proxy_buffering off;
    }}"""


def _ubicaciones_api(cfg: dict[str, str], logs: Path) -> str:
    return _comunes(cfg, logs, "api") + f"""
    location / {{
        proxy_pass http://arquis_backend;{_PROXY}
        proxy_read_timeout 1h;
        proxy_buffering off;
    }}"""


def _acme() -> str:
    """Validacion HTTP-01 de Let's Encrypt (tambien sirve para las renovaciones)."""
    if shell.ES_WINDOWS:
        return ""
    return f"""
    location ^~ /.well-known/acme-challenge/ {{
        root {ACME_DIR};
        default_type text/plain;
    }}"""


def _version_nginx() -> tuple[int, ...]:
    exe = shell.which("nginx", ["/usr/sbin/nginx"])
    if shell.ES_WINDOWS:
        return tuple(int(x) for x in (env.get("NGINX_VERSION") or "1.26.2").split("."))
    if not exe:
        return (1, 18, 0)
    r = shell.run([exe, "-v"], check=False, capturar=True, silencioso=True)
    m = re.search(r"nginx/(\d+)\.(\d+)\.(\d+)", (r.stderr or "") + (r.stdout or ""))
    return tuple(int(x) for x in m.groups()) if m else (1, 18, 0)


def _listen_ssl(ds: str) -> str:
    """`http2 on;` existe desde nginx 1.25.1 (Ubuntu 22.04 trae 1.18 y 24.04 trae 1.24)."""
    if _version_nginx() >= (1, 25, 1):
        return f"listen 443 ssl{ds};\n    http2 on;"
    return f"listen 443 ssl http2{ds};"


def _bloque_servidor(cfg: dict[str, str], logs: Path) -> str:
    be, fe = cfg["BACKEND_PORT"], cfg["FRONTEND_PORT"]
    web = cfg.get("WEB_DOMAIN") or "_"
    api = cfg.get("API_DOMAIN", "").strip()
    puerto = cfg.get("NGINX_PORT") or "80"
    cert, clave = cfg.get("NGINX_SSL_CERT", ""), cfg.get("NGINX_SSL_KEY", "")
    ds = " default_server" if web == "_" else ""
    nombres = " ".join(n for n in (web, api) if n)
    texto = f"""
map $http_upgrade $connection_upgrade {{
    default upgrade;
    ''      close;
}}

upstream arquis_backend  {{ server 127.0.0.1:{be}; keepalive 16; }}
upstream arquis_frontend {{ server 127.0.0.1:{fe}; keepalive 16; }}
"""
    if cfg.get("HTTPS") == "cloudflare":
        texto += "\n# Detras de Cloudflare: registrar la IP real del visitante\n"
        texto += "".join(f"set_real_ip_from {r};\n" for r in CLOUDFLARE)
        texto += "real_ip_header CF-Connecting-IP;\n"
    if cert and clave:
        ssl = f"""
    ssl_certificate     {cert.replace(chr(92), '/')};
    ssl_certificate_key {clave.replace(chr(92), '/')};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:arquis_ssl:10m;
    add_header Strict-Transport-Security "max-age=31536000" always;"""
        texto += f"""
# HTTP → HTTPS (y validacion de Let's Encrypt)
server {{
    listen {puerto}{ds};
    server_name {nombres};{_acme()}
    location / {{ return 301 https://$host$request_uri; }}
}}

# Visor{' + API en /api' if not api else ''}
server {{
    {_listen_ssl(ds)}
    server_name {web};{ssl}
{_ubicaciones_web(cfg, logs, con_swagger=not api)}
}}
"""
        if api:
            texto += f"""
# API publica (app movil)
server {{
    {_listen_ssl("")}
    server_name {api};{ssl}
{_ubicaciones_api(cfg, logs)}
}}
"""
        return texto
    texto += f"""
# Visor{' + API en /api' if not api else ''}
server {{
    listen {puerto}{ds};
    server_name {web};{_acme()}
{_ubicaciones_web(cfg, logs, con_swagger=not api)}
}}
"""
    if api:
        texto += f"""
# API publica (app movil)
server {{
    listen {puerto};
    server_name {api};{_acme()}
{_ubicaciones_api(cfg, logs)}
}}
"""
    return texto


def generar(cfg: dict[str, str] | None = None) -> str:
    cfg = cfg or env.cargar()
    if shell.ES_WINDOWS:
        servidor = _bloque_servidor(cfg, d.dir_logs())
        return f"""# Generado por la CLI de Arquis (arquis services nginx config). No editar a mano.
worker_processes  auto;
pid        logs/nginx.pid;
error_log  logs/error.log warn;

events {{
    worker_connections  1024;
}}

http {{
    include       mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    keepalive_timeout 65;
    server_tokens off;
{servidor}
}}
"""
    return ("# Generado por la CLI de Arquis (arquis services nginx config). No editar a mano.\n"
            "server_tokens off;\n" + _bloque_servidor(cfg, d.dir_logs()))


def ruta_config() -> Path:
    return d.dir_nginx() / "conf" / "nginx.conf" if shell.ES_WINDOWS else CONF_LINUX


# ── instalacion ─────────────────────────────────────────────────────────────────
def instalar_binarios() -> None:
    """Instala nginx (Linux: apt/dnf; Windows: descarga de nginx.org a <DEPLOY_DIR>/nginx)."""
    if not shell.ES_WINDOWS:
        if shell.which("nginx", ["/usr/sbin/nginx"]):
            ui.info("nginx ya esta instalado.")
            return
        gestor = shell.gestor_paquetes()
        if not gestor:
            raise ui.Fallo("No se encontro apt ni dnf para instalar nginx.")
        shell.run(shell.sudo([gestor, "install", "-y", "nginx"]))
        shell.run(shell.sudo(["systemctl", "enable", "--now", "nginx"]), check=False)
        ui.ok("nginx instalado.")
        return
    destino = d.dir_nginx()
    if (destino / "nginx.exe").exists():
        ui.info(f"nginx ya esta en {destino}.")
        return
    version = env.get("NGINX_VERSION") or "1.26.2"
    url = f"https://nginx.org/download/nginx-{version}.zip"
    ui.info(f"Descargando {url} ...")
    with urllib.request.urlopen(url, timeout=120) as r:
        datos = r.read()
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        raiz = f"nginx-{version}/"
        for miembro in z.namelist():
            if not miembro.startswith(raiz) or miembro.endswith("/"):
                continue
            rel_path = Path(miembro[len(raiz):])
            if ".." in rel_path.parts:
                continue
            salida = destino / rel_path
            salida.parent.mkdir(parents=True, exist_ok=True)
            salida.write_bytes(z.read(miembro))
    (destino / "logs").mkdir(exist_ok=True)
    (destino / "temp").mkdir(exist_ok=True)
    ui.ok(f"nginx {version} instalado en {destino}")


SITIO_DEFECTO = [Path("/etc/nginx/sites-enabled/default"), Path("/etc/nginx/conf.d/default.conf")]


def _escribir_linux(ruta: Path, contenido: str) -> None:
    import tempfile
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", prefix="arquis-nginx-") as f:
        f.write(contenido)
        tmp = f.name
    try:
        if ruta.exists():
            shell.run(shell.sudo(["cp", "-p", str(ruta), str(ruta) + ".bak"]), silencioso=True)
        shell.run(shell.sudo(["install", "-D", "-m", "644", tmp, str(ruta)]), silencioso=True)
    finally:
        Path(tmp).unlink(missing_ok=True)


def _sitio_defecto(cfg: dict[str, str]) -> None:
    """El sitio 'default' de la distribucion tambien escucha en :80 como default_server."""
    activos = [r for r in SITIO_DEFECTO if r.exists()]
    if not activos or cfg.get("NGINX_PORT", "80") not in ("80", "443"):
        return
    if ui.confirmar("La distribucion trae un sitio 'default' en el puerto 80 que choca con Arquis. ¿Desactivarlo?", True):
        for r in activos:
            destino = r.with_name(r.name + ".deshabilitado") if r.suffix == ".conf" else None
            shell.run(shell.sudo(["mv", str(r), str(destino)] if destino else ["rm", "-f", str(r)]), silencioso=True)
        ui.ok("Sitio por defecto desactivado.")


def _selinux() -> None:
    """En RHEL/Rocky/Alma con SELinux enforcing nginx no puede conectar a 127.0.0.1:5080 sin este booleano."""
    if not shell.which("getenforce") or shell.salida(["getenforce"]).lower() != "enforcing":
        return
    if shell.salida(["getsebool", "httpd_can_network_connect"]).endswith("on"):
        return
    ui.info("SELinux enforcing: permitiendo a nginx conectar con el backend (httpd_can_network_connect).")
    shell.run(shell.sudo(["setsebool", "-P", "httpd_can_network_connect", "1"]), check=False)


def escribir_config(cfg: dict[str, str] | None = None) -> None:
    """Genera la configuracion a partir del .env, la valida y recarga nginx."""
    cfg = cfg or env.cargar()
    ruta = ruta_config()
    if shell.ES_WINDOWS:
        d.dir_logs().mkdir(parents=True, exist_ok=True)
        if ruta.exists():
            shutil.copy2(ruta, ruta.with_suffix(ruta.suffix + ".bak"))
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(generar(cfg), encoding="utf-8")
    else:
        shell.run(shell.sudo(["mkdir", "-p", str(d.dir_logs()), ACME_DIR]), silencioso=True)
        _escribir_linux(ruta, generar(cfg))
        _sitio_defecto(cfg)
        _selinux()
    ui.ok(f"Configuracion escrita en {ruta}")
    _avisos(cfg)
    if not probar():
        raise ui.Fallo("nginx -t encontro errores en la configuracion.")
    if not shell.ES_WINDOWS:
        activo = shell.salida(["systemctl", "is-active", "nginx"]) == "active"
        shell.run(shell.sudo(["systemctl", "reload" if activo else "start", "nginx"]), check=False)
        ui.ok("nginx recargado." if activo else "nginx iniciado.")


def _avisos(cfg: dict[str, str]) -> None:
    if cfg["BACKEND_HOST"] == "0.0.0.0" or cfg["FRONTEND_HOST"] == "0.0.0.0":
        ui.info("Sugerencia: con nginx, use BACKEND_HOST/FRONTEND_HOST=127.0.0.1 para no exponer los puertos internos.")
    if cfg.get("HTTPS") == "letsencrypt" and not cfg.get("NGINX_SSL_CERT"):
        ui.info("HTTPS pendiente: arquis services nginx https")


def probar() -> bool:
    """nginx -t"""
    s = d.nginx()
    if not Path(s.ejecutable).exists() and not shell.which("nginx"):
        ui.warn("nginx no esta instalado.")
        return False
    cmd = [s.ejecutable, *s.argumentos, "-t"] if shell.ES_WINDOWS else shell.sudo(["nginx", "-t"])
    r = shell.run(cmd, cwd=s.carpeta, check=False, capturar=True, silencioso=True)
    texto = ((r.stdout or "") + (r.stderr or "")).strip()
    (ui.ok if r.returncode == 0 else ui.error)(texto.splitlines()[-1] if texto else "nginx -t")
    if r.returncode != 0 and texto:
        ui.dim(texto[-800:])
    return r.returncode == 0


def recargar() -> None:
    """Aplica la configuracion sin cortar conexiones (nginx -s reload)."""
    if not probar():
        raise ui.Fallo("La configuracion tiene errores; no se recarga.")
    s = d.nginx()
    if shell.ES_WINDOWS:
        shell.run([s.ejecutable, *s.argumentos, "-s", "reload"], cwd=s.carpeta)
    else:
        shell.run(shell.sudo(["systemctl", "reload", "nginx"]))
    ui.ok("nginx recargado.")


def ver_config() -> None:
    ruta = ruta_config()
    print(ruta.read_text(encoding="utf-8") if ruta.exists() else generar())


def vista_previa() -> None:
    """Muestra la configuracion que se generaria con el .env actual."""
    print(generar())


# ── dominios ────────────────────────────────────────────────────────────────────
_DOMINIO = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")


def es_dominio(nombre: str) -> bool:
    return bool(_DOMINIO.match(nombre.lower()))


def _ips_servidor() -> set[str]:
    ips = {env.ip_local()}
    if not shell.ES_WINDOWS:
        ips |= set(shell.salida(["hostname", "-I"]).split())
    return ips


def comprobar_dns(cfg: dict[str, str] | None = None) -> bool:
    """Comprueba que los dominios resuelven a este servidor."""
    cfg = cfg or env.cargar()
    nombres = [n for n in (cfg.get("WEB_DOMAIN"), cfg.get("API_DOMAIN")) if n and es_dominio(n)]
    if not nombres:
        ui.info("No hay dominios configurados (WEB_DOMAIN=_ usa la IP).")
        return True
    propias = _ips_servidor()
    bien = True
    filas = []
    cloudflare = False
    for n in nombres:
        ips = _resolver(n)
        if not ips:
            estado, bien = ui.c("no resuelve", ui.C.RED), False
        elif all(es_cloudflare(i) for i in ips):
            estado, cloudflare = ui.c("Cloudflare (proxy)", ui.C.CYAN), True
        elif propias & set(ips):
            estado = ui.c("apunta aqui", ui.C.GREEN)
        else:
            estado = ui.c("otra IP (¿NAT/proxy?)", ui.C.YELLOW)
        filas.append([n, ", ".join(ips) or "-", estado])
    ui.tabla([[f[0], f[1][:60], f[2]] for f in filas], ["Dominio", "Resuelve a", "Estado"])
    ui.dim("IPs de este servidor: " + ", ".join(sorted(propias)))
    if cloudflare:
        ui.info("El DNS pasa por Cloudflare: use HTTPS=cloudflare (certificado de origen). "
                "Let's Encrypt por HTTP no funciona detras del proxy.")
    if not bien:
        ui.warn("Cree registros DNS tipo A apuntando a la IP publica del servidor y espere a que propaguen.")
    return bien


def dominios() -> None:
    """Asistente: dominio del visor, subdominio de la API y HTTPS."""
    cfg = env.cargar()
    ui.info("Ejemplo: visor en sig.midominio.com y API (app movil) en api.midominio.com.")
    web = ui.preguntar("Dominio del visor (o _ para usar la IP del servidor)",
                       cfg["WEB_DOMAIN"] if cfg["WEB_DOMAIN"] != "_" else "").strip().lower() or "_"
    if web != "_" and not es_dominio(web):
        raise ui.Fallo(f"'{web}' no parece un dominio valido.")
    api = ""
    if web != "_":
        base = web.split(".", 1)[1] if web.count(".") >= 2 else web
        api = ui.preguntar("Subdominio de la API para la app movil (vacio = la API queda en el dominio del visor /api)",
                           cfg.get("API_DOMAIN") or f"api.{base}").strip().lower()
        if api and not es_dominio(api):
            raise ui.Fallo(f"'{api}' no parece un dominio valido.")
        if api == web:
            api = ""
    https = "none"
    if web != "_":
        claves = ["letsencrypt", "cloudflare", "manual", "none"]
        opciones = ["Let's Encrypt (gratis, automatico; DNS apuntando directo al servidor)",
                    "Cloudflare: certificado de origen (si el DNS usa el proxy de Cloudflare)",
                    "Certificado propio (rutas a .pem)", "Sin HTTPS"]
        cf = usa_cloudflare(dict(cfg, WEB_DOMAIN=web, API_DOMAIN=api))
        if cf:
            ui.info("Sus dominios pasan por Cloudflare (proxy): se recomienda el certificado de origen.")
        defecto = claves.index(cfg["HTTPS"]) if cfg.get("HTTPS") in claves and cfg["HTTPS"] != "none" else (1 if cf else 0)
        https = claves[ui.elegir("HTTPS", opciones, defecto)]
    cfg.update(NGINX_ENABLED="true", WEB_DOMAIN=web, API_DOMAIN=api, HTTPS=https,
               BACKEND_HOST="127.0.0.1", FRONTEND_HOST="127.0.0.1", BACKEND_PUBLIC_URL="")
    if https == "letsencrypt":
        cfg["LETSENCRYPT_EMAIL"] = ui.preguntar("Correo para avisos de vencimiento", cfg.get("LETSENCRYPT_EMAIL") or "")
        if not (LE_DIR / "fullchain.pem").exists():
            cfg["NGINX_SSL_CERT"] = cfg["NGINX_SSL_KEY"] = ""   # hasta emitirlo
    elif https == "cloudflare":
        if not str(cfg.get("NGINX_SSL_CERT", "")).startswith(str(SSL_DIR)):
            cfg["NGINX_SSL_CERT"] = cfg["NGINX_SSL_KEY"] = ""   # se completa al pegar el certificado
    elif https == "manual":
        cfg["NGINX_SSL_CERT"] = ui.preguntar("Ruta del certificado (fullchain.pem)", cfg.get("NGINX_SSL_CERT"))
        cfg["NGINX_SSL_KEY"] = ui.preguntar("Ruta de la clave privada (privkey.pem)", cfg.get("NGINX_SSL_KEY"))
    else:
        cfg["NGINX_SSL_CERT"] = cfg["NGINX_SSL_KEY"] = ""
    env.escribir(cfg)
    ui.ok(".env actualizado.")
    resumen_urls(cfg)
    if web != "_":
        ui.seccion("DNS")
        comprobar_dns(cfg)
    if ui.confirmar("¿Aplicar ahora (nginx, certificado y reinicio de servicios)?", True):
        aplicar()


def resumen_urls(cfg: dict[str, str] | None = None) -> None:
    cfg = cfg or env.cargar()
    filas = [["Visor (navegador)", env.url_publica("web", cfg)],
             ["API publica (app movil)", env.url_api_movil(cfg, android=False)],
             ["Frontend → backend (interno)", env.url_interna_api(cfg)]]
    ui.tabla(filas, ["", "URL"])


def aplicar() -> None:
    """Escribe nginx, emite/renueva el certificado si corresponde y reaplica el entorno a los servicios."""
    from .. import control
    cfg = env.cargar()
    instalar_binarios()
    if cfg.get("HTTPS") in ("letsencrypt", "cloudflare") and not cfg.get("NGINX_SSL_CERT"):
        https()
    else:
        escribir_config()
    for clave in ("backend", "frontend"):
        s = d.obtener(clave)
        if control.gestor(s).existe(s):
            control.gestor(s).actualizar_entorno(s)
            control.gestor(s).reiniciar(s)
            ui.ok(f"{s.nombre} reiniciado con la configuracion nueva.")
    ui.info("Regenere la app movil con la URL nueva si cambio: arquis entorno movil (y compile en su equipo)")


# ── HTTPS (Let's Encrypt) ───────────────────────────────────────────────────────
def _instalar_certbot() -> str:
    exe = shell.which("certbot", ["/usr/bin/certbot", "/snap/bin/certbot"])
    if exe:
        return exe
    gestor = shell.gestor_paquetes()
    if gestor in ("dnf", "yum") and not shell.salida(["sh", "-c", "rpm -q epel-release"]).startswith("epel"):
        shell.run(shell.sudo([gestor, "install", "-y", "epel-release"]), check=False)
    if not gestor:
        raise ui.Fallo("Instale certbot manualmente.")
    shell.run(shell.sudo([gestor, "install", "-y", "certbot"]))
    exe = shell.which("certbot", ["/usr/bin/certbot"])
    if not exe:
        raise ui.Fallo("No se pudo instalar certbot.")
    return exe


def certificado() -> None:
    """Emite (o amplia) un certificado Let's Encrypt para WEB_DOMAIN y API_DOMAIN y activa HTTPS."""
    if shell.ES_WINDOWS:
        raise ui.Fallo("Let's Encrypt automatico solo en Linux. En Windows use HTTPS=manual.")
    cfg = env.cargar()
    nombres = [n for n in (cfg.get("WEB_DOMAIN"), cfg.get("API_DOMAIN")) if n and es_dominio(n)]
    if not nombres:
        raise ui.Fallo("Configure dominios reales primero: arquis services nginx dominios")
    if cfg.get("NGINX_PORT", "80") != "80":
        raise ui.Fallo("Let's Encrypt valida por el puerto 80: use NGINX_PORT=80.")
    if not comprobar_dns(cfg) and not ui.confirmar("Hay dominios que no resuelven. ¿Intentar igualmente?", False):
        return
    if usa_cloudflare(cfg):
        ui.warn("Los dominios pasan por el proxy de Cloudflare: Let's Encrypt (HTTP-01) fallara con 'redirect loop'.")
        i = ui.elegir("¿Que hacer?", ["Usar el certificado de origen de Cloudflare (recomendado)",
                                      "Intentar Let's Encrypt igualmente (desactive antes la nube naranja en Cloudflare)",
                                      "Cancelar"], 0)
        if i == 0:
            cloudflare_origen()
            return
        if i == 2:
            return
    certbot = _instalar_certbot()
    # 1) nginx solo HTTP (sirve /.well-known/acme-challenge)
    if not (LE_DIR / "fullchain.pem").exists():
        escribir_config(dict(cfg, NGINX_SSL_CERT="", NGINX_SSL_KEY=""))
    else:
        escribir_config()
    # 2) emitir / ampliar
    cmd = [certbot, "certonly", "--webroot", "-w", ACME_DIR, "--cert-name", CERT_NOMBRE,
           "--non-interactive", "--agree-tos", "--keep-until-expiring", "--expand",
           "--deploy-hook", "systemctl reload nginx"]
    cmd += ["--email", cfg["LETSENCRYPT_EMAIL"]] if cfg.get("LETSENCRYPT_EMAIL") else ["--register-unsafely-without-email"]
    for n in nombres:
        cmd += ["-d", n]
    shell.run(shell.sudo(cmd))
    # 3) activar HTTPS
    cfg.update(HTTPS="letsencrypt", NGINX_SSL_CERT=str(LE_DIR / "fullchain.pem"), NGINX_SSL_KEY=str(LE_DIR / "privkey.pem"))
    env.escribir(cfg)
    escribir_config(cfg)
    ui.ok("HTTPS activo para: " + ", ".join(nombres))
    _renovacion()


def https() -> None:
    """Activa HTTPS segun HTTPS del .env (Let's Encrypt o certificado de origen de Cloudflare)."""
    cfg = env.cargar()
    if cfg.get("HTTPS") == "cloudflare" or (cfg.get("HTTPS") != "manual" and usa_cloudflare(cfg)):
        cloudflare_origen()
    else:
        certificado()


def _leer_pem(titulo: str, marca: str) -> str:
    """Pide una ruta a un archivo .pem o el contenido pegado (hasta la linea -----END ...-----)."""
    ui.info(f"{titulo}: pegue el contenido completo (desde -----BEGIN hasta -----END) o escriba la ruta de un archivo.")
    primera = input("  › ").strip()
    if primera and not primera.startswith("-----BEGIN") and Path(primera).expanduser().is_file():
        texto = Path(primera).expanduser().read_text(encoding="utf-8")
    else:
        lineas = [primera]
        while not lineas[-1].startswith("-----END"):
            try:
                lineas.append(input().strip())
            except EOFError:
                break
        texto = "\n".join(l for l in lineas if l) + "\n"
    if marca not in texto or "-----END" not in texto:
        raise ui.Fallo(f"No parece un {titulo.lower()} valido (falta '{marca}').")
    return texto


def cloudflare_origen() -> None:
    """Instala el certificado de origen de Cloudflare (15 anios, sin renovaciones) y activa HTTPS."""
    cfg = env.cargar()
    ui.seccion("Certificado de origen de Cloudflare")
    print("""  En el panel de Cloudflare de su dominio:
    1. SSL/TLS → Origin Server → Create Certificate
       (clave RSA, nombres: *.{dom} y {dom}, validez 15 anios) → Create
    2. Deje esa pantalla abierta: copie 'Origin Certificate' y 'Private Key' aqui.
    3. Luego: SSL/TLS → Overview → modo 'Full (strict)'.
""".format(dom=(cfg.get("WEB_DOMAIN") or "midominio.com").split(".", 1)[-1]))
    cert = _leer_pem("Certificado (Origin Certificate)", "BEGIN CERTIFICATE")
    clave = _leer_pem("Clave privada (Private Key)", "PRIVATE KEY")
    destino_cert, destino_clave = SSL_DIR / "cloudflare-origin.pem", SSL_DIR / "cloudflare-origin.key"
    if shell.ES_WINDOWS:
        destino_cert = d.dir_instalacion() / "ssl" / "cloudflare-origin.pem"
        destino_clave = d.dir_instalacion() / "ssl" / "cloudflare-origin.key"
        destino_cert.parent.mkdir(parents=True, exist_ok=True)
        destino_cert.write_text(cert, encoding="utf-8")
        destino_clave.write_text(clave, encoding="utf-8")
    else:
        _instalar_secreto(destino_cert, cert, "644")
        _instalar_secreto(destino_clave, clave, "600")
    cfg.update(HTTPS="cloudflare", NGINX_SSL_CERT=str(destino_cert), NGINX_SSL_KEY=str(destino_clave))
    env.escribir(cfg)
    escribir_config(cfg)
    ui.ok("HTTPS activo con el certificado de origen de Cloudflare.")
    ui.warn("En Cloudflare ponga SSL/TLS → modo 'Full (strict)' (con 'Flexible' habra bucles de redireccion).")


def _instalar_secreto(ruta: Path, contenido: str, modo: str) -> None:
    import tempfile
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", prefix="arquis-ssl-") as f:
        f.write(contenido)
        tmp = f.name
    os.chmod(tmp, 0o600)
    try:
        shell.run(shell.sudo(["install", "-D", "-m", modo, "-o", "root", "-g", "root", tmp, str(ruta)]), silencioso=True)
    finally:
        os.unlink(tmp)


def _renovacion() -> None:
    timers = shell.salida(["systemctl", "list-timers", "--all"])
    if "certbot" in timers or "snap.certbot" in timers:
        ui.ok("Renovacion automatica activa (timer de certbot).")
    else:
        shell.run(shell.sudo(["systemctl", "enable", "--now", "certbot-renew.timer"]), check=False, capturar=True)
        ui.info("Verifique la renovacion con: arquis services nginx renovar-prueba")


def renovar_prueba() -> None:
    """certbot renew --dry-run"""
    shell.run(shell.sudo(["certbot", "renew", "--dry-run", "--cert-name", CERT_NOMBRE]), check=False)


def estado_certificado() -> None:
    """Dominios y fecha de vencimiento del certificado."""
    if shell.ES_WINDOWS:
        ui.info(f"Certificado: {env.get('NGINX_SSL_CERT') or 'ninguno'}")
        return
    shell.run(shell.sudo(["certbot", "certificates", "--cert-name", CERT_NOMBRE]), check=False)


# ── otros ───────────────────────────────────────────────────────────────────────
def habilitar() -> None:
    """Activa nginx (alias del asistente de dominios)."""
    dominios()


def quitar_config() -> None:
    ruta = ruta_config()
    if ruta.exists() and ui.confirmar(f"¿Eliminar {ruta}?"):
        if shell.ES_WINDOWS:
            ruta.unlink()
        else:
            shell.run(shell.sudo(["rm", "-f", str(ruta)]))
            shell.run(shell.sudo(["systemctl", "reload", "nginx"]), check=False)
        ui.ok("Configuracion eliminada.")


def firewall() -> None:
    """Abre en el firewall los puertos publicos de nginx (80 y 443 si hay HTTPS)."""
    puerto = env.get("NGINX_PORT")
    puertos = [puerto] + (["443"] if env.get("NGINX_SSL_CERT") or env.get("HTTPS") != "none" else [])
    for p in puertos:
        if shell.ES_WINDOWS:
            shell.run(["netsh", "advfirewall", "firewall", "add", "rule", f"name=Arquis nginx {p}", "dir=in",
                       "action=allow", "protocol=TCP", f"localport={p}"], check=False)
        elif shell.which("ufw"):
            shell.run(shell.sudo(["ufw", "allow", f"{p}/tcp"]), check=False)
        elif shell.which("firewall-cmd"):
            shell.run(shell.sudo(["firewall-cmd", "--permanent", f"--add-port={p}/tcp"]), check=False)
        else:
            ui.warn("No se encontro ufw ni firewalld; abra el puerto manualmente.")
            return
    if not shell.ES_WINDOWS and not shell.which("ufw") and shell.which("firewall-cmd"):
        shell.run(shell.sudo(["firewall-cmd", "--reload"]), check=False)
    ui.ok("Reglas de firewall aplicadas: " + ", ".join(puertos))
