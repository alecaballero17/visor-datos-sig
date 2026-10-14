"""
Configuration and constants for SIG Vector Studio.
"""
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT_DIR.parent
DEFAULT_SHP_DIR = PROJECT_ROOT / "03_DatosPrueba" / "DatosSIG_Reproj"
ASSETS_DIR = ROOT_DIR / "assets"
WEB_DIR = ASSETS_DIR / "web"

# Spatial Reference & Default Center (San Ignacio de Velasco / Santa Cruz region)
DEFAULT_CENTER_LAT = -16.3900
DEFAULT_CENTER_LON = -60.9650
DEFAULT_ZOOM = 15
DEFAULT_SRID = 4326

# Layer Definitions & Colors (aligned with VisorDatosSIG)
LAYER_CONFIG = {
    "manzanas": {
        "title": "Manzanas",
        "geom_type": "Polygon",
        "color": "#dc2626",      # Vibrant Red
        "fill_color": "#ef4444",
        "fill_opacity": 0.12,
        "weight": 2.5,
        "shp_filename": "Exp_MapaBase_MZA_4326.shp",
        "table_name": "dbo.Manzanas",
        "id_col": "IdManzana"
    },
    "lotes": {
        "title": "Lotes / Terrenos",
        "geom_type": "Polygon",
        "color": "#0284c7",      # Vibrant Sky Blue
        "fill_color": "#38bdf8",
        "fill_opacity": 0.18,
        "weight": 1.5,
        "shp_filename": "Exp_MapaBase_LOTES_4326.shp",
        "table_name": "dbo.Lotes",
        "id_col": "IdLote"
    },
    "codigosfijos": {
        "title": "Códigos Fijos / Casas",
        "geom_type": "Point",
        "color": "#f59e0b",      # Warm Amber
        "fill_color": "#fbbf24",
        "fill_opacity": 0.9,
        "weight": 2,
        "radius": 5,
        "shp_filename": "Exp_CodigoFijo_4326.shp",
        "table_name": "dbo.CodigosFijos",
        "id_col": "IdCodigo"
    },
    "vias": {
        "title": "Vías / Calles",
        "geom_type": "LineString",
        "color": "#9333ea",      # Vivid Purple
        "fill_color": "none",
        "fill_opacity": 0.0,
        "weight": 3.5,
        "shp_filename": "Exp_MapaBase_VIAS_4326.shp",
        "table_name": "dbo.Vias",
        "id_col": "IdVia"
    }
}

# API backend defaults
API_BASE_URL = "http://localhost:5080/api"

# Tile services
OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
SATELLITE_TILE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
CARTODB_DARK_TILE_URL = "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"

# Default tile provider for color & shape extraction
DEFAULT_VECTORIZER_TILE_URL = OSM_TILE_URL
