# Plan de Pruebas Integradas E2E: Web y Móvil con Contenedor SQL Server y Agentes CLI

Este documento establece la guía técnica, los prerrequisitos, los casos de prueba y el procedimiento de ejecución automatizado para validar el sistema **GeoIT Operaciones (Arquis)** de extremo a extremo, empleando una base de datos SQL Server en contenedor Docker, la API REST en .NET 10, el Visor Web y la aplicación móvil en Flutter conducida mediante emuladores *headless* y agentes de consola (CLI).

---

## 1. Alcance y Arquitectura del Entorno de Pruebas

El objetivo es validar el ciclo de vida completo de una orden de trabajo (Planificación Web ➔ Despacho ➔ Recepción Móvil ➔ Navegación ➔ Validación Antifraude de Campo ➔ Cierre y Persistencia SQL ➔ Actualización en Tiempo Real Web) sin requerir intervención manual ni dispositivos físicos.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AGENTE / RUNNER CLI                             │
└──────┬──────────────────┬──────────────────────┬───────────────────────┘
       │                  │                      │
       ▼                  ▼                      ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────────────────────────┐
│  SQL SERVER  │   │   BACKEND    │   │      EMULADOR ANDROID (CLI)      │
│  (Docker)    │◄──┤  (.NET 10)   │◄──┤  - Sin ventana (-no-window)      │
│  Puerto      │   │  Puerto 5080 │   │  - Control GPS: adb emu geo fix  │
│  14330       │   │              │   │  - Pruebas: flutter test         │
└──────────────┘   └──────┬───────┘   └──────────────────────────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │  VISOR WEB   │
                   │  (Blazor UI) │
                   │  Puerto 5180 │
                   └──────────────┘
