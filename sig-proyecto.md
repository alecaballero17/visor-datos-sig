# **Specification de Requerimientos Funcionales (SRS)**

# **GeoIT Operaciones \- Sistema de Gestión de Cortes y Reconexiones de Agua**

# **1\. Ficha del Proyecto y Generalidades**

| Parámetro | Detalle del Proyecto |
| :---- | :---- |
| **Materia** | Sistemas de Información Geográfica (SIG 2/2026) |
| **Docente** | Ing. Ubaldo Perez |
| **Proyecto** | GeoIT Operaciones / GeoConsulta \- Visor Catastral y Operaciones Móviles |
| **Plataformas** | Plataforma Web (Administración/Monitoreo) y Aplicación Móvil (Operaciones Campo) |
| **Estado** | Especificación Técnica Completa |

## **1.1. Objetivo General**

Desarrollar e implementar un sistema georreferenciado integrado (Web y Móvil) para la gestión territorial de cortes y reconexiones de agua potable. La solución optimiza la planificación de cuadrillas, automatiza la asignación de rutas mediante algoritmos de red vial y garantiza el registro auditable de evidencias en terreno con validación antifraude.

---

# **2\. Requerimientos Funcionales \- Aplicación Web (Administración y Monitoreo)**

El módulo web centraliza el análisis territorial, la planificación operativa y la supervisión del personal técnico.

## **RF-WEB-01: Autenticación y Control de Sesión**

* **Descripción**: El sistema debe proveer un mecanismo seguro de inicio y cierre de sesión para usuarios con rol de Administrador o Supervisor Operativo.  
* **Criterios de Aceptación**:  
  * Autenticación basada en credenciales cifradas (Usuario / Contraseña).  
  * Control de acceso basado en roles (RBAC) restrictivo a funciones administrativas.  
  * Cierre automático de sesión tras 15 minutos de inactividad.

## **RF-WEB-02: Dashboard General y Métricas Operativas**

* **Descripción**: Panel de control con indicadores clave de rendimiento (KPIs) sobre el estado de las conexiones.  
* **Tarjetas de Resumen**:  
  * Total de conexiones catastradas.  
  * Conexiones en estado Normal.  
  * Conexiones programadas Para Corte.  
  * Conexiones en estado Cortado.  
  * Conexiones en Baja Parcial.  
  * Conexiones en Baja Total.  
* **Componentes Gráficos**:  
  * Gráfico de Barras: Comparativa de intervenciones ejecutadas vs. pendientes por cuadrilla.  
  * Gráfico de Dona: Distribución porcentual del estado de las conexiones del municipio.

## **RF-WEB-03: Visor Geográfico Catastral 2D y 3D**

* **Descripción**: Mapeo interactivo de la infraestructura catastral con capacidad de renderizado tridimensional.  
* **Capas Vectores**:  
  * Códigos fijos (puntos de acometida) clasificados semánticamente por color según estado comercial/operativo.  
  * Manzanas y Lotes (polígonos catastrales con dimensiones).  
  * Red de vías y calles (`dbo.Vias`).  
* **Mapas Base (Basemaps)**: Alternancia dinámica entre OpenStreetMap y Google Maps (Satélite/Híbrido).  
* **Navegación espacial**:  
  * Alternancia fluida entre visualización 2D y 3D (WebGL) con controles de inclinación (pitch) y rotación (bearing).  
  * Módulo de búsqueda rápida por Código Fijo o Nombre de Cliente con centrado automático de cámara (Fly-to).

## **RF-WEB-04: Planificación Operativa y Asignación de Tareas**

* **Descripción**: Módulo para la creación de órdenes de trabajo masivas e individuales (Cortes y Reconexiones).  
* **Flujo Operativo**:  
  * Selección del tipo de trabajo: Asignación de Cortes o Asignación de Reconexiones.  
  * Seleccionar operario o cuadrilla de campo responsable.  
  * Definición del volumen de trabajo (cantidad de códigos fijos a intervenir).  
  * Selección interactiva del punto de partida inicial de la cuadrilla mediante un clic directo sobre el mapa.

