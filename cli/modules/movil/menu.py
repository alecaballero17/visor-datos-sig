from cli.core.menu import Menu

from ..entorno import sincronizar
from . import movil

MENU = Menu("movil", "App movil (Flutter)", "Compilar APK con la URL del .env, instalar y depurar", orden=55)
MENU.agregar("apk", "Compilar APK", movil.apk)
MENU.agregar("aab", "Compilar App Bundle (.aab)", movil.appbundle)
MENU.agregar("windows", "Compilar para Windows", movil.windows)
MENU.agregar("instalar", "Instalar APK en dispositivo", movil.instalar, "adb")
MENU.agregar("run", "flutter run (hot reload)", movil.ejecutar)
MENU.agregar("dispositivos", "Dispositivos conectados", movil.dispositivos)
MENU.agregar("logs", "Logs del dispositivo en vivo", movil.logs_dispositivo)
MENU.agregar("env", "Sincronizar Movil/.env", sincronizar.movil)
MENU.agregar("limpiar", "flutter clean + pub get", movil.limpiar)
MENU.agregar("doctor", "flutter doctor", movil.doctor)
