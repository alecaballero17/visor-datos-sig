"""
GeoJSON Exporter for individual layers or complete workspace.
Compatible with Leaflet and VisorDatosSIG GeoDataService.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from sig_vector_studio.core.layer_manager import LayerManager

def export_layer_to_geojson_file(layer_manager: LayerManager, layer_key: str, output_path: Path | str) -> int:
    """Exports a single layer to GeoJSON file."""
    layer = layer_manager.get_layer(layer_key)
    if not layer:
        raise ValueError(f"Capa '{layer_key}' no encontrada.")
        
    data = layer.to_geojson()
    with open(str(output_path), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return len(data["features"])

def export_all_layers_to_directory(layer_manager: LayerManager, output_dir: Path | str) -> Dict[str, int]:
    """Exports all layers as individual .geojson files in output directory."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    stats = {}
    for key, layer in layer_manager.layers.items():
        file_path = out_path / f"{key}.geojson"
        stats[key] = export_layer_to_geojson_file(layer_manager, key, file_path)
    return stats