## **RF-WEB-05: Optimización de Rutas mediante Red Vial**

* **Descripción**: Motor de cálculo de trayectorias eficientes basado en la topología de la ciudad.  
* **Criterios Técnicos**:  
  * Cálculo de la ruta óptima utilizando el **Algoritmo de Dijkstra** sobre la tabla topológica de calles (`dbo.Vias`).  
  * Ordenamiento secuencial estricto de puntos de parada (1, 2, 3... N).  
  * Restricción topológica: La ruta debe circular exclusivamente sobre ejes viales, prohibiendo el cruce o cruce diagonal de manzanas catastrales.  
  * Persistencia de la secuencia asignada en la base de datos centralizada para su consumo automático por la app móvil.

## **RF-WEB-06: Monitoreo y Seguimiento de Personal en Campo**

* **Descripción**: Módulo de telemetría e inspección del recorrido de los técnicos.  
* **Funcionalidades**:  
  * Visualización en vivo o histórica del recorrido de cada operario.  
  * Renderizado del trazo GPS con marcas de tiempo (timestamps) y registro de velocidad de avance.  
  * Panel lateral con porcentaje de cumplimiento de la hoja de ruta asignada.

---

# **3\. Requerimientos Funcionales \- Aplicación Móvil (Operaciones en Campo)**

Herramienta nativa/híbrida para teléfonos inteligentes utilizada por las cuadrillas de corte y reconexión.

## **RF-MOB-01: Autenticación de Operadores en Campo**

* **Descripción**: Control de acceso para técnicos en terreno.  
* **Criterios de Aceptación**:  
  * Identificación individual con perfil asignado: **Cortador** o **Reconector**.  
  * Carga de token de sesión para trabajo en zonas de baja cobertura.

## **RF-MOB-02: Bandeja de Trabajo y Lista de Órdenes Asignadas**

* **Descripción**: Vista principal del operario con su ruta programada del día.  
* **Estructura**:  
  * Presentación cronológica y secuencial de los puntos (1, 2, 3... N) según la optimización de la web.  
  * Ficha descriptiva por punto: Nombre del cliente, Código Fijo, Dirección, Estado actual y Coordenadas geográficas.

## **RF-MOB-03: Georreferenciación y Navegación Asistida**

* **Descripción**: Guía de traslado del técnico desde su posición actual hacia el siguiente servicio.  
* **Componentes**:  
  * Captura en tiempo real del GPS del dispositivo para calcular la distancia en metros/kilómetros al objetivo.  
  * Botón **"Navegar"**: Integración mediante *Deep Links* hacia aplicaciones externas de navegación (Google Maps / Waze) para recibir instrucciones turn-by-turn.

## **RF-MOB-04: Registro Operativo y Captura de Evidencias en Terreno**

* **Descripción**: Formulario digital de cierre de orden de trabajo.  
* **Campos del Registro**:  
  * Estado final de la intervención: **Cortado** / **Reconectado** u **Observado** (Impedimento técnico/social).  
  * Lectura del medidor o nivel de avance actual.  
  * Campo de texto para observaciones estructuradas (ej. "Casa cerrada", "Medidor no visible", "Perro agresivo").  
  * Módulo de cámara: Captura obligatoria de **hasta 3 fotografías** de evidencia visual directa.

## **RF-MOB-05: Validación Geográfica y Temporal Antifraude**

* **Descripción**: Mecanismo de auditoría pasiva para garantizar el trabajo físico real.  
* **Funcionamiento**:  
  * En el instante exacto en que se presiona "Guardar Registro", la aplicación captura de forma automatizada e inalterable: la fecha/hora del dispositivo y las coordenadas GPS instantáneas.  
  * Estos datos se adjuntan al paquete de la orden de trabajo para corroborar que el técnico estaba a una distancia válida del código fijo.

