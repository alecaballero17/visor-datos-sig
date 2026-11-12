# Arquis CLI

Herramienta de línea de comandos para instalar, configurar, operar y desplegar
Arquis. Pensada para **servidores Linux** (Ubuntu/Debian y RHEL/Rocky/Alma);
también funciona en Windows para desarrollo. Solo usa la biblioteca estándar de
Python 3.10+ (el importador de shapefiles usa `pyshp`: `arquis deps pip-cli`).

```bash
./arquis.sh                         # menú interactivo
./arquis.sh --list                  # todos los comandos
./arquis.sh bd migraciones estado   # comando directo
sudo ./arquis.sh deploy completo    # despliegue (necesita root)
./arquis.sh deploy completo --yes   # sin preguntas (valores por defecto)
```

En Windows: `arquis.cmd ...`. Los lanzadores usan `.venv` si existe.

## Servidor Linux desde cero

En un VPS recién creado basta con:

```bash
git clone <repo> && cd visor-datos-sig
sudo ./arquis.sh inicio servidor
```

**El lanzador** (`arquis.sh`) deja lista la propia CLI antes de abrirla:

- instala Python 3.10+ con apt o dnf si falta;
- crea `.venv` (e instala `python3-venv` si hace falta);
- reinstala `cli/requirements/cli.txt` cada vez que el archivo cambia.

Con `sudo`, el `.venv` se crea como tu usuario, no como root.

**`inicio servidor`** revisa todo lo demás y arregla lo que falte, en orden y
preguntando antes de cada paso (con `--yes`, sin preguntar):

| # | Requisito | Si falta |
|---|---|---|
| 1 | .NET 10, sqlcmd, fuentes | apt/dnf con el repositorio de Microsoft |
| 2 | Dependencias Python | pip en `.venv` |
| 3 | `.env` válido | asistente `entorno crear` |
| 4 | NuGet de backend y frontend | `dotnet restore` |
| 5 | dotnet-ef | herramienta local (`.config/dotnet-tools.json`) |
| 6 | SQL Server | Docker, servicio nativo `mssql-server` o uno existente |
| 7 | Base de datos | `bd crear` |
| 8 | Migraciones pendientes | `dotnet ef database update` |
| 9 | Capas SIG | importa los SHP si están en `SHP_DIR` |
| 10 | nginx | instala y configura dominios |
| 11 | HTTPS | Let's Encrypt |
| 12 | Servicios | despliegue completo (systemd) |

Para ver el estado sin cambiar nada: `./arquis.sh inicio revisar`. Al abrir el
menú interactivo también se avisa de lo pendiente. Android/Flutter queda fuera:
no se compila en el servidor.

## Dominios: visor y API en subdominios

```bash
sudo ./arquis.sh services nginx dominios     # o: inicio dominios
```

Pide el dominio del visor (`sig.midominio.com`), el subdominio de la API
(`api.midominio.com`) y el tipo de HTTPS. Comprueba el DNS, escribe nginx, emite
el certificado y reinicia los servicios con la configuración nueva.

```
Navegador ──https://sig.midominio.com──▶ nginx ─┬─ /             → frontend :5180
                                               └─ /api/, /hubs/  → backend  :5080 (127.0.0.1)
Frontend (servidor Blazor) ──http://127.0.0.1:5080──▶ backend
App móvil ──https://api.midominio.com/api──▶ nginx ──▶ backend :5080 (API, SignalR, swagger)
```

- **El frontend llega al backend por localhost.** El JavaScript del navegador usa
  el mismo origen (`sig…/api`), así que no hay CORS y las cookies son propias.
- **La app móvil usa el subdominio de la API**, porque no está en la misma red:
  `entorno movil` escribe esa URL en `Movil/.env`, y el APK se compila en tu equipo.
- **HTTPS:** un solo certificado Let's Encrypt cubre los dos nombres. certbot lo
  renueva solo y recarga nginx. También se puede usar `HTTPS=manual`, con
  `NGINX_SSL_CERT` y `NGINX_SSL_KEY`.
- **Antes de empezar:** crea en el DNS dos registros A, `sig` y `api`, apuntando a
  la IP del VPS (`services nginx dns` los comprueba).
- **Sin dominio** (`WEB_DOMAIN=_`), todo se sirve por la IP del servidor:
  visor en `/` y API en `/api`.

## Módulos

