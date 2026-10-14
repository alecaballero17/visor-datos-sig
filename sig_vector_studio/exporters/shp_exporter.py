"""
Shapefile Exporter for LayerManager layers.
"""
from pathlib import Path
from typing import Dict
from sig_vector_studio.core.layer_manager import LayerManager
from sig_vector_studio.core.shapefile_io import save_layer_to_shapefile
from sig_vector_studio.config import LAYER_CONFIG

def export_all_layers_to_shapefiles(layer_manager: LayerManager, output_dir: Path | str) -> Dict[str, int]:
    """Exports all layers to .shp in the designated folder."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    stats = {}
    for key, layer in layer_manager.layers.items():
        conf = LAYER_CONFIG.get(key, {})
        shp_name = conf.get("shp_filename", f"{key}.shp")
        target_path = out_path / shp_name
        stats[key] = save_layer_to_shapefile(layer, target_path)
    return stats
