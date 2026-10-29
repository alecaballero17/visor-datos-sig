# Plan de implementación de GeoIT Operaciones — Web y Android

Actualizado: 28 de octubre de 2026. Incluye el avance del código móvil y el estado de la web, la API y SQL Server. Las pruebas SQL citadas corresponden al 27/10/2026; no se repitieron tras el avance móvil.

## Cómo interpretar el estado

- **Implementado en código:** existe en el árbol de trabajo; no implica compilación ni aceptación funcional.
- **Verificado:** tiene una prueba ejecutada y se indica su alcance y fecha.
- **Pendiente:** falta implementación, preparación del entorno o ejecución de pruebas.
- **Bloqueado:** no puede aceptarse el flujo integrado hasta resolver una dependencia.

Los cambios móviles del 28/10 están en el árbol de trabajo y no se presentan como una versión publicada ni como un APK probado. En ese avance no se modificaron la web ni el backend. Esta actualización modifica únicamente el plan.

## 1. Alcance acordado

- **Web:** utilizada por el administrador para consultar catastro, asignar cortes/reconexiones y supervisar resultados.
- **Android:** utilizada por empleados con perfiles Cortador, Reconector y otros que se habiliten.
- **Persistencia:** una sola base SQL Server. Web y Android acceden por la misma API .NET; Android no se conecta al puerto SQL.
- **Datos:** utilizar la base preparada con `02_BaseDatos/` y sus geometrías existentes. No importar automáticamente `03_DatosPrueba/` ni generar clientes, rutas o métricas ficticias.
- **Objetivo:** demostración académica funcional y aceptable. No se exige endurecimiento de seguridad, JWT, operación offline completa, publicación en Play Store ni soporte iOS.
- Conservar `Movil/lib/modules/`, los servicios Dio y los widgets actuales. No reescribir la arquitectura ni introducir Bloc/Riverpod como condición para terminar.
- OCR y seguimiento con la aplicación cerrada quedan fuera de la entrega mínima.

## 2. Evidencia de pruebas y estado real

Informe detallado: [Pruebas con SQL Server](04_Documentacion/07_PRUEBAS_SQLSERVER_ANDROID.md).

En el diagnóstico del 27/10 se verificó el contenedor `arquis-sql-1`, del contexto Docker `desktop-linux`, con SQL Server publicado en `127.0.0.1:14330`. La base original `VisorDatosSIG` contenía lo siguiente; este inventario no se volvió a consultar el 28/10:

| Elemento | Cantidad verificada |
|---|---:|
| Códigos fijos | 6.271 |
| Vías | 578: 576 LineString y 2 MultiLineString, SRID 4326 |
| Lotes | 15.281 |
| Manzanas | 863 |
| Conexiones con Estado=1 | 6.271 |
| Estados de servicio sin verificar | 6.271 |
| Conexiones cuyas columnas de coordenadas no coinciden con su geometría | 6.265 |

**La API del repositorio no arranca directamente sobre esta base:** intenta aplicar la migración inicial sobre tablas existentes. No se debe confundir una compilación correcta con integración lista.

Para continuar el diagnóstico se creó `VisorDatosSIG_Pruebas_20261027` mediante backup/restauración y una copia temporal de la API fuera del repositorio. Solo allí se omitieron los inicializadores incompatibles, se ajustaron mapeos y se corrigieron coordenadas. **Esas adaptaciones no están implementadas en el código del repositorio ni aplicadas al catastro original.**

Con las adaptaciones temporales se comprobaron login/sesión/cierre, consulta de capas, búsqueda, asignación, Dijkstra, corte, reconexión, persistencia de lectura/evidencia y eventos SignalR reales. El servidor rechazó coordenadas a más de 30 m, pero aceptó una observación sin GPS ni foto. La ficha de agua siguió fallando por usar propiedades `geography` sobre columnas `geometry`.

