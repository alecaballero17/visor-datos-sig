"""
LayerManager: Central in-memory repository and spatial coordination between Manzanas, Lotes, CodigosFijos, and Vias.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from sig_vector_studio.config import LAYER_CONFIG, DEFAULT_SHP_DIR
from sig_vector_studio.core.models import VectorLayer, Feature
from sig_vector_studio.core.shapefile_io import load_shapefile_into_layer
from sig_vector_studio.core.geometry import point_in_polygon, polygon_centroid

class LayerManager:
    def __init__(self):
        self.layers: Dict[str, VectorLayer] = {}
        self._init_layers()
        
    def _init_layers(self):
        for key, conf in LAYER_CONFIG.items():
            layer = VectorLayer(
                key=key,
                title=conf["title"],
                geom_type=conf["geom_type"],
                color=conf["color"],
                style_meta=conf
            )
            self.layers[key] = layer
            
    def load_from_default_directory(self, base_dir: Optional[Path] = None, max_per_layer: Optional[int] = None) -> Dict[str, int]:
        """Loads shapefiles from default 03_DatosPrueba/DatosSIG_Reproj."""
        shp_dir = base_dir or DEFAULT_SHP_DIR
        stats = {}
        for key, conf in LAYER_CONFIG.items():
            shp_path = shp_dir / conf["shp_filename"]
            if shp_path.exists():
                count = load_shapefile_into_layer(shp_path, self.layers[key], max_features=max_per_layer)
                stats[key] = count
            else:
                stats[key] = 0
        return stats
    
    def get_layer(self, key: str) -> Optional[VectorLayer]:
        return self.layers.get(key)
    
    def find_feature(self, layer_key: str, feature_id: int) -> Optional[Feature]:
        layer = self.get_layer(layer_key)
        return layer.get_feature(feature_id) if layer else None
    
    def find_parent_manzana_for_point(self, lon: float, lat: float) -> Optional[Feature]:
        """Spatial query: find which Manzana contains point (lon, lat)."""
        mza_layer = self.get_layer("manzanas")
        if not mza_layer:
            return None
            
        for feat in mza_layer.features.values():
            if feat.geom_type == "Polygon" and feat.coordinates:
                # Outer ring
                outer_ring = feat.coordinates[0]
                if point_in_polygon(lon, lat, outer_ring):
                    return feat
        return None

    def find_parent_lote_for_point(self, lon: float, lat: float) -> Optional[Feature]:
        """Spatial query: find which Lote contains point (lon, lat)."""
        lote_layer = self.get_layer("lotes")
        if not lote_layer:
            return None
            
        for feat in lote_layer.features.values():
            if feat.geom_type == "Polygon" and feat.coordinates:
                outer_ring = feat.coordinates[0]
                if point_in_polygon(lon, lat, outer_ring):
                    return feat
        return None

    def find_parent_manzana_for_polygon(self, coords: List[List[float]]) -> Optional[Feature]:
        """Find parent Manzana using centroid of polygon coords."""
        cx, cy = polygon_centroid(coords)
        return self.find_parent_manzana_for_point(cx, cy)
    
    def get_all_geojson(self) -> Dict[str, Any]:
        """Returns a composite GeoJSON structure with all active layers."""
        return {
            key: layer.to_geojson()
            for key, layer in self.layers.items()
        }
        
    def delete_feature(self, layer_key: str, feature_id: int) -> Optional[Feature]:
        """Elimina un vector de la capa especificada y lo retorna."""
        layer = self.get_layer(layer_key)
        if layer and feature_id in layer.features:
            feat = layer.features.pop(feature_id)
            return feat
        return None

    def delete_features_in_bbox(self, bbox: Tuple[float, float, float, float], layer_keys: Optional[List[str]] = None) -> List[Tuple[str, Feature]]:
        """
        Elimina todos los vectores que intersecan la caja envolvente (min_lon, min_lat, max_lon, max_lat).
        Retorna la lista de tuplas (layer_key, Feature) eliminados.
        """
        min_lon, min_lat, max_lon, max_lat = bbox
        min_lon, max_lon = min(min_lon, max_lon), max(min_lon, max_lon)
        min_lat, max_lat = min(min_lat, max_lat), max(min_lat, max_lat)

        target_keys = layer_keys or list(self.layers.keys())
        deleted_items: List[Tuple[str, Feature]] = []

        for key in target_keys:
            layer = self.get_layer(key)
            if not layer:
                continue
            to_delete = []
            for fid, feat in layer.features.items():
                bx = feat.bbox
                if not (bx[2] < min_lon or bx[0] > max_lon or bx[3] < min_lat or bx[1] > max_lat):
                    to_delete.append(fid)

            for fid in to_delete:
                feat = layer.features.pop(fid)
                deleted_items.append((key, feat))

        return deleted_items

    def get_global_extent(self) -> Tuple[float, float, float, float]:
        """Overall bounding box of all layers."""
        all_extents = [l.get_layer_extent() for l in self.layers.values() if l.get_layer_extent()]
        if not all_extents:
            return (-60.98, -16.41, -60.92, -16.35)
        min_xs = [e[0] for e in all_extents]
        min_ys = [e[1] for e in all_extents]
        max_xs = [e[2] for e in all_extents]
        max_ys = [e[3] for e in all_extents]
        return (min(min_xs), min(min_ys), max(max_xs), max(max_ys))
