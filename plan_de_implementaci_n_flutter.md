# Plan para completar la aplicación Android de GeoIT Operaciones

Actualizado: 27 de octubre de 2026. Sustituye el roadmap inicial por un plan basado en el código existente y las pruebas con SQL Server en Docker Desktop.

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

El contenedor real es `arquis-sql-1`, del contexto Docker `desktop-linux`, con SQL Server publicado en `127.0.0.1:14330`. La base original `VisorDatosSIG` contiene:

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

### Funciones móviles existentes que se deben completar

| Área | Base existente | Brecha principal |
|---|---|---|
| Acceso | Login REST y cookie en memoria | Consumir identidad y resolver expiración; sin recuperación al reiniciar |
| Órdenes | Servicios de rutas y pantalla de mapa | Bandeja secuencial y selección por `orden`, no por proximidad |
| Ubicación | Geolocator, distancias y envío de posiciones | GPS fresco, errores explícitos y separación de simulación |
| Atención | Formulario, lectura, motivos y una foto Base64 | Hasta tres fotos, reintento y validación del cierre |
| Actualización web | REST móvil y emisión SignalR en backend | Verificar el resultado en Android real y en la web |

## 3. Fase 0 — Estabilizar la API contra la base real

**Prioridad obligatoria antes de desarrollar nuevas pantallas.** Los siguientes son bloqueos de compatibilidad, no un proyecto de seguridad.

1. Configurar la conexión Linux por variable `ConnectionStrings__DefaultConnection`: servidor `127.0.0.1,14330`, base `VisorDatosSIG` y credenciales locales. No guardar contraseñas en Git. La configuración actual apunta a LocalDB/instancia Windows.
2. Resolver la inicialización de una base importada por scripts: evitar ejecutar `InitialCreate` sobre tablas existentes. Definir y probar una estrategia explícita para bases SQL existentes y bases nuevas; no insertar historiales de migración a ciegas.
3. Alinear EF con las tablas reales `UsuarioMenu`, `BitacoraAcceso` y revisar `BitacoraMigracion`. Probar los inicializadores sin duplicar ni perder roles al reiniciar.
4. Declarar `HasColumnType("geometry")` en las geometrías de vías, códigos, lotes y manzanas. Las pruebas detectaron GeoJSON con ejes invertidos al usar el mapeo predeterminado `geography`.
5. Preparar un script revisable para corregir `CodigosFijos.Latitud` desde `Geom.STY` y `Longitud` desde `Geom.STX`, exclusivamente para geometrías Point válidas. Respaldar antes y comprobar límites de San Ignacio; no intercambiar valores por suposición. Evitar que importaciones posteriores reproduzcan la inconsistencia.
6. Ajustar EF para guardar `CodigosFijos` con triggers, por ejemplo deshabilitando la cláusula SQL OUTPUT en el mapeo de esa tabla. Sin esto el cierre de cortes falla con SQL 334. Declarar precisión de lecturas/importes.
7. Corregir consultas de agua que usan `.Lat`, `.Long` o variables `geography` sobre `geometry`. Revisar las distancias: SRID 4326 en geometry no implica metros.
8. Aclarar elegibilidad de cortes/reconexiones con los estados disponibles. No asumir deuda real: la API contiene importes constantes de ejemplo y el catastro no acredita estados comerciales verificados. Para el ensayo, usar selección explícita del administrador y etiquetar cualquier supuesto.

**Aceptación:** arrancar el código del repositorio sin parches temporales sobre una copia de la base; login, capas con coordenadas correctas, ficha y asignaciones responden; reiniciar sin errores. Corte cambia Estado a 3 y reconexión a 1, conservando datos y actualizando el dashboard.

## 4. Fase 1 — Preparar Android y conectividad

Android Studio no es obligatorio: preparar Flutter SDK, herramientas Android de línea de comandos, platform-tools/adb, herramientas de compilación y, si se usará emulador, Android Emulator e imagen x86_64. Comprobar virtualización/KVM en el equipo anfitrión; `/dev/kvm` no era visible desde esta sesión. Alternativa: teléfono Android por USB.

1. Ejecutar `flutter doctor -v` y resolver el toolchain Android. Elegir Flutter compatible con Dart `^3.11.0`, declarado por el proyecto.
2. Crear `Movil/.env`: falta actualmente, pero `main.dart` lo carga obligatoriamente y `pubspec.yaml` lo incluye como asset.
3. Configurar la dirección de la API, no la de SQL Server:

   ```dotenv
   API_URL_LOCAL=http://localhost:5080/api
   API_URL_ANDROID=http://10.0.2.2:5080/api
   ```

   Para un teléfono por Wi-Fi, sustituir `10.0.2.2` por la IP LAN de Zorin. Por USB puede usarse `adb reverse tcp:5080 tcp:5080` y `http://127.0.0.1:5080/api`.
4. Comprobar acceso a `/health` desde Android. Revisar permiso de Internet y política de tráfico HTTP para esta demostración local; el manifiesto principal no declara una excepción de tráfico en claro.
5. Ejecutar `flutter pub get`, `flutter analyze` y `flutter run`. Revisar especialmente plugins nativos no esenciales como voz/LLM si bloquean Android; no ampliar el alcance para utilizarlos.

**Aceptación:** aplicación arrancando en Android, sin error por `.env`, y API accesible desde el dispositivo elegido.

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

1. Conservar y mostrar usuario, nombre y rol devueltos por login. Usar el login real para consultar asignaciones y transmitir posiciones; eliminar identidades de respaldo como `Pedro` u `Operario` en el flujo normal.
2. Gestionar 401 con regreso al login y detención del tracking; limpiar estado al salir.
3. Para el mínimo aceptable se permite volver a iniciar sesión tras cerrar la app. Persistencia y auto-login son mejoras posteriores, no bloqueos.
4. No presentar el registro público como creación de un empleado habilitado. Utilizar cuentas con rol previamente asignado por el administrador y comprobar esos perfiles en el ensayo.

