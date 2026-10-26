# Roadmap de Implementación en Flutter (App Móvil) con Agente IA
## Sistema Móvil de Operaciones en Campo (GeoIT Operaciones)

Este documento define la estrategia secuencial, incremental y modular para guiar a un **Agente IA de Programación** (ej. Claude Code, Cursor, GitHub Copilot Workspace, Roo Code) en la construcción de la aplicación móvil en Flutter, conectada al backend existente.

---

### Enfoque de Implementación y Reglas de Trabajo con el Agente IA

1. **Principio de Aislamiento:** Cada paso debe implementarse, compilarse y validarse de forma independiente antes de pasar al siguiente.
2. **Arquitectura Recomendada:** *Clean Architecture* o arquitectura por capas (Data, Domain, Presentation) utilizando **Bloc/Cubit** o **Riverpod** como gestor de estado.
3. **Manejo de Contexto del Agente:** Proporcionar al agente el esquema de datos y contratos REST/JSON correspondientes antes de cada fase para evitar alucinaciones en modelos de datos.

---

### Cronograma Secuencial de Requerimientos Funcionales (Fases 1 a 6)

```
[ Fase 0: Setup ] 
       │
       ▼
[ Fase 1: RF-MOB-01 (Auth & Sesión) ]
       │
       ▼
[ Fase 2: RF-MOB-02 (Bandeja & Lista Optimizada) ]
       │
       ▼
[ Fase 3: RF-MOB-03 (Geolocalización & Navegación Turn-by-Turn) ]
       │
       ▼
[ Fase 4: RF-MOB-04 & RF-MOB-05 (Formulario de Cierre & Auditoría Antifraude) ]
       │
       ▼
[ Fase 5: RF-MOB-06 (OCR Medidor - Opcional/Avanzado) ]
       │
       ▼
[ Fase 6: Pruebas de Integración y Empaquetado ]
```

---

## Fase 0: Setup del Entorno y Dependencias Base

**Objetivo:** Configurar el proyecto Flutter base con las librerías necesarias y el árbol de carpetas limpio.

### Dependencias Principales en `pubspec.yaml`
- **Networking y Estado:** `dio` / `http`, `flutter_bloc` (o `flutter_riverpod`).
- **Geolocalización y Mapas:** `geolocator`, `latlong2`, `url_launcher`.
- **Cámara y Multimedia:** `camera` / `image_picker`.
- **Almacenamiento Local:** `flutter_secure_storage` (tokens), `shared_preferences`.
- **OCR (Opcional):** `google_mlkit_text_recognition`.

### Prompt inicial para el Agente IA:
> *"Configura la estructura de carpetas siguiendo Clean Architecture (`core`, `data`, `domain`, `presentation`). Agrega las dependencias clave en `pubspec.yaml` y configura un cliente HTTP singleton con interceptores para inyección automática de token Bearer."*

---

## Fase 1: RF-MOB-01 - Autenticación y Control de Sesión

**Objetivo:** Permitir el ingreso del operario (cortador o reconector), persistir la sesión y restringir el acceso a vistas no autorizadas.

### Tareas para el Agente:
1. Diseñar la interfaz de usuario del Login idéntica a los mockups (fondo blanco con acentos verdes corporativos, campos `Usuario`, `Contraseña`, selector de visibilidad de password y botón `Iniciar Sesión`).
2. Implementar `AuthRepository` y su llamada REST contra la API Web (`POST /api/auth/login`).
3. Guardar token JWT y rol del usuario (`Cortador` / `Reconector`) en almacenamiento seguro.
4. Implementar redirección automática: si existe token válido al iniciar el splash, omitir el login.

### Criterio de Aceptación:
- El usuario ingresa credenciales, recibe token de sesión y es redirigido a la bandeja de trabajo con su nombre en el encabezado (ej. "Pedro").

---

## Fase 2: RF-MOB-02 - Bandeja de Trabajo y Lista de Órdenes

**Objetivo:** Mostrar los códigos asignados en el orden secuencial calculado por el algoritmo de Dijkstra en la aplicación web.

### Tareas para el Agente:
1. Implementar modelo de datos `OrdenTrabajo` / `AsignacionCorte`:
   - `id`, `ordenSecuencia` ($1, 2, 3\dots$), `codigoFijo`, `nombreCliente`, `latitud`, `longitud`, `estado` (*Pendiente*, *Cortado*, *Observado*).