La web entregó HTTP 200 para `/login`, `/dashboard` y su recurso de actualización en vivo. Esto no certifica su interacción visual. No se ejecutó Android: Flutter/SDK Android no estaban disponibles en PATH y no había navegador automatizable.

### Resumen actual por plataforma

| Plataforma / área | Hecho | Falta para aceptar |
|---|---|---|
| Web: acceso y catastro | Pantallas de acceso, mapa, capas y búsqueda existentes | Prueba visual e interactiva con la API del repositorio y SQL compatible |
| Web: asignaciones | Vistas de cortes/reconexiones, selección de partida, previsualización Dijkstra y consulta de rutas | Ensayar selección → previsualización → persistencia; revisar elegibilidad e importes de ejemplo |
| Web: supervisión | Dashboard, monitor GPS y suscripciones SignalR existentes | Verificar indicadores, marcadores, estados terminales y reconexión con Android |
| API / SQL compartidos | Contratos REST, ruteo y emisión de eventos existentes; diagnóstico en copia temporal | Corregir fase 0 y validaciones de cierre en el repositorio |
| Móvil: acceso | Identidad de sesión en memoria, consulta de sesión, limpieza al salir/401 y retorno al login implementados | Ejecutar pruebas y comprobar cambio de empleado en Android |
| Móvil: órdenes | Bandeja con selección/inicio de ruta, paradas ordenadas, progreso y reintento implementados | Modelos tipados completos y validación contra asignaciones SQL |
| Móvil: GPS | Captura reciente, precisión/hora, errores, reintento y bloqueo operativo de simulación implementados | Validar permisos, ciclo de vida y lecturas en Android; añadir navegación externa |
| Móvil: atención | Lectura válida, motivo, 1–3 fotos de cámara, JSON/Base64 y recuperación básica de cierre implementados | Pruebas del formulario, cámara, GPS, red y persistencia; validación obligatoria en servidor |
| Entrega Android | Configuración empaquetada, HTTP local y pruebas automatizadas escritas | Toolchain, análisis, ejecución de tests, emulador/teléfono y APK release instalado |

### Evidencia disponible y límites

- **Verificado el 27/10:** ensayos HTTP/SQL y SignalR real descritos arriba, con adaptaciones temporales fuera del repositorio. Pasaron las comprobaciones de ruteo .NET y de suscripciones web con un doble de hub; consultar [informe SQL](04_Documentacion/07_PRUEBAS_SQLSERVER_ANDROID.md) y [guía de tests web](tests/README.md).
- **Verificado el 28/10:** revisión estructural de los archivos Dart cambiados e imports relativos, XML Android, presencia del asset de configuración y `git diff --check`. Estas comprobaciones no sustituyen al analizador de Dart.
- **No ejecutado en el avance móvil:** `flutter analyze`, `flutter test`, compilación e instalación APK. Los intentos de análisis y tests devolvieron `flutter: command not found`; Flutter/Dart no estaban disponibles en PATH.
- **No certificado:** interacción visual de la web, funcionamiento Android, cámara/GPS físicos y circuito integrado completo con el código del repositorio.

Guía móvil de ejecución y ensayo: [Movil/PRUEBAS_OPERACION.md](Movil/PRUEBAS_OPERACION.md).

## 3. Fase 0 — Estabilizar la API contra la base real

**Estado: pendiente y bloqueante para aceptar tanto web como Android.** El avance móvil no corrigió estos puntos. Se puede continuar con trabajo independiente del cliente mientras se prepara el entorno; las pruebas integradas requieren completar esta fase.

Los siguientes son bloqueos de compatibilidad, no un proyecto de seguridad.

