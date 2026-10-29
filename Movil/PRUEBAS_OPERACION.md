# Avance del flujo operativo móvil

Los cambios se limitan a `Movil/`. La API y la web conservan sus contratos.

## Configuración

La app empaqueta `.env.example` con las direcciones locales de demostración. No requiere un `.env` privado para arrancar. Para otro destino se puede sobrescribir la URL al ejecutar o compilar:

```sh
flutter run --dart-define=API_URL_ANDROID=http://10.0.2.2:5080/api
```

Para teléfono por USB:

```sh
adb reverse tcp:5080 tcp:5080
flutter run --dart-define=API_URL_ANDROID=http://127.0.0.1:5080/api
```

El manifiesto permite HTTP para la API local. El seguimiento requiere ubicación solo en primer plano; no solicita ubicación permanente. No hay persistencia de sesión al reiniciar ni cola offline.

## Validación automática

Desde `Movil/`, cuando esté disponible Flutter compatible con Dart ^3.11.0:

```sh
flutter pub get
dart format lib test
flutter analyze
flutter test
flutter build apk --release
```

Las pruebas cubren secuencia, estados terminales, identidad, transporte de cookie, limpieza por 401 y bloqueo operativo del modo simulado. No sustituyen la prueba nativa de cámara/GPS.

En el entorno de implementación Flutter/Dart no estaban en PATH, por lo que los comandos de análisis, tests y compilación quedan pendientes. Se revisaron los cambios y `git diff --check`.

## Ensayo en Android

1. Entrar con un empleado habilitado. Abrir Mis rutas; verificar nombre/roles y asignaciones propias. Probar actualizar, bandeja vacía y servidor inaccesible.
2. Elegir ruta pendiente y comprobar inicio. Revisar que paradas se atiendan por orden, aunque otra esté más cerca. Observado y Omitido cuentan como atendidos.
3. Denegar ubicación o apagar GPS: comprobar mensaje y reintento, sin envío de coordenadas de respaldo. Revisar precisión y hora reales.
4. En modo Simular, comprobar etiqueta ENSAYO y bloqueo del cierre. No se envían esas posiciones. Volver a la bandeja y abrir la ruta para recuperar GPS real.
5. Probar lectura inválida, ausencia de fotos y distancia superior a 30 m. Cerrar con GPS nuevo y de una a tres fotos de cámara; comprobar repetición y eliminación.
6. Interrumpir la red al guardar: formulario y evidencia permanecen. Al reintentar se consulta el punto; si ya está atendido se avanza sin repetir el PUT. Esto reduce duplicados, pero no sustituye idempotencia en servidor.
7. Expirar sesión: debe regresar al login y detener tracking. Salir y entrar con otro empleado; verificar ausencia de datos del anterior.
8. Instalar APK release y repetir con cámara/GPS físicos. Verificar persistencia SQL y actualización web cuando la compatibilidad API/SQL esté resuelta.

Pendientes: navegación externa, modelos tipados completos, validación nativa y compilación APK. Los bloqueos de compatibilidad SQL y obligatoriedad de evidencia/GPS en servidor requieren trabajo separado en backend.