```

---

## 2. Prerrequisitos de Infraestructura y Entorno

### 2.1. Base de Datos en Contenedor Docker
* **Docker Desktop** activo en el contexto `default`.
* Contenedor `arquis-sql-1` (imagen `mcr.microsoft.com/mssql/server:2022-latest`) con el volumen persistente `arquis_sql-data`.
* **Datos Catastrales Existentes en `VisorDatosSIG`:**
  * 6.271 Códigos Fijos de agua potable.
  * 15.281 Lotes catastrales.
  * 863 Manzanas (`dbo.Manzanas`).
  * 578 Ejes viales (`dbo.Vias`, EPSG:4326).
  * Cuentas habilitadas: `admin` (Administrador), `Pedro` (Cortador), `Juan` (Lecturador).

### 2.2. Entorno .NET y Node.js
* .NET SDK 10.0 (según `global.json`).
* Node.js v18+ (para ejecución de pruebas de sockets/SignalR).
* Paquete de herramientas de compilación C# restaurado (`nuget.config` en la raíz).

### 2.3. Herramientas Android CLI (Sin Android Studio obligatorio)
* **Android SDK Command-Line Tools** (`cmdline-tools;latest`).
* Paquetes mínimos instalados vía `sdkmanager`:
  * `platform-tools` (`adb`).
  * `platforms;android-34`.
  * `system-images;android-34;google_apis;x86_64`.
  * `emulator`.
* Dispositivo virtual creado:
  ```powershell
  avdmanager create avd -n EmuladorPruebas -k "system-images;android-34;google_apis;x86_64" --device "pixel"
  ```
* Flutter SDK 3.44+ / Dart 3.12+ configurado con la ruta del SDK:
  ```powershell
  flutter config --android-sdk <Ruta_Android_SDK>
  ```

### 2.4. Adecuaciones Previas en el Código (Fase 0)
Antes de ejecutar los ensayos, el repositorio debe contar con:
1. Cadena de conexión a `Server=127.0.0.1,14330;Database=VisorDatosSIG;User Id=sa;Password=Arquis1!a44b953454c6414f965152cf5865876c;TrustServerCertificate=True;`.
2. Mapeo en singular en EF Core para `BitacoraAcceso` y `UsuarioMenu`.
3. Desactivación de cláusula OUTPUT en `CodigosFijos` (`UseSqlOutputClause(false)`).
4. `HasColumnType("geometry")` en entidades espaciales (`Via`, `CodigoFijo`, `Lote`, `Manzana`).
5. Corrección de `AguaPotableController.cs` (`.STX`/`.STY` y variables `geometry`).
6. Sincronización de coordenadas escalares ejecutada en la base:
   ```sql
   UPDATE dbo.CodigosFijos
   SET Latitud = Geom.STY, Longitud = Geom.STX
   WHERE Geom IS NOT NULL AND Geom.STGeometryType() = 'Point';
   ```

---

## 3. Matriz de Pruebas Integradas

### 3.1. Pruebas de la Plataforma Web y API

| ID | Módulo / Requisito | Acción de Prueba | Resultado Esperado | Validación Automatizada |
| :--- | :--- | :--- | :--- | :--- |
| **PW-01** | Autenticación (`RF-WEB-01`) | `POST /api/autenticacion/iniciar` con credenciales de `admin`. | HTTP 200, cookie `Arquis.Auth` emitida y registro insertado en `dbo.BitacoraAcceso`. | Consulta SQL a `BitacoraAcceso` donde `Login='admin'` y `Exitoso=1`. |
| **PW-02** | Dashboard y Capas (`RF-WEB-02`, `03`) | `GET /api/dashboard/kpis` y `GET /api/layers/codigos-fijos`. | Conteos coinciden con SQL (6.271 conexiones). GeoJSON devuelve coordenadas válidas `[Long, Lat]` sin inversión de ejes. | Script HTTP comprueba estructura de GeoJSON y propiedades `features[0].geometry.coordinates`. |
| **PW-03** | Dijkstra Vial (`RF-WEB-05`) | `POST /api/rutas-trabajo/optimizar-preview` con punto de partida en calle y 3 códigos fijos. | Trayectoria sobre `dbo.Vias`, sin cruces diagonales, distancia positiva y orden secuencial (1, 2, 3). | Test de grafo en `Arquis.RoutingChecks` pasando 10/10. |
| **PW-04** | Creación y Despacho (`RF-WEB-04`) | `POST /api/rutas-trabajo/asignacion-masiva` asignando a operario `Pedro`. | HTTP 200, ruta creada en `dbo.RutasTrabajo` (estado `Pendiente`) y emisión de evento SignalR `ReceiveRutaAsignada`. | Aserción SignalR y consulta a `dbo.RutasTrabajo`. |
| **PW-05** | Telemetría en Vivo (`RF-WEB-06`) | `POST /api/tracking/posicion` con coordenadas del operario. | Posición persistida en `dbo.TrackingPosiciones` y retransmitida en tiempo real por el Hub `/hubs/tracking`. | Aserción SignalR en `realtime-checks.cjs`. |

---

### 3.2. Pruebas de la Aplicación Móvil (Headless / Emulador)

| ID | Módulo / Requisito | Acción de Prueba | Resultado Esperado | Validación Automatizada |
| :--- | :--- | :--- | :--- | :--- |
| **PM-01** | Sesión de Operario (`RF-MOB-01`) | Iniciar sesión desde el cliente móvil como `Pedro`. | Cookie en memoria, perfil cargado (`Cortador`), acceso a bandeja. | Test unitario en `auth_interceptor_test.dart` y prueba de widget. |
| **PM-02** | Bandeja de Trabajo (`RF-MOB-02`) | Carga de rutas asignadas y apertura de orden. | Secuencia 1..N estrictamente respetada. No reordena por proximidad arbitraria. | Test en `rutas_navegacion_test.dart`. |
| **PM-03** | Navegación Externa (`RF-MOB-03`) | Selección de acción "Navegar" en parada pendiente. | `NavegacionExternaService` genera URI con coordenadas exactas (`google.navigation:q=` / Waze) y fallback web. | Aserción en `rutas_navegacion_test.dart`. |
| **PM-04** | **Antifraude: Rechazo por Distancia** (`RN-01`, `RF-MOB-05`) | Simular GPS a **50 metros** del predio (`adb emu geo fix`) e intentar registrar corte. | El cliente o la API rechazan la solicitud con error `RN-01 Antifraude: distancia excede 30 m`. La orden no cambia de estado. | HTTP 400 devuelto por la API / Bloqueo en modal del cliente. |
| **PM-05** | **Antifraude: Aceptación Válida** (`RN-01`, `RF-MOB-05`) | Simular GPS a **10 metros** del predio (`adb emu geo fix`). | El indicador antifraude se coloca en verde ($\le 30\text{ m}$). Se habilita el guardado. | Formulario permite envío del payload con coordenadas reales recientes (< 10 s). |
| **PM-06** | Registro de Evidencia (`RF-MOB-04`) | Adjuntar foto de evidencia (simulada o archivo local) + lectura de medidor `145.2`. | Payload empaquetado con array de fotos Base64 y lectura numérica. | PUT `/api/rutas-trabajo/{id}/puntos/{pId}/ejecutar` exitoso. |
| **PM-07** | **Persistencia e Impacto Catastral** | Comprobación en base de datos tras el cierre del punto. | En `dbo.CodigosFijos`: `Estado` cambia a `3` (Cortado) y `FechaCambioEstado` se actualiza. La ruta pasa a `Completada` si todos sus puntos fueron atendidos. | Consulta SQL directa con `sqlcmd`: `Estado = 3`. |

---

## 4. Procedimiento de Ejecución Paso a Paso desde CLI

Este procedimiento está diseñado para ser ejecutado por un desarrollador o por un **Agente de IA Autónomo** en una única sesión de PowerShell.

### Paso 1: Iniciar y preparar el contenedor SQL Server
```powershell
# 1. Asegurar contexto y levantar contenedor
docker context use default
docker start arquis-sql-1

