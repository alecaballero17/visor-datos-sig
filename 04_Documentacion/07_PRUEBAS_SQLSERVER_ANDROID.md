# Pruebas con SQL Server y prerrequisitos de Android

Fecha: 27/10/2026. Alcance: revisar la integración disponible y fundamentar el roadmap Android. No se modificó el código de la aplicación móvil ni se corrigieron permanentemente los defectos encontrados.

## Entorno y aislamiento

- Docker Desktop, contexto `desktop-linux`, contenedor `arquis-sql-1`.
- SQL Server: puerto anfitrión `127.0.0.1:14330`; base original `VisorDatosSIG`.
- .NET SDK Linux 10.0.113. API en 5080 y frontend en 5180 durante las pruebas.
- Se creó un backup COPY_ONLY y se restauró como `VisorDatosSIG_Pruebas_20261027`. Las asignaciones, posiciones, cambios de estado y correcciones diagnósticas de coordenadas se hicieron en esa copia.
- Credencial SQL tomada del entorno del contenedor, sin escribirla en el repositorio ni mostrarla en los resultados.

**Distinción esencial:** el código del repositorio no pudo arrancar directamente sobre la base importada. Para continuar se copió el backend a `/tmp/arquis-api-check` y se aplicaron adaptaciones exclusivamente diagnósticas. Sus resultados no acreditan que esos defectos estén corregidos en el repositorio.

## Inventario contrastado directamente en SQL

| Dato | Resultado |
|---|---:|
| Códigos fijos | 6.271 |
| Lotes | 15.281 |
| Manzanas | 863 |
| Vías | 578 |
| Geometrías viales | 576 LineString y 2 MultiLineString |
| SRID vial | 4326 |
| Conexiones en Estado=1 | 6.271 |
| Estados sin verificar | 6.271 |
| Coordenadas inconsistentes con geometría Point, tolerancia 0,00001° | 6.265 |

Las geometrías son de tipo SQL `geometry`. En un ejemplo, `Latitud` y `Longitud` contenían ambos aproximadamente -60,96, mientras `Geom.STY` indicaba aproximadamente -16,39. Los límites geométricos del catastro son latitud -16,4407…-16,3530 y longitud -61,0039…-60,9287.

La base de pruebas no contenía rutas ni posiciones antes de los ensayos. La comprobación final mantuvo en la base original los 6.271 códigos en Estado=1 y las mismas 6.265 inconsistencias: no se aplicó allí la corrección de coordenadas.

## Bloqueos encontrados sin adaptación permanente

| Área | Resultado observado | Consecuencia |
|---|---|---|
| Arranque normal | SQL 2714: `Manzanas` ya existe al ejecutar `InitialCreate` | La API no inicia sobre la base importada |
| Inicialización de menús | SQL 208: EF consulta `UsuarioMenus`, pero existe `UsuarioMenu` | Segundo bloqueo al omitir solo la migración |
| Login | SQL 208 al insertar en `BitacoraAccesos`; la tabla real es `BitacoraAcceso` | HTTP 500; fallo funcional de mapeo, no de contraseña |
| Espacial | EF sin tipo geometry explícito entrega ejes invertidos en GeoJSON | HTTP 200 no basta para validar capas; ruteo con posiciones reales falla |
| Coordenadas de conexiones | 6.265 columnas no coinciden con su Point | Las asignaciones no representan correctamente sus destinos |
| Ficha de agua | SQL 6592: `.Long`/`.Lat` no existen en SqlGeometry | HTTP 500; revisar también distancias y variables geography |
| Ejecución de corte | SQL 334: OUTPUT incompatible con trigger de `CodigosFijos` | La transacción de cierre falla con HTTP 500 |
| Observación sin coordenadas ni fotos | HTTP 200, punto guardado Observado | La obligatoriedad del cierre solo existe parcialmente en cliente |

## Adaptaciones temporales para aislar causas

Se aplicaron por etapas, únicamente en la API temporal y/o la base de pruebas:

1. Omitir `Database.Migrate()` para no recrear el esquema SQL importado.
2. Omitir `MenuSeeder` para evitar el mapeo de menús incompatible.
3. Mapear `BitacoraAcceso` al nombre real de tabla.
4. Mapear `Geom` como `geometry` en vías, códigos, lotes y manzanas.
5. Corregir las 6.265 coordenadas escalares desde STY/STX en la copia.
6. Desactivar SQL OUTPUT en el mapeo de `CodigosFijos` para respetar el trigger existente.

No se aplicó un parche temporal a la ficha de agua: su fallo permanece registrado.