1. Configurar la conexión Linux por variable `ConnectionStrings__DefaultConnection`: servidor `127.0.0.1,14330`, base `VisorDatosSIG` y credenciales locales. No guardar contraseñas en Git. La configuración actual apunta a LocalDB/instancia Windows.
2. Resolver la inicialización de una base importada por scripts: evitar ejecutar `InitialCreate` sobre tablas existentes. Definir y probar una estrategia explícita para bases SQL existentes y bases nuevas; no insertar historiales de migración a ciegas.
3. Alinear EF con las tablas reales `UsuarioMenu`, `BitacoraAcceso` y revisar `BitacoraMigracion`. Probar los inicializadores sin duplicar ni perder roles al reiniciar.
4. Declarar `HasColumnType("geometry")` en las geometrías de vías, códigos, lotes y manzanas. Las pruebas detectaron GeoJSON con ejes invertidos al usar el mapeo predeterminado `geography`.
5. Preparar un script revisable para corregir `CodigosFijos.Latitud` desde `Geom.STY` y `Longitud` desde `Geom.STX`, exclusivamente para geometrías Point válidas. Respaldar antes y comprobar límites de San Ignacio; no intercambiar valores por suposición. Evitar que importaciones posteriores reproduzcan la inconsistencia.
6. Ajustar EF para guardar `CodigosFijos` con triggers, por ejemplo deshabilitando la cláusula SQL OUTPUT en el mapeo de esa tabla. Sin esto el cierre de cortes falla con SQL 334. Declarar precisión de lecturas/importes.
7. Corregir consultas de agua que usan `.Lat`, `.Long` o variables `geography` sobre `geometry`. Revisar las distancias: SRID 4326 en geometry no implica metros.
8. Aclarar elegibilidad de cortes/reconexiones con los estados disponibles. No asumir deuda real: la API contiene importes constantes de ejemplo y el catastro no acredita estados comerciales verificados. Para el ensayo, usar selección explícita del administrador y etiquetar cualquier supuesto.

**Aceptación:** arrancar el código del repositorio sin parches temporales sobre una copia de la base; login, capas con coordenadas correctas, ficha y asignaciones responden; reiniciar sin errores. Corte cambia Estado a 3 y reconexión a 1, conservando datos y actualizando el dashboard.

## 4. Fase 1 — Preparar Android y conectividad en Zorin OS

**Estado: configuración de la app implementada; toolchain y ejecución pendientes.**

### Hecho en código

- `main.dart` carga `Movil/.env.example`, incluido como asset en `pubspec.yaml`. Ya no se exige crear un `.env` privado para arrancar.
- Valores de demostración: `API_URL_LOCAL=http://localhost:5080/api` y `API_URL_ANDROID=http://10.0.2.2:5080/api`.
- `ApiProvider` permite sobrescribir esas URLs con `--dart-define` al ejecutar o compilar.
- El manifiesto declara Internet y permite HTTP para la API local de demostración. Se retiraron los permisos de ubicación permanente/servicio en segundo plano que no requiere el alcance mínimo.
- Se corrigieron imports relativos de servicios móviles que no resolvían el cliente de API.

### Falta realizar

1. Instalar/configurar Flutter compatible con Dart `^3.11.0`, JDK compatible con Gradle, Android SDK, herramientas de compilación y platform-tools/adb. Ejecutar `flutter doctor -v` y resolver licencias/toolchain.
2. Usar VS Code con soporte Flutter/Dart. Android Studio es opcional: el SDK y Android Emulator se pueden preparar por línea de comandos.
3. Para emulador, crear un dispositivo virtual con imagen compatible con la arquitectura de la laptop, comprobar virtualización y KVM en Zorin, e iniciarlo desde terminal o VS Code. La ausencia de `/dev/kvm` en la sesión anterior no acredita el estado del anfitrión.
4. Alternativa: teléfono Android por USB con depuración habilitada. Comprobar `adb devices` y `flutter devices`.
5. Comprobar `/health` desde Android, ejecutar `flutter pub get`, `flutter analyze` y `flutter run`. Revisar plugins nativos de voz/LLM si bloquean la compilación, sin ampliar el alcance para utilizarlos.