```
inicio     Flujos de un solo comando (desarrollo, servidor)
entorno    .env: asistente, edición, validación, limpieza, .env.example
deps       doctor, paquetes del sistema (apt/dnf/winget), NuGet, dotnet-ef, .venv, pip, pub
libs       Librerías web offline (wwwroot/lib), paquetes obsoletos
bd         Base de datos
  servidor     conexión, SQL Server en Docker, mssql-server (Linux), LocalDB (Windows), login de la app
  migraciones  EF Core: estado, aplicar, ir a versión/rollback, nueva, script, bundle
  scripts      02_BaseDatos/*.sql con registro de ejecución y checksum
  respaldos    BACKUP / RESTORE verificados (historial de msdb)
  consultas    consola SQL, conteos, tamaños, CSV, bitácoras, sesiones
  usuarios     crear, contraseña (PBKDF2 igual que el backend), roles, activar
  capas        verificar SHP, importar, vincular, índices espaciales, reparar
services   Servicios
  build        compilar/publicar backend, frontend y migrador; format; vulnerables
  dev          modo desarrollo desde el código (PID + logs en .setup/)
  backend      servicio del sistema: detalles, iniciar, detener, reiniciar, logs en vivo...
  frontend     ídem
  nginx        ídem + instalación, configuración, nginx -t, recarga, firewall
movil      APK/AAB con la URL del .env, instalar por adb, flutter run, logs
test       pruebas del CI, Flutter, verificación SQL, prueba de humo de la API
deploy     despliegue completo, versiones, rollback, historial, paquete portable
mant       información, puertos ocupados, limpieza
```

## Despliegue

`sudo ./arquis.sh deploy completo` ejecuta, en orden:

1. verificaciones (herramientas, `.env`, permisos, conexión SQL, dotnet-ef);
2. pruebas;
3. publicación en `<DEPLOY_DIR>/releases/<fecha>`;
4. respaldo de la base, migraciones EF y capas;
5. nginx;
6. registro de servicios;
7. cambio del enlace `current` y arranque con comprobación de salud.

**Si la versión nueva no responde, vuelve sola a la anterior.** La base de datos
no se revierte: el respaldo previo queda en la carpeta de respaldos del servidor
SQL (`arquis bd respaldos listar`).

Bajo `sudo`, la compilación (`dotnet publish`, `dotnet ef`) corre como el usuario
dueño del repositorio, para no dejar archivos de root dentro del código; solo la
copia a `/opt/arquis` se hace como root.

```
/opt/arquis/
  current/        → releases/20261112-153000   (enlace simbólico atómico)
  releases/       versiones publicadas (se conservan DEPLOY_KEEP_RELEASES)
  data/           HOME del usuario 'arquis' (claves de Data Protection: las sesiones sobreviven reinicios)
  logs/           backend/frontend (.out/.err)
  deploys.jsonl   historial
/etc/systemd/system/arquis-{backend,frontend}.service
/etc/arquis/{backend,frontend}.env     variables y cadena de conexión (0600, root)
/etc/nginx/conf.d/arquis.conf
```

Servicios systemd: usuario de sistema `arquis` sin shell (se crea solo), reinicio
automático, `ProtectSystem=full`, `NoNewPrivileges` y secretos fuera de la unidad.
`arquis services logs` sigue los logs en vivo; `arquis services estado` muestra
el estado, el PID, la memoria y los reinicios.

nginx (ver «Dominios»). Además, la CLI:

- desactiva el sitio `default` de la distribución si choca en el puerto 80;
- usa `default_server` cuando el dominio es `_`;
- activa `httpd_can_network_connect` si SELinux está en modo enforcing (RHEL);
- abre el firewall con `ufw` o `firewalld` si `DEPLOY_OPEN_FIREWALL=true`.

Para HTTPS, configure `NGINX_SSL_CERT` y `NGINX_SSL_KEY` (por ejemplo, certbot).

Servidor sin SDK ni código fuente: `arquis deploy paquete` crea un `.zip` con la
versión publicada, un `efbundle` para el sistema destino (`linux-x64`,
`linux-arm64`, `win-x64`) y la propia CLI. En el servidor (runtime ASP.NET Core
10, Python 3 y sqlcmd):

```bash
./arquis.sh entorno crear
sudo ./arquis.sh deploy instalar-paquete
```

### Windows

Funciona igual para desarrollo, con LocalDB, `arquis.cmd` y una terminal de
administrador para los servicios. Los servicios se registran con
[NSSM](https://nssm.cc) en `C:\Arquis\tools`, y nginx se descarga de nginx.org.

## Agregar una herramienta

1. Escriba las funciones en `cli/modules/<modulo>/<herramienta>.py` (la docstring
   aparece como ayuda; lance `ui.Fallo("mensaje")` para errores esperados).
2. Regístrelas en `cli/modules/<modulo>/menu.py`:

```python
from cli.core.menu import Menu
from . import herramienta

MENU = Menu("clave", "Título", "Descripción", orden=70)
MENU.agregar("accion", "Título de la acción", herramienta.funcion, "nota corta")
MENU.descubrir(__package__)   # opcional: agrega subcarpetas con su propio menu.py
```

Cualquier carpeta con `menu.py` se descubre sola, tanto en el menú interactivo
como en el modo comando. Utilidades compartidas en `cli/core/`:

- `ui`: salida, preguntas y tablas;
- `shell`: comandos, `sudo` y `como_usuario`;
- `env`: configuración;
- `sql`: sqlcmd;
- `paths`: rutas del repositorio.