## **RF-MOB-06: Reconocimiento Óptico de Caracteres (OCR) del Medidor (Avanzado)**

* **Descripción**: Módulo opcional de inteligencia artificial embebida.  
* **Funcionamiento**: Escaneo automático de los números de la carátula del medidor desde la foto tomada por la cámara, rellenando automáticamente el campo "Lectura del Medidor" para minimizar errores humanos de digitación.

---

# **4\. Requisitos No Funcionales y Reglas de Negocio**

## **4.1. Requisitos No Funcionales (RNF)**

\+------------------------------------------------------------------------------------+

\| REQUISITOS NO FUNCIONALES DE ARQUITECTURA Y DESEMPEÑO                             \|

\+---------------------+--------------------------------------------------------------+

\| RNF-01: Precisión y \| El algoritmo de ruteo debe conectarse a la capa de red vial  \|

\| Topología Vial      \| dbo.Vias respetando el sentido de calles y giros permitidos. \|

\+---------------------+--------------------------------------------------------------+

\| RNF-02: Interfaz y  \| El visor WebGL debe mantener una tasa constante \>= 30 FPS   \|

\| Rendimiento WebGL   \| durante la renderización de modelos 3D y capas vectoriales. \|

\+---------------------+--------------------------------------------------------------+

\| RNF-03: Latencia y  \| Sincronización de registros móviles hacia la base de datos   \|

\| Sincronización      \| centralizada en menos de 3 segundos con conexión LTE/5G.     \|

\+---------------------+--------------------------------------------------------------+

## **4.2. Reglas de Negocio (RN)**

1. **RN-01: Obligatoriedad de Validación Geográfica Antifraude**  
   * No se aceptará ningún registro de corte, reconexión u observación si la distancia entre la coordenada del registro del móvil y la coordenada del código fijo catastrado supera el radio de tolerancia de **30 metros**. La solicitud será rechazada por el sistema impidiendo el reporte falso.  
2. **RN-02: Paquete Estándar de Entregables del Proyecto**  
   * El proyecto deberá ser entregado formalmente incluyendo:  
     * Documentación Técnica y Funcional (Manuales de Usuario y Arquitectura).  
     * Scripts de Base de Datos Espacial (Definición de tablas `dbo.Vias`, catastro, triggers e índices espaciales PostGIS/SQL Server Spatial).  
     * Código Fuente completo compilable tanto de la solución Web como de la App Móvil.  
     * Repositorio de código o enlace centralizado en la nube con empaquetado para despliegue en servidor web.

---

# **5\. Matriz de Seguimiento y Estado de Ejecución del Proyecto**

A continuación se detalla el estado de cumplimiento y la arquitectura implementada en la plataforma:

### **5.1. Plataforma Web (Administración y Monitoreo)**