Emulador:

```sh
flutter run --dart-define=API_URL_ANDROID=http://10.0.2.2:5080/api
```

Teléfono por USB:

```sh
adb reverse tcp:5080 tcp:5080
flutter run --dart-define=API_URL_ANDROID=http://127.0.0.1:5080/api
```

Para Wi-Fi, usar la IP LAN de Zorin y comprobar escucha de la API y acceso de red. Android se conecta a la API, nunca al puerto SQL. Al generar el APK debe conservarse la URL correspondiente al entorno del ensayo.

**Aceptación pendiente:** app arrancando en Android con la configuración elegida y API accesible desde el dispositivo.

## 5. Fase 2 — Acceso de empleados y contratos reales

Mantener la autenticación por cookie existente. No migrar a JWT para esta entrega.

| Acción | Contrato actual |
|---|---|
| Login | `POST /api/autenticacion/iniciar`, JSON `{usuario,password,origen:"movil"}`; devuelve identidad y cookie `Arquis.Auth` |
| Sesión | `GET /api/autenticacion/sesion` |
| Salir | `POST /api/autenticacion/cerrar` |
| Rutas del empleado | `GET /api/rutas-trabajo/asignadas?operario={login}` |
| Detalle | `GET /api/rutas-trabajo/{id}` |
| Iniciar | `PUT /api/rutas-trabajo/{id}/iniciar` |
| Cerrar punto | `PUT /api/rutas-trabajo/{rutaId}/puntos/{puntoId}/ejecutar`, JSON |
| Posición | `POST /api/tracking/posicion` |

### Hecho en código

- `SesionUsuario` conserva login, nombre y roles; rechaza una identidad sin usuario. Se mantiene cookie en memoria.
- Login conserva la identidad devuelta y limpia el campo de contraseña. Tracking consulta `/autenticacion/sesion` y usa el login real, sin adoptar `Operario` como identidad de respaldo.
- Un 401 elimina cookie/identidad, limpia tracking y solicita regreso al login. Logout realiza limpieza local incluso si falla su petición.
- La bandeja muestra nombre y roles del empleado y consulta sus asignaciones.
- El registro informa que una cuenta necesita habilitación administrativa; ya no asegura que registrar equivalga a tener permiso de trabajo de campo.

### Falta realizar / verificar

1. Ejecutar las pruebas de cookie/401 e identidad y comprobar navegación real tras expiración.
2. Salir y entrar con otro empleado; verificar rutas, identidad, posición y seguimiento sin datos de la sesión anterior.
3. Preparar cuentas habilitadas y comprobar los perfiles aceptados por la API en el ensayo. La compatibilidad de tablas de acceso sigue dependiendo de la fase 0.
4. Auto-login y persistencia de sesión quedan como mejora posterior; para el mínimo se permite volver a iniciar sesión al reiniciar la app.

**Aceptación pendiente:** cada empleado ve su identidad y sus rutas; cambio de empleado y expiración funcionan en Android.

## 6. Fase 3 — Bandeja y secuencia de atención

**Estado: flujo principal implementado en código; modelos completos y validación pendientes.**

### Hecho en código

- `bandeja_rutas_pantalla.dart`: consulta de rutas del empleado, selección de ruta, inicio de una ruta pendiente y detalle de paradas con orden, titular, código, dirección, estado y coordenadas.
- Bandeja accesible desde la pantalla de mapa; se dejó de elegir automáticamente la primera ruta. Al abrir la atención se recupera el detalle actual del servidor.
- `secuencia_atencion.dart`: orden ascendente y selección de siguiente pendiente. La navegación ya no selecciona por proximidad ni reoptimiza el orden recibido.
- `Completado`, `Ejecutado`, `Observado` y `Omitido` se consideran atendidos para secuencia y progreso móvil.
- Estados de carga, error/reintento, sin rutas y ruta finalizada. Las consultas de rutas/detalle propagan errores en lugar de devolver listas vacías o `null`.