2. Crear pantalla principal con encabezado temático (botón "Iniciar Recorrido", contador de pendientes y lista scrolleable).
3. Diseñar tarjeta (Card) de orden según el prototipo: badge numérico grande con el orden de visita ($1, 2, 3\dots$), nombre del abonado en negrita, código fijo y coordenadas.
4. Conectar llamada `GET /api/asignaciones/pendientes?tecnicoId={id}`.

### Criterio de Aceptación:
- La lista refleja exactamente la secuencia calculada en la web sin alterar el orden numérico.

---

## Fase 3: RF-MOB-03 - Georreferenciación y Navegación Asistida

**Objetivo:** Indicar distancia hacia el punto de corte y enlazar con apps externas de navegación vehicular/peatonal.

### Tareas para el Agente:
1. Implementar servicio de geolocalización con `geolocator`:
   - Solicitar permisos en tiempo de ejecución (`location_when_in_use`).
   - Obtener coordenadas actuales del operario ($lat_{actual}, lon_{actual}$) y precisión en metros.
2. Pantalla de detalle de la orden:
   - Panel superior con coordenadas destino vs. coordenadas actuales y precisión GPS.
   - Botón `Obtener GPS` para refrescar la posición del móvil.
3. Botón `Navegar`:
   - Implementar *Deep Linking* con `url_launcher` hacia Google Maps / Waze usando el esquema:
     `geo:lat,lng?q=lat,lng(NombreCliente)` o `google.navigation:q=lat,lng&mode=d`.

### Criterio de Aceptación:
- El botón `Navegar` abre la app de navegación externa trazando la ruta desde la posición actual hacia el destino de la orden.

---

## Fase 4: RF-MOB-04 y RF-MOB-05 - Registro Operativo con Validación Antifraude

**Objetivo:** Capturar la lectura del medidor, estado, fotos de respaldo y validar obligatoriamente la presencia física mediante GPS (regla de los 30 m).

### Tareas para el Agente:
1. Formulario de atención en la vista de la orden:
   - Campo numérico: *Avance actual del medidor*.
   - Selector radial: *Cortado* vs. *Observado*.
   - Campo de texto para justificación si es observado (ej. *"Casa cerrada"*).
   - Componente de captura fotográfica: botón `Tomar Fotografía` para almacenar hasta 3 imágenes locales.
2. **Validación Antifraude (RF-MOB-05 / RN-01):**
   - Al presionar `Guardar Resultado`:
     1. Obtener coordenada GPS obligatoria y fresca (menos de 10 segundos).
     2. Calcular distancia euclidiana/geodésica (Haversine) entre el móvil y el código fijo catastrado:
        $$d = 2r \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)}\right)$$
     3. Si $d > 30\text{ metros}$, bloquear el envío y alertar al usuario: *"No puede reportar fuera del radio de atención permitido (30 m)"*.
     4. Si $d \le 30\text{ metros}$, estampar en el payload: `$latitudEnvio`, `$longitudEnvio`, `$fechaHoraUtc`.
3. Consumir endpoint multipart `POST /api/cortes/registrar`.

### Criterio de Aceptación:
- No es posible guardar un corte u observación falso sin estar físicamente en el lugar y sin adjuntar evidencia fotográfica.

---

## Fase 5: RF-MOB-06 - Reconocimiento Óptico de Caracteres (OCR) del Medidor (Opcional)

**Objetivo:** Autocompletar la lectura del medidor analizando la fotografía tomada.

### Tareas para el Agente:
1. Integrar `google_mlkit_text_recognition` en el flujo de la cámara.
2. Al capturar la fotografía del medidor, recortar o procesar la imagen buscando secuencias numéricas (de 4 a 7 dígitos).
3. Si el OCR detecta una lectura con alto nivel de confianza, poblar automáticamente el campo de texto `Avance actual del medidor`, permitiendo corrección manual si fuese necesario.

### Criterio de Aceptación:
- Al tomar una fotografía nítida del medidor de agua, el valor numérico se escribe automáticamente en el formulario.

---

## Fase 6: Pruebas End-to-End, Sincronización y Empaquetado

**Objetivo:** Consolidar la solución y preparar el artefacto de entrega.

### Tareas para el Agente:
1. Validar el flujo completo: Asignación en Web $\rightarrow$ Visualización secuencial en Móvil $\rightarrow$ Navegación $\rightarrow$ Cierre con foto y GPS $\rightarrow$ Reflejo automático en el Dashboard y mapa de la Web.
2. Manejo de errores de red (modo offline temporal o reintentos si falla la subida).
3. Generación del APK de producción:
   ```bash
   flutter build apk --release
   ```