# 2. Esperar disponibilidad del puerto SQL
do {
    Start-Sleep -Seconds 2
    $tcp = Test-NetConnection -ComputerName 127.0.0.1 -Port 14330 -WarningAction SilentlyContinue
} until ($tcp.TcpTestSucceeded)

Write-Host "Contenedor SQL Server listo en el puerto 14330."
```

### Paso 2: Sincronizar coordenadas en la base de datos
```powershell
docker exec arquis-sql-1 /opt/mssql-tools18/bin/sqlcmd `
  -S localhost -U sa -P "Arquis1!a44b953454c6414f965152cf5865876c" -C `
  -d VisorDatosSIG `
  -Q "UPDATE dbo.CodigosFijos SET Latitud=Geom.STY, Longitud=Geom.STX WHERE Geom IS NOT NULL AND Geom.STGeometryType()='Point';"
```

### Paso 3: Iniciar la API Backend en segundo plano
```powershell
$backendJob = Start-Job -ScriptBlock {
    Set-Location "D:\Demos\2026-2-SIG\visor-datos-sig"
    dotnet run --project src/Arquis.Backend --no-restore
}

# Esperar a que responda el endpoint de salud
do {
    Start-Sleep -Seconds 2
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:5080/health" -Method Get -ErrorAction Stop
    } catch {
        $health = $null
    }
} until ($health -and $health.status -eq "ok")

Write-Host "API Backend iniciada en http://localhost:5080."
```

### Paso 4: Ejecutar pruebas de regresión vial y tiempo real
```powershell
# Validación de las 10 reglas del grafo vial Dijkstra
dotnet run --project tests/Arquis.RoutingChecks --configuration Release

# Validación de suscripciones y desconexión SignalR
node tests/realtime-checks.cjs
```

