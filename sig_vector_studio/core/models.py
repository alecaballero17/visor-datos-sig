"""
Data models for Vector Features and Layers.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from sig_vector_studio.core.geometry import get_geometry_bbox, bboxes_intersect, to_wkt

@dataclass
class Feature:
    id: int
    layer_key: str
    geom_type: str                   # 'Point', 'LineString', 'Polygon', 'MultiPolygon'
    coordinates: Any                 # GeoJSON coordinates format
    properties: Dict[str, Any] = field(default_factory=dict)
    is_new: bool = False             # Flag indicating feature was added in this session
    is_modified: bool = False        # Flag indicating properties or geometry modified
    
    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        return get_geometry_bbox(self.geom_type, self.coordinates)
    
    @property
    def centroid(self) -> Tuple[float, float]:
        bx = self.bbox
        return ((bx[0] + bx[2]) / 2.0, (bx[1] + bx[3]) / 2.0)
    
    @property
    def wkt(self) -> str:
        return to_wkt(self.geom_type, self.coordinates)
    
    def to_geojson_dict(self) -> Dict[str, Any]:
        return {
            "type": "Feature",
            "id": self.id,
            "geometry": {
                "type": self.geom_type,
                "coordinates": self.coordinates
            },
            "properties": {
                **self.properties,
                "_is_new": self.is_new,
                "_is_modified": self.is_modified,
                "_layer": self.layer_key
            }
        }

class VectorLayer:
    def __init__(self, key: str, title: str, geom_type: str, color: str, style_meta: Dict[str, Any] = None):
        self.key = key
        self.title = title
        self.geom_type = geom_type
        self.color = color
        self.style_meta = style_meta or {}
        self.features: Dict[int, Feature] = {}
        self.next_id: int = 1
        self.visible: bool = True
        
    def add_feature(self, geom_type: str, coordinates: Any, properties: Dict[str, Any] = None, feature_id: Optional[int] = None, is_new: bool = False) -> Feature:
        if feature_id is None:
            # Generate next safe ID
            feature_id = self.next_id
            while feature_id in self.features:
                feature_id += 1
            self.next_id = feature_id + 1
        else:
            if feature_id >= self.next_id:
                self.next_id = feature_id + 1
                
        feat = Feature(
            id=feature_id,
            layer_key=self.key,
            geom_type=geom_type,
            coordinates=coordinates,
            properties=properties or {},
            is_new=is_new
        )
        self.features[feature_id] = feat
        return feat
    
    def remove_feature(self, feature_id: int) -> Optional[Feature]:
        return self.features.pop(feature_id, None)
    
    def get_feature(self, feature_id: int) -> Optional[Feature]:
        return self.features.get(feature_id)
    
    def update_properties(self, feature_id: int, new_props: Dict[str, Any]):
        if feature_id in self.features:
            self.features[feature_id].properties.update(new_props)
            self.features[feature_id].is_modified = True
            
    def update_geometry(self, feature_id: int, geom_type: str, coordinates: Any):
        if feature_id in self.features:
            feat = self.features[feature_id]
            feat.geom_type = geom_type
            feat.coordinates = coordinates
            feat.is_modified = True
            
    def query_bbox(self, bbox: Tuple[float, float, float, float]) -> List[Feature]:
        """Find features intersecting the given bbox (minx, miny, maxx, maxy)."""
        return [f for f in self.features.values() if bboxes_intersect(f.bbox, bbox)]
    
    def get_layer_extent(self) -> Optional[Tuple[float, float, float, float]]:
        if not self.features:
            return None
        min_xs, min_ys, max_xs, max_ys = [], [], [], []
        for f in self.features.values():
            bx = f.bbox
            min_xs.append(bx[0])
            min_ys.append(bx[1])
            max_xs.append(bx[2])
            max_ys.append(bx[3])
        return (min(min_xs), min(min_ys), max(max_xs), max(max_ys))
    
    def to_geojson(self, filter_bbox: Optional[Tuple[float, float, float, float]] = None) -> Dict[str, Any]:
        feats = self.query_bbox(filter_bbox) if filter_bbox else list(self.features.values())
        return {
            "type": "FeatureCollection",
            "name": self.key,
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
            },
            "features": [f.to_geojson_dict() for f in feats]
        }
    
    def count(self) -> int:
        return len(self.features)
