"""
SectorFeeder: Alimentador y extractor espacial de datos catastrales oficiales.
Permite consultar e importar instantáneamente vías, manzanas, lotes y casas oficiales
que intersecan un BBOX (cuadrante) seleccionado en el mapa desde los Shapefiles del proyecto.
"""
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from sig_vector_studio.config import DEFAULT_SHP_DIR
from sig_vector_studio.core.shapefile_io import load_shapefile_into_layer
from sig_vector_studio.core.models import VectorLayer, Feature

class SectorFeeder:
    _cached_layers: Optional[Dict[str, VectorLayer]] = None

    @classmethod
    def load_official_dataset(cls) -> Dict[str, VectorLayer]:
        """Carga en caché los shapefiles oficiales del proyecto."""
        if cls._cached_layers is not None:
            return cls._cached_layers

        layers = {
            "vias": VectorLayer("vias", "Vías / Calles Oficiales", "LineString", "#9333ea"),
            "manzanas": VectorLayer("manzanas", "Manzanas Oficiales", "Polygon", "#dc2626"),
            "lotes": VectorLayer("lotes", "Lotes Oficiales", "Polygon", "#0284c7"),
            "codigosfijos": VectorLayer("codigosfijos", "Casas / Medidores Oficiales", "Point", "#f59e0b")
        }

        files_map = {
            "vias": "Exp_MapaBase_VIAS_4326.shp",
            "manzanas": "Exp_MapaBase_MZA_4326.shp",
            "lotes": "Exp_MapaBase_LOTES_4326.shp",
            "codigosfijos": "Exp_CodigoFijo_4326.shp"
        }

        for key, fname in files_map.items():
            shp_path = DEFAULT_SHP_DIR / fname
            if shp_path.exists():
                try:
                    load_shapefile_into_layer(shp_path, layers[key])
                except Exception as e:
                    print(f"[SectorFeeder] Error cargando {fname}: {e}")

        cls._cached_layers = layers
        return cls._cached_layers

    @classmethod
    def get_features_in_bbox(cls, bbox: Tuple[float, float, float, float]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retorna todos los vectores oficiales que intersecan la zona seleccionada (min_lon, min_lat, max_lon, max_lat).
        """
        min_lon, min_lat, max_lon, max_lat = bbox
        min_lon, max_lon = min(min_lon, max_lon), max(min_lon, max_lon)
        min_lat, max_lat = min(min_lat, max_lat), max(min_lat, max_lat)

        layers = cls.load_official_dataset()
        results: Dict[str, List[Dict[str, Any]]] = {
            "vias": [],
            "manzanas": [],
            "lotes": [],
            "codigosfijos": []
        }

        for key, layer in layers.items():
            for feat in layer.features.values():
                bx = feat.bbox
                # Comprobar intersección de cajas envolventes
                if not (bx[2] < min_lon or bx[0] > max_lon or bx[3] < min_lat or bx[1] > max_lat):
                    results[key].append({
                        "geom_type": feat.geom_type,
                        "coordinates": feat.coordinates,
                        "properties": dict(feat.properties),
                        "centroid": feat.centroid
                    })

        return results