### Paso 5: Preparar y arrancar el Emulador Android Headless
```powershell
# Iniciar emulador en segundo plano sin ventana gráfica
$emulatorProc = Start-Process -FilePath "emulator" `
  -ArgumentList "-avd EmuladorPruebas -no-window -no-audio -no-boot-anim -gpu swiftshader_indirect" `
  -PassThru

# Esperar a que adb reconozca el dispositivo completamente booteado
adb wait-for-device
do {
    Start-Sleep -Seconds 3
    $boot = adb shell getprop sys.boot_completed
} until ($boot.Trim() -eq "1")

# Mapear el puerto de la API hacia el emulador
adb reverse tcp:5080 tcp:5080
Write-Host "Emulador Android listo y conectado a la API por reverse proxy."
```

### Paso 6: Simulación de Condiciones de Campo desde CLI

#### 6.1. Simular rechazo antifraude (distancia > 30 m):
```powershell
# Inyectar coordenadas deliberadamente lejanas al Código Fijo #1
adb emu geo fix -60.9650 -16.3950
```

#### 6.2. Simular aprobación antifraude (distancia < 30 m):
```powershell
# Inyectar coordenadas reales del Código Fijo #1 (STY: -16.389389, STX: -60.960764)
adb emu geo fix -60.960764 -16.389389
```

#### 6.3. Inyectar imagen de evidencia en la galería virtual:
```powershell
adb push tests/assets/evidencia_corte_demo.jpg /sdcard/DCIM/Camera/
```

### Paso 7: Ejecución de las Pruebas de la Aplicación Móvil
```powershell
Set-Location "D:\Demos\2026-2-SIG\visor-datos-sig\Movil"

# 1. Pruebas unitarias de modelos, interceptores y secuencias (18 pruebas)
flutter test --no-pub

# 2. Pruebas de integración E2E en el emulador headless
flutter test integration_test/flujo_operativo_test.dart `
  -d emulator-5554 `
  --dart-define=API_URL_ANDROID=http://127.0.0.1:5080/api
```

### Paso 8: Verificación Cruzada en Base de Datos
El agente o evaluador ejecuta una consulta para verificar el efecto del corte en SQL Server:
```powershell
docker exec arquis-sql-1 /opt/mssql-tools18/bin/sqlcmd `
  -S localhost -U sa -P "Arquis1!a44b953454c6414f965152cf5865876c" -C `
  -d VisorDatosSIG `
  -Q "SELECT c.IdCodigo, c.CodFijo, c.Estado, p.EstadoFinal, p.LecturaMedidor, p.DistanciaAntifraudeMetros FROM dbo.CodigosFijos c JOIN dbo.PuntosRutaTrabajo p ON p.IdCodigoFijo=c.IdCodigo WHERE c.IdCodigo=1;"
```
* **Criterio de éxito:** `Estado = 3` (Cortado), `EstadoFinal = 'Cortado'`, `DistanciaAntifraudeMetros <= 30.0` y `LecturaMedidor > 0`.

### Paso 9: Limpieza y Detención de Procesos
```powershell
# Detener emulador
adb emu kill

# Detener backend y contenedor
Stop-Job $backendJob
docker stop arquis-sql-1
Write-Host "Ciclo de pruebas completado y entorno liberado."
```

---

## 5. Criterios de Aceptación Definitivos (Definición de Terminado)

Para dar por aceptada la solución integrada sin parches temporales:
1. **Zero Parches:** La API corre directamente sobre el contenedor `arquis-sql-1` sin modificar la base original de forma destructiva ni omitir tablas en tiempo de ejecución.
2. **Consistencia Topológica:** Las rutas generadas siguen las calles de `dbo.Vias` y no intersectan manzanas catastrales.
3. **Regla Antifraude Inviolable:** No existe ningún camino (ni por app móvil ni por consumo directo del endpoint REST) donde se pueda registrar un corte/reconexión sin coordenadas GPS válidas dentro del radio de 30 metros y con al menos una evidencia fotográfica registrada.
4. **Sincronización Multicanal:** El cierre registrado en el emulador móvil se refleja en menos de 3 segundos en el visor web y dashboard mediante SignalR sin requerir recargar la página.
