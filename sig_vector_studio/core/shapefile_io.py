"""
Shapefile Import / Export using pyshp (shapefile library).
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import shapefile
from sig_vector_studio.core.models import VectorLayer, Feature

def shape_to_geojson_geometry(shp: shapefile.Shape) -> Tuple[str, Any]:
    """Convert a pyshp Shape object into GeoJSON (geom_type, coordinates)."""
    shape_type = shp.shapeType
    
    # Point
    if shape_type in (shapefile.POINT, shapefile.POINTZ, shapefile.POINTM):
        return ("Point", [float(shp.points[0][0]), float(shp.points[0][1])])
    
    # MultiPoint
    if shape_type in (shapefile.MULTIPOINT, shapefile.MULTIPOINTZ, shapefile.MULTIPOINTM):
        pts = [[float(p[0]), float(p[1])] for p in shp.points]
        return ("MultiPoint", pts)
    
    # Polyline / LineString
    if shape_type in (shapefile.POLYLINE, shapefile.POLYLINEZ, shapefile.POLYLINEM):
        parts = list(shp.parts) + [len(shp.points)]
        lines = []
        for i in range(len(parts) - 1):
            segment = [[float(p[0]), float(p[1])] for p in shp.points[parts[i]:parts[i+1]]]
            lines.append(segment)
        if len(lines) == 1:
            return ("LineString", lines[0])
        return ("MultiLineString", lines)
    
    # Polygon
    if shape_type in (shapefile.POLYGON, shapefile.POLYGONZ, shapefile.POLYGONM):
        parts = list(shp.parts) + [len(shp.points)]
        rings = []
        for i in range(len(parts) - 1):
            ring = [[float(p[0]), float(p[1])] for p in shp.points[parts[i]:parts[i+1]]]
            rings.append(ring)
        if len(rings) == 1:
            return ("Polygon", rings)
        return ("Polygon", rings)  # In GeoJSON Polygon coords is [outer, inner1, inner2...]
    
    return ("Unknown", None)

def load_shapefile_into_layer(filepath: Path | str, layer: VectorLayer, max_features: Optional[int] = None) -> int:
    """
    Loads shapes and records from a .shp file into the target VectorLayer.
    Returns the count of loaded features.
    """
    path_str = str(filepath)
    if not os.path.exists(path_str):
        raise FileNotFoundError(f"No existe el archivo shapefile: {path_str}")
        
    # Check for .cpg file
    cpg_path = Path(path_str).with_suffix(".cpg")
    encoding = "utf-8"
    if cpg_path.exists():
        try:
            with open(cpg_path, "r", encoding="ascii", errors="ignore") as f:
                cpg_enc = f.read().strip().lower()
                if cpg_enc in ("utf-8", "utf8"):
                    encoding = "utf-8"
                elif cpg_enc in ("latin1", "iso-8859-1", "1252", "cp1252"):
                    encoding = "latin1"
        except Exception:
            pass

    reader = shapefile.Reader(path_str, encoding=encoding)
    field_names = [f[0] for f in reader.fields[1:]]
    
    count = 0
    for shape_record in reader.iterShapeRecords():
        shp = shape_record.shape
        rec = shape_record.record
        
        geom_type, coords = shape_to_geojson_geometry(shp)
        if geom_type == "Unknown" or not coords:
            continue
            
        props = {}
        for fname, val in zip(field_names, rec):
            # Clean strings and handle None
            if isinstance(val, bytes):
                val = val.decode("latin1", errors="replace")
            elif isinstance(val, str):
                val = val.strip()
            props[fname] = val
            
        # Assign a primary ID only if positive and unique
        fid = None
        for id_cand in ["OBJECTID", "IdManzana", "IdLote", "IdCodigo", "IdVia"]:
            if id_cand in props and isinstance(props[id_cand], int) and props[id_cand] > 0:
                if props[id_cand] not in layer.features:
                    fid = props[id_cand]
                    break
                
        layer.add_feature(geom_type, coords, props, feature_id=fid, is_new=False)
        count += 1
        if max_features and count >= max_features:
            break
            
    return count

def save_layer_to_shapefile(layer: VectorLayer, output_path: Path | str) -> int:
    """
    Exports a VectorLayer into a Shapefile (.shp, .shx, .dbf, .prj).
    """
    path_str = str(output_path)
    if path_str.lower().endswith(".shp"):
        base_name = path_str[:-4]
    else:
        base_name = path_str
        
    geom_type = layer.geom_type
    if geom_type == "Point":
        shp_type = shapefile.POINT
    elif geom_type in ("LineString", "MultiLineString"):
        shp_type = shapefile.POLYLINE
    else:
        shp_type = shapefile.POLYGON
        
    w = shapefile.Writer(base_name, shapeType=shp_type, encoding="latin1")
    
    # Collect all unique property field names
    all_fields: Dict[str, str] = {}
    for feat in layer.features.values():
        for k, v in feat.properties.items():
            if k.startswith("_"):
                continue
            if k not in all_fields:
                if isinstance(v, int):
                    all_fields[k] = "N"
                elif isinstance(v, float):
                    all_fields[k] = "F"
                else:
                    all_fields[k] = "C"
                    
    # Define DBF fields (truncate name to 10 chars per dBase spec)
    clean_field_map = {}
    for fld, ftype in all_fields.items():
        short_name = fld[:10]
        # Avoid collisions
        suffix = 1
        while short_name in [v[0] for v in clean_field_map.values()]:
            short_name = f"{fld[:8]}{suffix}"
            suffix += 1
        clean_field_map[fld] = (short_name, ftype)
        if ftype == "N":
            w.field(short_name, "N", 10, 0)
        elif ftype == "F":
            w.field(short_name, "F", 18, 8)
        else:
            w.field(short_name, "C", 80)
            
    saved_count = 0
    for feat in layer.features.values():
        # Geometry
        if feat.geom_type == "Point":
            w.point(feat.coordinates[0], feat.coordinates[1])
        elif feat.geom_type == "LineString":
            w.line([feat.coordinates])
        elif feat.geom_type == "Polygon":
            w.poly(feat.coordinates)
        else:
            continue
            
        # Record
        rec_dict = {}
        for orig_k, (short_k, ftype) in clean_field_map.items():
            val = feat.properties.get(orig_k, "")
            if val is None:
                val = 0 if ftype in ("N", "F") else ""
            rec_dict[short_k] = val
        w.record(**rec_dict)
        saved_count += 1
        
    w.close()
    
    # Write PRJ file for EPSG:4326 (WGS 84)
    prj_content = (
        'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],'
        'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
    )
    with open(f"{base_name}.prj", "w", encoding="utf-8") as f:
        f.write(prj_content)
        
    return saved_count