### Falta realizar / verificar

1. Introducir modelos tipados completos de ruta y punto; actualmente el flujo conserva mapas dinámicos y funciones compartidas de secuencia. El modelo de identidad sí existe.
2. Si se mantiene el requisito de bandeja como pantalla inicial, cambiar la entrada posterior al login: actualmente se accede a ella desde el mapa.
3. Ejecutar los tests escritos de orden/estados terminales y probar varias rutas reales, actualización de lista y retorno desde atención.
4. Comparar orden 1…N con SQL y web, incluso con GPS cerca de otra parada. Verificar que una observación avanza sin volver a seleccionarse.

**Aceptación pendiente:** la secuencia móvil coincide con la persistida y se distingue una ruta vacía/finalizada de un error de red.

## 7. Fase 4 — GPS, distancia y navegación externa

**Estado: seguimiento y controles implementados; navegación externa y validación Android pendientes.**

### Hecho en código

- Seguimiento REST con identidad real; conserva la hora de captura del dispositivo. No necesita cliente SignalR Flutter: el backend publica a la web.
- Captura GPS con validación de coordenadas, antigüedad inferior a diez segundos y precisión obtenida del dispositivo. Se eliminó la fabricación de una `Position` con coordenadas anteriores y timestamp nuevo.
- El centro inicial del mapa no se transmite como GPS. La navegación oculta el marcador del empleado hasta tener posición real o modo de ensayo explícito.
- Errores de GPS/permiso y acción de reintento; navegación muestra precisión y hora de la última captura.
- El ciclo de vida solicita detener transmisión fuera de primer plano y reanudarla con sesión activa al regresar.
- Simulación identificada como ENSAYO: sus posiciones no se transmiten y el cierre operativo queda bloqueado. Volver a la bandeja y abrir la ruta permite regresar a GPS real.

### Falta realizar / verificar

1. Agregar `url_launcher` y botón Navegar hacia una app compatible, con destino correcto y alternativa si no hay aplicación disponible.
2. Probar permisos iniciales, denegación permanente, GPS apagado, timeout y reintento; revisar mensajes y ausencia de envíos ante fallo.
3. Verificar ciclo de vida, cámara, pausa/reanudación y regreso de simulación a GPS real en Android.
4. Comprobar posición, precisión/hora y distancia visibles y la recepción de posiciones reales en el monitor web. Las posiciones simuladas del emulador deben identificarse como ensayo.

**Aceptación pendiente:** GPS real actualiza la posición web, Navegar abre el destino correcto y el ensayo en primer plano no exige ubicación permanente.

## 8. Fase 5 — Cierre, evidencia y tolerancia geográfica

**Estado: mejoras del formulario implementadas; validaciones del servidor y prueba integrada pendientes.** Se reutilizaron `formulario_cierre_orden_modal.dart` y `RutasTrabajoService`.

### Hecho en código móvil

- Cortado/Reconectado según ruta u Observado con motivo. Lectura numérica finita y no negativa cuando se ejecuta; notas editables sin precargar una declaración de trabajo realizado.
- De una a tres fotos de cámara, previsualización, repetición, eliminación y reducción de calidad/tamaño mediante `image_picker`. La galería dejó de ser una fuente de evidencia operativa.
- Al guardar, solicita GPS nuevo y valida radio de 30 m. Recomprueba antigüedad antes del envío tras preparar las fotos; presenta precisión real y errores de distancia.
- Mantiene el contrato JSON/Base64 existente.
- Bloqueo de doble envío y cambios/salida mientras guarda. Ante error mantiene formulario y fotografías en memoria.
- Antes de repetir un cierre fallido consulta el punto. Si ya está atendido, avanza sin repetir el PUT; si no puede verificarlo, no reenvía. Esta recuperación reduce duplicados, pero no ofrece idempotencia garantizada de servidor ni persistencia al cerrar la app.

