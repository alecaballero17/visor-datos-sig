"""Pruebas automaticas y de humo."""
from __future__ import annotations

import http.cookiejar
import json
import time
import urllib.request

from cli.core import env, shell, ui
from cli.core.paths import MOVIL, TESTS


def routing() -> bool:
    """Pruebas de rutas Dijkstra (tests/Arquis.RoutingChecks, sin SQL)."""
    r = shell.run([shell.dotnet(), "run", "--project", TESTS / "Arquis.RoutingChecks"], check=False)
    return r.returncode == 0


def realtime() -> bool:
    """Pruebas SignalR (tests/realtime-checks.cjs, requiere Node)."""
    node = shell.which("node")
    if not node:
        ui.warn("Node no instalado: se omite.")
        return True
    return shell.run([node, TESTS / "realtime-checks.cjs"], check=False).returncode == 0


def compilacion() -> bool:
    """La solucion compila en Release."""
    from cli.core.paths import proyectos_dotnet
    return all(shell.run([shell.dotnet(), "build", p, "-c", "Release", "--nologo", "-v", "q"], check=False,
                         como_usuario=True).returncode == 0 for p in proyectos_dotnet())


def flutter_test() -> bool:
    """flutter test en Movil/."""
    fl = shell.which("flutter")
    if not fl:
        ui.warn("Flutter no instalado: se omite.")
        return True
    return shell.run([fl, "test"], cwd=MOVIL, check=False).returncode == 0


def flutter_analyze() -> bool:
    """flutter analyze en Movil/."""
    fl = shell.which("flutter")
    if not fl:
        ui.warn("Flutter no instalado: se omite.")
        return True
    return shell.run([fl, "analyze", "--no-fatal-infos"], cwd=MOVIL, check=False).returncode == 0


def sql_estados() -> bool:
    """tests/service-state-checks.sql contra la base configurada."""
    from cli.core import sql
    try:
        print(sql.archivo(TESTS / "service-state-checks.sql"))
        return True
    except ui.Fallo as e:
        ui.error(str(e))
        return False


def humo(base: str | None = None) -> bool:
    """Prueba de humo contra la API en marcha: salud, login, capas, busqueda."""
    base = (base or ui.preguntar("URL de la API", env.url_local("backend"))).rstrip("/")
    usuario = ui.preguntar("Usuario de prueba", "admin")
    clave = ui.preguntar("Contrasena", secreto=True) if not ui.AUTO_YES else "Admin123!"
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def pedir(metodo, ruta, cuerpo=None):
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        req = urllib.request.Request(base + ruta, data=datos, method=metodo,
                                     headers={"Content-Type": "application/json"} if datos else {})
        t = time.perf_counter()
        try:
            with opener.open(req, timeout=20) as r:
                return r.status, r.read(), (time.perf_counter() - t) * 1000
        except urllib.error.HTTPError as e:
            return e.code, e.read(), (time.perf_counter() - t) * 1000
        except Exception as e:  # noqa: BLE001
            return 0, str(e).encode(), 0

    casos = [
        ("Salud", "GET", "/health", None, lambda c, b: c == 200),
        ("Login", "POST", "/api/autenticacion/iniciar", {"usuario": usuario, "password": clave}, lambda c, b: c == 200),
        ("Sesion", "GET", "/api/autenticacion/sesion", None, lambda c, b: c == 200),
        ("Catalogo de capas", "GET", "/api/capas", None, lambda c, b: c == 200 and b.startswith(b"[")),
        ("GeoJSON lotes", "GET", "/api/capas/lotes/geojson?bbox=-61.0,-16.45,-60.9,-16.35&limit=50", None, lambda c, b: c == 200),
        ("Busqueda", "GET", "/api/busqueda?texto=1&tamano=5", None, lambda c, b: c == 200),
        ("Cerrar sesion", "POST", "/api/autenticacion/cerrar", {}, lambda c, b: c in (200, 204)),
    ]
    filas, bien = [], True
    for nombre, metodo, ruta, cuerpo, valida in casos:
        codigo, cuerpo_r, ms = pedir(metodo, ruta, cuerpo)
        ok = valida(codigo, cuerpo_r)
        bien &= ok
        filas.append([nombre, f"{metodo} {ruta[:50]}", codigo, f"{ms:.0f} ms",
                      ui.c("ok", ui.C.GREEN) if ok else ui.c("fallo", ui.C.RED)])
    ui.tabla(filas, ["Caso", "Peticion", "HTTP", "Tiempo", ""])
    return bien


def _correr(lista) -> bool:
    resultados = []
    for nombre, fn in lista:
        ui.seccion(nombre)
        inicio = time.time()
        try:
            r = fn()
        except ui.Fallo as e:
            ui.error(str(e))
            r = False
        resultados.append([nombre, ui.c("ok", ui.C.GREEN) if r else ui.c("fallo", ui.C.RED), f"{time.time() - inicio:.0f} s"])
    ui.titulo("Resultado de pruebas")
    ui.tabla(resultados, ["Prueba", "Estado", "Tiempo"])
    return all("ok" in r[1] for r in resultados)


def rapidas() -> bool:
    """Compilacion + routing + realtime (las del CI)."""
    return _correr([("Compilacion Release", compilacion), ("Routing", routing), ("Realtime", realtime)])


def todas() -> bool:
    """Todas las pruebas automaticas (incluye Flutter)."""
    return _correr([("Compilacion Release", compilacion), ("Routing", routing), ("Realtime", realtime),
                    ("Flutter analyze", flutter_analyze), ("Flutter test", flutter_test)])
