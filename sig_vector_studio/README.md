# SIG Vector Studio

**SIG Vector Studio** es una aplicación de escritorio modular en Python con interfaz gráfica profesional (Dark Slate Theme), diseñada para visualizar, modificar, crear vectores geográficos y vectorizar automáticamente elementos urbanos (vías, terrenos/lotes, casas/códigos fijos, manzanas) utilizando **imágenes satelitales de alta resolución y Visión por Computadora (OpenCV)**.

Cuenta con iconos vectoriales SVG limpios, un **algoritmo de asignación de códigos catastrales**, un **extractor de datos contextuales directamente del mapa real** (sin datos ficticios fijos) y compatibilidad total con la base de datos SQL Server y el visor web **VisorDatosSIG**.

---

## Arquitectura Modular

```
sig_vector_studio/
├── main.py                          # Punto de entrada y configuración de la app
├── config.py                        # Configuración de capas, estilos, coordenadas y mosaicos
│
├── core/                            # Núcleo geoespacial
│   ├── geometry.py                  # Algoritmos: Point-in-Polygon, Centroid, BBox, OGC WKT
│   ├── models.py                    # Entidades Feature, VectorLayer y Colecciones
│   ├── layer_manager.py             # Repositorio espacial, relaciones jerárquicas y queries
│   └── shapefile_io.py              # Lector/Escritor de Shapefiles (.shp, .dbf, .prj) con pyshp
│
├── cv_vectorizer/                   # Visión por Computadora e Imágenes Satelitales
│   ├── tile_downloader.py           # Descarga y ensamblado de mosaicos satelitales Esri World Imagery
│   └── contour_detector.py          # Extracción de contornos con OpenCV y conversión a EPSG:4326
│
├── generators/                      # Algoritmos de codificación y extracción de datos
│   ├── code_algorithm.py            # Algoritmo jerárquico de códigos (UV, MZA, NroLote, CodFijo, CodF_SIG)
│   └── mock_data_generator.py       # Extractor y sintetizador de nombres reales extraídos del mapa
│
├── exporters/                       # Exportación y compatibilidad con VisorDatosSIG
│   ├── sql_exporter.py              # Script T-SQL con geometry::STGeomFromText('...', 4326)
│   ├── geojson_exporter.py          # GeoJSON compatible con Leaflet y C# GeoDataService
│   └── shp_exporter.py              # Capas Shapefile listas para QGIS o migración ogr2ogr
│
├── gui/                             # Interfaz gráfica PyQt6
│   ├── main_window.py               # Ventana principal, barra de herramientas y docks
│   ├── map_widget.py                # Visor Leaflet interactivo con QWebChannel / WebEngine
│   ├── cv_dialog.py                 # Asistente de vectorización por visión satelital
│   ├── attribute_editor.py          # Inspector y editor de atributos de vectores
│   ├── export_dialog.py             # Diálogo de exportación a SQL, GeoJSON y SHP
│   ├── icons.py                     # Proveedor de iconos vectoriales SVG limpios
│   └── styles.py                    # Hoja de estilos moderna oscura (Dark Slate QSS)
│
└── assets/web/                      # Motor de mapas web embebido
    ├── index.html                   # Contenedor Leaflet interactivo
    ├── map_controller.js            # Lógica de dibujo, selección y puente bidireccional con Python
    └── qwebchannel.js               # Biblioteca de comunicación Qt WebChannel
```

---

## 🚀 Cómo Iniciar la Aplicación

Puedes iniciar la aplicación de cualquiera de las siguientes formas:

1. **Doble clic en el archivo por lotes:**
   ```cmd
   iniciar_editor.cmd
   ```

2. **Desde PowerShell:**
   ```powershell
   .\iniciar_editor.ps1
   ```

3. **Desde la terminal con Python:**
   ```bash
   python sig_vector_studio/main.py
   ```

---

## ✨ Funcionalidades Principales