| Código | Requisito Funcional | Estado | Grado | Detalles de la Implementación Técnica |
| :--- | :--- | :---: | :---: | :--- |
| **RF-WEB-01** | Autenticación y Control de Sesión | **Completado** | **100%** | Cookie segura (`Arquis.Auth`), roles RBAC (`Administrador`, `Consultor`, `Cortador`, `Reconector`), y **cierre automático tras 15 minutos exactos de inactividad** en backend (`ExpireTimeSpan = TimeSpan.FromMinutes(15)`) y frontend. |
| **RF-WEB-02** | Dashboard General y Métricas Operativas | **Completado** | **100%** | 6 tarjetas de resumen (Total, Normal, Para Corte, Cortado, Baja Parcial, Baja Total), gráfico de dona de distribución porcentual y comparativa de barras de intervenciones ejecutadas vs. pendientes por cuadrilla en `DashboardController.cs` y `DashboardKpiModal.razor`. |
| **RF-WEB-03** | Visor Geográfico Catastral 2D y 3D | **Completado** | **100%** | **Doble motor integrado**: Visor 2D (Leaflet) para gestión y catastro rápido, y **Motor WebGL Nativo 3D** (`webglEngine.js` con Three.js) acelerado por hardware con extrusión volumétrica de lotes/manzanas, balizas luminiscentes de acometidas según estado comercial, controles espaciales de **Inclinación (Pitch: 15°-85°)**, **Rotación (Bearing: 0°-360°)** y **tasa constante $\ge 30-60$ FPS** (RNF-02). |
| **RF-WEB-04** | Planificación Operativa y Asignación | **Completado** | **100%** | Creación masiva e individual de tickets de corte y reconexión, selección territorial por UV/MZA, asignación de cuadrillas con roles específicos y **selección interactiva del punto de partida inicial mediante clic directo en el mapa**. |
| **RF-WEB-05** | Optimización de Rutas mediante Red Vial | **Completado** | **100%** | Algoritmo de Dijkstra sobre la topología vial `dbo.Vias` (`DijkstraRoutingService.cs`), ordenamiento secuencial estricto ($1, 2, 3\dots N$) sobre ejes de calle prohibiendo cruce diagonal de manzanas, cálculo de distancias/tiempos y persistencia GeoJSON. |
| **RF-WEB-06** | Monitoreo y Seguimiento de Personal | **Completado** | **100%** | Módulo de telemetría completa integrado en el panel lateral (`MonitoreoGpsView.razor`): **modo en vivo** con posiciones GPS instantáneas, velocidad, rumbo y batería; **modo histórico** con reproductor animado tipo Timeline y timestamps; y **panel lateral con porcentaje de cumplimiento de la hoja de ruta asignada** ($\% = \frac{\text{Ejecutadas}}{\text{Total}} \times 100\%$), métricas de avance y trazado de ruta en mapa. |

### **5.2. Aplicación Móvil (Operaciones en Campo - Flutter)**

| Código | Requisito Funcional | Estado | Grado | Detalles / Brechas Pendientes para Siguiente Fase |
| :--- | :--- | :---: | :---: | :--- |
| **RF-MOB-01** | Autenticación de Operadores | Parcial | 70% | Login operativo contra API; pendiente persistencia segura de token/cookie (`shared_preferences`) para auto-login offline. |
| **RF-MOB-02** | Bandeja de Trabajo y Órdenes Asignadas | En Proceso | 45% | La app arranca en mapa; pendiente construir la pantalla en lista scrolleable de órdenes secuenciales ($1, 2, 3\dots$) según mockups. |
| **RF-MOB-03** | Georreferenciación y Navegación Asistida | Parcial | 65% | GPS en tiempo real y distancias calculadas; pendiente botón "Navegar" con Deep Linking (`url_launcher`) hacia Waze/Google Maps. |
| **RF-MOB-04** | Registro Operativo y Evidencias | **Completado** | **100%** | Modal completo `FormularioCierreOrdenModal.dart` integrado con selector radial (*Cortado/Reconectado* vs *Observado* con catálogo estructurado de 8 motivos), campo numérico de *Lectura del medidor*, campo de notas y **captura estricta de 1 fotografía de evidencia** (`image_picker` con preview, reintento y codificación Base64). |
| **RF-MOB-05** | Validación Antifraude (Radio 30 m) | **Completado** | **100%** | Doble anillo de validación: cálculo preventivo en el cliente con alerta visual de proximidad e indicador de distancia respecto al predio, y validación estricta en backend (`RN-01`) que rechaza solicitudes con $d > 30\text{ m}$. Integrado con coordenadas GPS en vivo (`TrackingGpsService`). |
| **RF-MOB-06** | OCR del Medidor con ML Kit | No Iniciado | 0% | Módulo avanzado opcional; pendiente integrar `google_mlkit_text_recognition`. |