### Falta realizar / verificar

1. **Backend:** exigir GPS y evidencia en todos los cierres, incluido Observado; limitar fotos y validar estados y lectura. Actualmente la comprobación de distancia es condicional a recibir coordenadas y las fotos son opcionales en servidor.
2. **Backend:** distinguir hora GPS/dispositivo de recepción UTC; el alias `/api/cortes/registrar` no aprovecha `FechaHoraUtc`. Revisar idempotencia si el ensayo demuestra duplicados no resueltos por la consulta previa.
3. **Pruebas móviles:** añadir pruebas del formulario, respuestas de red y recuperación de envíos inciertos. Ejecutar cámara real, 1/2/3 fotos, lectura inválida, GPS ausente/caducado y límites del radio.
4. **Integración:** confirmar que la lectura/evidencia se persisten, cambia el estado de conexión y se actualiza la web. Requiere corregir también el trigger y los mapeos de fase 0.

Payload de referencia para el endpoint PUT:

```json
{
  "latitudMovil": -16.40,
  "longitudMovil": -60.96,
  "lecturaMedidor": 123,
  "estadoFinal": "Cortado",
  "motivoObservacion": null,
  "observaciones": "Atención realizada",
  "fotos": ["data:image/jpeg;base64,..."]
}
```

Las coordenadas del ejemplo son ilustrativas: en ejecución deben proceder del GPS y compararse con el punto asignado.

**Aceptación:** fuera del radio o sin GPS/foto no se cierra el punto; dentro del radio se guarda lectura/evidencia, se actualiza el estado y se avanza sin repetir observados.

## 9. Web — Implementado y pendiente

**Estado: funcionalidades existentes en código; sin cambios web en el avance móvil y sin aceptación visual completa.**

### Hecho

- Acceso y panel de catastro con mapa, consulta de capas y búsqueda.
- `AsignarCortesView.razor` y `AsignarReconexionesView.razor`: selección de destinos/operario, partida, previsualización Dijkstra y creación/consulta de rutas mediante API.
- Dashboard y `MonitoreoGpsView.razor`: indicadores, seguimiento, hoja de ruta y lista de paradas ordenada.
- `RealtimeUpdates.razor` y `wwwroot/js/realtime.js`: suscripciones compartidas a posiciones, asignaciones y cambios de puntos/rutas, con gestión de reconexión. Dashboard solicita refrescar capas ante cambios de punto.
- Pruebas disponibles en `tests/Arquis.RoutingChecks` y `tests/realtime-checks.cjs`. Su ejecución documentada del 27/10 pasó; el test de suscripciones usa un doble de hub y no prueba la interfaz del navegador.

### Falta realizar / verificar

1. **API/SQL:** completar fase 0. La web depende de las mismas correcciones de acceso, capas, ficha de agua, coordenadas y cierre que Android.
2. **Asignación visual:** ensayar selección de clientes y empleado, partida desde primera parada o clic en calle, previsualización y guardado. Confirmar misma secuencia/geometría en SQL y Android; errores útiles ante puntos fuera de red y ausencia de asignaciones parciales.
3. **Datos comerciales:** etiquetar importes de ejemplo y estados sin verificar; no presentar deuda o pago acreditado sin una fuente real. Revisar mensajes de corte/reconexión y criterios de elegibilidad.
4. **Progreso:** revisar coherencia de atendidos frente a ejecutados/observados/omitidos. El monitor cuenta Completado/Ejecutado y muestra Observado por separado; no trata Omitido explícitamente. Definir y comprobar el significado de cada indicador frente a Android y servidor.
5. **Supervisión real:** desde Android ejecutar corte, reconexión y observación; comprobar marcador, cumplimiento, indicadores y capas sin recargar, con conteos contrastados en SQL.
6. **Errores/reconexión:** detener/reiniciar API y cortar/restaurar red; comprobar aviso de desconexión y refresco al reconectar sin duplicar suscripciones.
7. **Interfaz:** verificar visualmente login, selección de capas, búsqueda, selección geométrica, ficha y operaciones. Capturar evidencia; un HTTP 200 no certifica estas interacciones.