### 1. Visualizador y Mapeo Integrado
- Muestra el mismo mapa que la plataforma web (`[-16.390, -60.965]`).
- Selector de mapa base:
  - 🛰️ **Satelital Alta Resolución (Esri World Imagery)**.
  - 🗺️ **OpenStreetMap**.
  - 🌃 **CartoDB Dark Matter**.
- Visualiza las capas con los mismos colores y estilos oficiales:
  - **Manzanas**: Polígonos rojos (`#dc2626`).
  - **Lotes / Terrenos**: Polígonos cian (`#0284c7`).
  - **Códigos Fijos / Casas**: Marcadores ámbar (`#f59e0b`).
  - **Vías / Calles**: Líneas violetas (`#9333ea`).

### 2. Edición y Creación Manual de Vectores
- **Modo Navegación**: Haz clic en cualquier vector para seleccionarlo y abrir su inspector de atributos.
- **Dibujar Lote / Terreno**: Dibuja polígonos clic a clic. Al presionar `Enter` o el botón "Terminar Dibujo", se calcula automáticamente el lote.
- **Dibujar Manzana**: Traza nuevas manzanas urbanas.
- **Agregar Casa / Código Fijo**: Haz clic en cualquier ubicación para agregar un punto de servicio o predio.
- **Dibujar Vía**: Traza calles, avenidas y pasajes.

### 3. Vectorización Automática por Imagen Satelital (Visión por Computadora)
1. Activa la herramienta **🛰️ Vectorizar con Imagen Satelital (IA / CV)** en la barra superior.
2. Arrastra un recuadro (BBOX) sobre la zona satelital deseada.
3. Se abrirá el diálogo con la imagen satelital en alta resolución descargada al instante.
4. Mediante **OpenCV** (CLAHE, filtros bilaterales, Canny, umbralización adaptativa/Otsu y Douglas-Peucker):
   - Detecta techos de casas, perímetros de parcelas/terrenos o trazas de calles.
   - Ajusta la sensibilidad, área mínima y tolerancia geométrica con controles deslizantes en vivo.
5. Haz clic en **✓ Asignar Códigos e Importar al Mapa**: los vectores se integrarán al mapa automáticamente con sus atributos calculados.

### 4. Algoritmo de Códigos Catastrales y Datos Sintéticos (Faker)
- **Para Manzanas**: Asigna `UV` (Unidad Vecinal), `MZA` secuencial y código compuesto `UV_MZA` (ej: `105-014`).
- **Para Lotes**: Determina espacialmente qué Manzana lo contiene (`IdManzana`) y calcula el siguiente `NroLote` correlativo (ej: `01`, `02`, `15`...).
- **Para Códigos Fijos (Casas / Agua)**: Determina qué Lote y Manzana lo contienen (`IdLote`), asigna `CodFijo` secuencial único (ej: `60001`), código jerárquico `CodF_SIG` (ej: `105-01-15`) y estado inicial activo.
- **Generador de Datos**: Asigna nombres bolivianos realistas de propietarios (ej: *Carlos Alberto Justiniano Saucedo*), estados de conexión de agua, categorías de vías (*Avenida*, *Calle*, *Pasaje*) y números de contrato.

### 5. Compatibilidad con la Base de Datos y la Plataforma VisorDatosSIG
Haz clic en **💾 Exportar a Base de Datos / SQL**:
- **Script SQL Server (`.sql`)**: Genera sentencias `INSERT INTO dbo.Lotes ... geometry::STGeomFromText('POLYGON(...)', 4326)` listas para ejecutar en SSMS o SQLCMD, incluyendo la re-sincronización de llaves foráneas espaciales.
- **Archivos GeoJSON (`.geojson`)**: Estructura compatible con el controlador de capas y la API C# Blazor.
- **Capas Shapefile (`.shp`)**: Archivos vectoriales listos para abrir en QGIS o importar con `ogr2ogr`.
