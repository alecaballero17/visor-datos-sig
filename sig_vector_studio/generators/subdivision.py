"""
Algoritmo de Subdivisión Catastral y Generación Automática de Terrenos y Puntos de Servicio.
Subdivide automáticamente manzanas seleccionadas en lotes urbanos regulares con sus respectivos códigos fijos.
"""
from typing import List, Tuple, Dict, Any
from sig_vector_studio.core.models import Feature
from sig_vector_studio.core.geometry import point_in_polygon, polygon_centroid
from sig_vector_studio.generators.mock_data_generator import generate_owner_name_from_map, generate_service_state

def subdivide_manzana_into_lots(
    manzana_feature: Feature,
    next_lote_start_num: int = 1,
    next_cod_fijo_start: int = 60000,
    rows: int = 2,
    cols: int = 6,
    layer_manager = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Subdivide geométricamente una manzana en lotes regulares y genera sus puntos de servicio (Códigos Fijos).
    Retorna: (lotes_generados, codigos_fijos_generados)
    """
    coords = manzana_feature.coordinates
    if not coords:
        return [], []
        
    outer_ring = coords[0] if isinstance(coords[0][0], list) else coords
    minx, miny, maxx, maxy = manzana_feature.bbox

    # Reducir un pequeño margen perimetral para aceras/vías (5%)
    dx = (maxx - minx) * 0.05
    dy = (maxy - miny) * 0.05
    inner_minx, inner_maxx = minx + dx, maxx - dx
    inner_miny, inner_maxy = miny + dy, maxy - dy

    step_x = (inner_maxx - inner_minx) / cols
    step_y = (inner_maxy - inner_miny) / rows

    uv = str(manzana_feature.properties.get("UV", "105"))
    mza = str(manzana_feature.properties.get("MZA", "01"))
    id_mza = manzana_feature.id

    lotes_res = []
    cfs_res = []
    
    current_lote_num = next_lote_start_num
    current_cod_fijo = next_cod_fijo_start

    for r in range(rows):
        for c in range(cols):
            x0 = inner_minx + c * step_x
            x1 = x0 + step_x
            y0 = inner_miny + r * step_y
            y1 = y0 + step_y

            # Polígono del lote
            lot_coords = [
                [round(x0, 7), round(y0, 7)],
                [round(x1, 7), round(y0, 7)],
                [round(x1, 7), round(y1, 7)],
                [round(x0, 7), round(y1, 7)],
                [round(x0, 7), round(y0, 7)]
            ]

            cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0

            # Solo incorporar el lote si su centroide cae dentro de la manzana
            if point_in_polygon(cx, cy, outer_ring):
                nro_lote_str = f"{current_lote_num:02d}"
                lote_props = {
                    "NroLote": nro_lote_str,
                    "IdManzana": id_mza,
                    "UV_MZA": f"{uv}-{mza}",
                    "TieneAgua": True,
                    "UsoSuelo": "Residencial",
                    "IdOrigen": 80000 + current_lote_num
                }

                lotes_res.append({
                    "geom_type": "Polygon",
                    "coordinates": [lot_coords],
                    "properties": lote_props
                })

                # Generar automáticamente el punto de servicio de agua/casa
                cod_f_sig = f"{uv}-{mza}-{nro_lote_str}"
                owner_name = generate_owner_name_from_map(layer_manager)
                cf_props = {
                    "CodFijo": current_cod_fijo,
                    "CodF_SQL": current_cod_fijo,
                    "CodF_SIG": cod_f_sig,
                    "Nombre": owner_name,
                    "Estado": 1,
                    "EstadoVerificado": 1,
                    "Longitud": round(cx, 7),
                    "Latitud": round(cy, 7),
                    "TieneAgua": True
                }

                cfs_res.append({
                    "geom_type": "Point",
                    "coordinates": [round(cx, 7), round(cy, 7)],
                    "properties": cf_props
                })

                current_lote_num += 1
                current_cod_fijo += 1

    return lotes_res, cfs_res