**Aceptación pendiente:** el administrador asigna y supervisa una atención real del APK usando el código del repositorio y la misma base, con estados y métricas consistentes.

## 10. Fase 6 — Pruebas, ensayo integrado y APK

### Hecho

- Se sustituyó el test Flutter de contador por pruebas de orden, avance tras Observado, estados terminales e identidad en `Movil/test/widget_test.dart`.
- Se añadieron pruebas de transporte de cookie, limpieza por 401 y bloqueo operativo de simulación en `Movil/test/auth_interceptor_test.dart`.
- Se documentaron configuración y ensayo en [Movil/PRUEBAS_OPERACION.md](Movil/PRUEBAS_OPERACION.md). Las pruebas móviles están escritas, **no ejecutadas**.

### Falta realizar

1. Preparar el toolchain y ejecutar desde `Movil/`:

   ```sh
   flutter pub get
   dart format lib test
   flutter analyze
   flutter test
   flutter build apk --release
   ```

   Corregir errores que detecten estas herramientas. La revisión estructural previa no garantiza compilación.
2. Añadir pruebas del formulario y errores de red; validar navegación de expiración además del interceptor. Ejecutar nuevamente las comprobaciones web/ruteo cuando se modifique el backend compartido:

   ```sh
   dotnet run --project tests/Arquis.RoutingChecks
   node tests/realtime-checks.cjs
   ```

3. Ejecutar el circuito: asignación web → bandeja → GPS → navegación externa → foto/lectura → cierre → persistencia SQL → actualización de indicadores y mapa web.
4. Incluir corte, reconexión y observación; GPS denegado, distancia superior a 30 m, falta de evidencia, expiración/cambio de empleado y pérdida temporal de red. No se exige cola offline completa.
5. Medir actualización en dispositivo y navegador. Los 63 ms del diagnóstico fueron un evento local aislado, no una garantía de latencia móvil ni prueba visual.
6. Instalar y probar el APK release final, además de debug. La configuración actual usa firma debug para release, aceptable para esta demostración; documentarlo y verificarlo en el teléfono evaluador.
7. Validar HTTP, cámara, mapas, permisos y GPS físicos. Preparar cuentas/roles, URL de API y pasos de arranque sin credenciales en Git. El emulador facilita el desarrollo, pero no sustituye la prueba de campo.

## 11. Prioridades y definición de terminado

| Prioridad | Trabajo restante | Resultado esperado |
|---|---|---|
| 1 | Compatibilidad API/SQL y validaciones obligatorias de cierre | Arranque y operación con el código del repositorio, sin parches temporales |
| 2 | Flutter/Android en Zorin, análisis, formato y ejecución de tests | Código móvil compilable y pruebas ejecutadas; emulador o teléfono conectado |
| 3 | Navegación externa, modelos tipados y ajustes detectados al ejecutar | Flujo móvil completo y errores comprensibles |
| 4 | Ensayo web y revisión de estados/importes/indicadores | Asignación y supervisión coherentes con SQL y móvil |
| 5 | Circuito integrado, APK release instalado y evidencia | Demostración reproducible en dispositivo y navegador |

Las tareas de cliente independientes pueden avanzar mientras se configura Android o se corrige la API. **Ninguna fase se marca como aceptada solo por existir archivos o pantallas.** Guardar fecha, entorno y resultado de cada criterio de aceptación.

La entrega mínima termina cuando administrador y empleados ejecutan el circuito sobre la misma base, sin coordenadas ficticias ni parches temporales, y el APK funciona en Android. OCR, JWT, persistencia offline avanzada, seguimiento en segundo plano e iOS quedan fuera hasta completar esa entrega.