**Aceptación:** cada empleado ve su nombre y sus propias rutas; se puede salir y entrar con otro empleado sin conservar datos del anterior.

## 6. Fase 3 — Bandeja y secuencia de atención

1. Añadir una bandeja inicial de rutas/órdenes con número de parada, cliente, código fijo, dirección, estado y coordenadas. Mantener el mapa como vista complementaria.
2. Introducir modelos Dart para ruta y punto, respetando `id`, `orden`, `estado` y los nombres reales de la API.
3. Ordenar siempre por `orden` ascendente. Sustituir `_seleccionarObjetivoMasCercano()` por la siguiente parada pendiente de esa secuencia: Dijkstra decide en web, el móvil no reoptimiza.
4. Tratar `Completado`, `Ejecutado`, `Observado` y `Omitido` como atendidos cuando corresponda, de forma consistente con el servidor. Hoy Observado puede seleccionarse nuevamente como objetivo.
5. Mostrar carga, error con reintento, ausencia de rutas y ruta terminada como estados distintos. Los servicios no deben convertir cualquier error de red en una lista vacía.

**Aceptación:** la secuencia 1…N coincide con la guardada en SQL y no cambia por la posición del GPS. Una observación permite avanzar a la siguiente parada.

## 7. Fase 4 — GPS, distancia y navegación externa

1. Mantener el seguimiento en primer plano y los envíos REST actuales. No hace falta incorporar un cliente SignalR en Flutter: el backend ya publica los cambios a la web.
2. Solicitar permisos y mostrar precisión, hora de la última captura, posición y distancia al objetivo. GPS apagado/denegado debe producir un mensaje y una acción de reintento.
3. No reutilizar coordenadas anteriores inventando un timestamp nuevo. No transmitir posiciones iniciales fijas como si fueran lecturas del dispositivo.
4. Agregar `url_launcher` y un botón Navegar hacia Google Maps u otra aplicación disponible. Incluir alternativa comprensible si no existe una app compatible.
5. Separar claramente el modo de ensayo. Un GPS simulado debe estar identificado y no activar silenciosamente el registro operativo real. No modificar la app para aparentar presencia física.

**Aceptación:** GPS real actualiza el objetivo y la posición visible en web; Navegar abre el destino correcto. La aplicación funciona sin exigir permisos de ubicación permanente para el ensayo en primer plano.

## 8. Fase 5 — Cierre, evidencia y tolerancia geográfica

Reutilizar `formulario_cierre_orden_modal.dart` y `RutasTrabajoService`; no reconstruir el formulario.

1. Mantener Cortado/Reconectado según tipo de ruta, u Observado con motivo; validar lectura numérica y notas.
2. Ampliar de una foto a **1–3 fotografías**, con cámara, previsualización, repetición y compresión. La evidencia de atención debe proceder de la cámara; identificar la galería como recurso de ensayo si se conserva.
3. Al guardar, solicitar una ubicación nueva, con antigüedad inferior a diez segundos, y comprobar los 30 m. Mostrar distancia y error cuando no se pueda validar. La precisión debe presentarse, no inventarse.
4. Mantener JSON/Base64, que ya consume el backend. No migrar a multipart ni a otra ruta sin necesidad.
5. En backend, hacer obligatorios GPS y evidencia también para Observado; limitar las fotos y validar estados. Esta es consistencia funcional del formulario, sin añadir un proyecto de seguridad. Distinguir hora GPS/dispositivo de la recepción UTC del servidor; actualmente el alias `/api/cortes/registrar` no aprovecha `FechaHoraUtc`.
6. Bloquear doble pulsación y conservar formulario/fotos si falla la red. Antes de repetir un envío de resultado incierto, consultar el punto para evitar duplicados.

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

## 9. Fase 6 — Ensayo integrado y APK

1. Sustituir el test de contador de `Movil/test/widget_test.dart`. Probar orden secuencial, estados terminales, formulario, manejo de 401 y errores de red.
2. Ejecutar en Android: asignación web → bandeja → GPS → navegación → foto/lectura → cierre → persistencia SQL → actualización de indicadores y mapa web.
3. Incluir un corte, una reconexión y una observación; probar GPS denegado, distancia superior a 30 m, falta de evidencia y corte temporal de red. Una cola offline completa no es necesaria.
4. Medir la actualización observada en dispositivo y navegador. Los 63 ms medidos fueron un evento local aislado, no una garantía de latencia móvil ni prueba de interfaz.
5. Ejecutar `flutter analyze`, `flutter test` y `flutter build apk --release`. La firma actual utiliza claves debug; es suficiente para un APK de demostración instalable, pero debe documentarse y probarse en el teléfono evaluador.
6. Instalar el APK final, no solo ejecutar debug. Verificar conexión HTTP, permisos, cámara, mapas y conectividad con Zorin. Preparar cuentas/roles, red y pasos de arranque sin credenciales en el repositorio.

## 10. Orden de ejecución y definición de terminado

**Compatibilidad API/SQL → Android y conectividad → identidad → bandeja/secuencia → GPS/navegación → cierre → ensayo/APK.**

No marcar una fase completa solo por tener archivos o pantallas. Guardar evidencia de su criterio de aceptación. La entrega mínima termina cuando administrador y empleados ejecutan el flujo anterior usando la misma base, sin coordenadas ficticias ni parches temporales, y el APK funciona en Android. OCR, JWT, persistencia offline avanzada, segundo plano e iOS se retoman únicamente después de esa entrega.