## Resultados HTTP y de persistencia

Todos los siguientes ensayos de API requirieron superar primero los bloqueos de arranque en la copia temporal.

| Prueba | Resultado |
|---|---|
| `/health` | 200 |
| Dashboard | 200; conteos coincidentes con SQL, 100% Estado=1 y 6.271 sin verificar; sin cuadrillas ficticias cuando no existen rutas |
| Cuatro capas GeoJSON | 200; inicialmente ejes invertidos, corregidos solo tras ajustar el mapeo temporal |
| Login de administrador y consulta de sesión | Inicialmente 500/401; 200 tras corregir el mapeo de bitácora temporal |
| Logout y consulta posterior de sesión | 200 y 401, respectivamente |
| Búsqueda de códigos fijos | 200 |
| Empleados, rutas asignadas y detalle | 200 |
| Dijkstra con tres destinos reales | Inicialmente 400; 200 tras alinear coordenadas y mapeo espacial; recorrido de 6.060,4 m |
| Dijkstra con partida fuera del área | 400 esperado, sin inventar una diagonal |
| Crear ticket y recuperar asignación por empleado | 200; puntos persistidos con secuencia |
| Iniciar ruta | 200; estado EnProgreso |
| Ejecutar a más de 30 m | 400 esperado |
| Ejecutar corte dentro del radio | Primero 500 por trigger; 200 tras adaptación temporal de OUTPUT |
| Lectura y evidencia | SQL confirmó lectura 123,00, distancia 0 m y evidencia en el punto atendido |
| Registrar Observado sin GPS/foto | 200 inesperado; SQL confirmó ausencia de ambos |
| Reconexión | 200 tras adaptación del trigger; SQL confirmó Estado=1 de la conexión |
| Estado final de rutas | Corte y reconexión Completadas; corte incluye una atención y una observación |
| Posición GPS por REST, activos e historial | 200; SQL confirmó una posición de prueba |
| Frontend `/login`, `/dashboard`, `/js/realtime.js` | HTTP 200; sin validación visual/interactiva |
| Ficha de agua | 500 incluso después de los demás ajustes temporales |

Las rutas se identificaron como `PRUEBA-20261027-CORTE` y `PRUEBA-20261027-RECONEXION`; la posición usa `PRUEBA-20261027`. La evidencia del cierre fue una imagen mínima de ensayo, no una captura de cámara. Android y su cámara no participaron.

## SignalR real y pruebas automatizadas

Se abrió una conexión WebSocket real mediante negociación y handshake SignalR contra la API. Se recibieron:

- `ReceiveRutaAsignada` al crear la orden.
- `ReceiveRutaActualizada` al iniciarla.
- `ReceivePuntoActualizado` al guardar la observación.
- `ReceivePosicion` al registrar telemetría.

Una notificación de posición llegó unos **63 ms** después de iniciar el POST, en un único ensayo local. Esto demuestra el evento del servidor, no una garantía de LTE/5G, una medición del APK ni la actualización visual del navegador.

También pasaron:

```bash
dotnet run --project tests/Arquis.RoutingChecks --no-restore
node tests/realtime-checks.cjs
```

El primer comando ejecutó diez comprobaciones del grafo real: red vacía, esquina vial, distancia, bidireccionalidad, acceso proyectado, desconexión, fuera de área, coordenadas no finitas, cruces geométricos y parada repetida. El segundo comprobó suscripciones compartidas, filtrado, reconexión y liberación con un doble de hub.

## Límites y conservación de resultados

- No había Flutter/SDK Android disponibles en PATH. Falta ejecutar y evaluar la aplicación en Android.
- No había navegador automatizable disponible; no se certificaron gráficos, interacción 3D ni FPS.
- El flujo original sigue bloqueado por compatibilidad de esquema, geometrías y trigger; primero debe corregirse de forma revisable y repetirse sin adaptaciones temporales.
- Dijkstra utiliza red bidireccional y ordenamiento heurístico entre paradas; los datos no contienen sentidos ni giros. No se afirma optimalidad global.
- No se requiere JWT ni endurecimiento avanzado para resolver estos fallos funcionales.
- Se conserva la copia SQL y el backup de diagnóstico en el contenedor. El backup está en `/var/opt/mssql/data/arquis_pruebas_20261027.bak`. No se eliminaron bases ni datos originales.
- Los servidores temporales utilizados para el diagnóstico se detuvieron al terminar; no deben utilizarse como arranque habitual.

El orden de trabajo y los criterios de entrega se encuentran en [el plan Android](../plan_de_implementaci_n_flutter.md).
