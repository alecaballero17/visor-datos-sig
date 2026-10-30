# Avance del flujo operativo móvil

## Actualización del 29/10/2026 — Windows

Bandeja como pantalla posterior al login, modelos tipados completos, validación de secuencia/asignación y navegación externa implementados. Google Maps y Waze abren el siguiente destino; ante falta de app se intenta Google Maps web. El GPS caduca a los diez segundos, permite abrir ajustes y volver del ensayo a GPS real; el seguimiento se detiene fuera de primer plano.

Las pruebas automatizadas cubren modelos, secuencia, estados, sesión/cookie, coordenadas inválidas, antigüedad GPS, cambio de empleado y enlaces externos con lanzador sustituido. No usan servicios HTTP reales ni dispositivos GPS.

Resultados ejecutados el 29/10: `flutter test --no-pub` pasó las **18 pruebas**. El análisis dirigido a los ocho archivos principales nuevos/modificados terminó con **No issues found**. El análisis global terminó con **18 diagnósticos preexistentes** (advertencias e información, sin errores); por eso su código de salida sigue siendo 1. `git diff --check` pasó.

Entorno comprobado: Flutter 3.44.0/Dart 3.12.0 en Windows. `flutter doctor -v` no encuentra Android SDK ni dispositivo Android. `flutter pub get` descarga dependencias, pero indica habilitar el modo de desarrollador de Windows para enlaces simbólicos de plugins. Resolver ambos puntos antes de compilar/instalar Android.

Para repetir las comprobaciones sin repetir la resolución de dependencias:

```powershell
flutter analyze --no-pub
flutter test --no-pub
```

El análisis global conserva advertencias preexistentes de imports, código muerto y APIs deprecadas; no equivalen a errores de compilación. El APK y el ensayo integrado siguen pendientes. Las notas históricas siguientes corresponden al avance anterior.

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
