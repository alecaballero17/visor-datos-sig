from cli.core.menu import Menu

from . import pruebas

MENU = Menu("test", "Pruebas", "Pruebas automaticas, de base de datos y de humo", orden=60)
MENU.agregar("rapidas", "Pruebas rapidas (CI)", pruebas.rapidas, "build + routing + realtime", requiere=("dotnet",))
MENU.agregar("todas", "Todas las pruebas", pruebas.todas, requiere=("dotnet",))
MENU.agregar("routing", "Routing (Dijkstra)", pruebas.routing, requiere=("dotnet",))
MENU.agregar("realtime", "Realtime (SignalR, Node)", pruebas.realtime)
MENU.agregar("flutter", "Flutter test", pruebas.flutter_test, requiere=("flutter",))
MENU.agregar("analyze", "Flutter analyze", pruebas.flutter_analyze, requiere=("flutter",))
MENU.agregar("sql", "Verificacion SQL de estados", pruebas.sql_estados, requiere=("base",))
MENU.agregar("humo", "Prueba de humo de la API", pruebas.humo, "contra la API en marcha")
