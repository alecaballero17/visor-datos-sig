"""
Algoritmo de codificación jerárquica y asignación de identificadores catastrales/servicios.
Genera códigos compatibles con la base de datos VisorDatosSIG (Manzanas, Lotes, CodigosFijos, Vias).
"""
import re
from typing import Dict, Any, Optional, Tuple, List
from sig_vector_studio.core.layer_manager import LayerManager
from sig_vector_studio.core.geometry import polygon_centroid

class CodeAssignmentAlgorithm:
    def __init__(self, layer_manager: LayerManager):
        self.lm = layer_manager

    def assign_codes_for_manzana(self, coords: List[List[float]], uv_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Calcula y asigna códigos únicos para una nueva Manzana:
        - UV (Unidad Vecinal)
        - MZA (Número de Manzana)
        - UV_MZA (Código catastral compuesto)
        """
        mza_layer = self.lm.get_layer("manzanas")
        existing_mzas = list(mza_layer.features.values()) if mza_layer else []
        
        # Determinar UV
        if uv_hint:
            uv = uv_hint.strip()
        else:
            # Encontrar UV de la manzana más cercana
            cx, cy = polygon_centroid(coords[0] if coords and isinstance(coords[0][0], list) else coords)
            nearest_uv = "105"
            min_dist = float("inf")
            for f in existing_mzas:
                feat_uv = f.properties.get("UV")
                if feat_uv:
                    bx = f.bbox
                    fcx = (bx[0] + bx[2]) / 2.0
                    fcy = (bx[1] + bx[3]) / 2.0
                    d = (cx - fcx)**2 + (cy - fcy)**2
                    if d < min_dist:
                        min_dist = d
                        nearest_uv = str(feat_uv)
            uv = nearest_uv

        # Determinar siguiente número de MZA dentro de esa UV
        mza_nums = []
        for f in existing_mzas:
            if str(f.properties.get("UV", "")) == uv:
                m_str = str(f.properties.get("MZA", ""))
                # Extraer números
                match = re.search(r"\d+", m_str)
                if match:
                    mza_nums.append(int(match.group()))
                    
        next_mza_num = (max(mza_nums) + 1) if mza_nums else 1
        mza_code = f"{next_mza_num:03d}"
        uv_mza = f"{uv}-{mza_code}"
        
        return {
            "UV": uv,
            "MZA": mza_code,
            "UV_MZA": uv_mza,
            "IdOrigen": 9000 + next_mza_num
        }

    def assign_codes_for_lote(self, coords: List[List[float]]) -> Dict[str, Any]:
        """
        Calcula y asigna códigos para un nuevo Lote:
        - Detecta espacialmente la Manzana contenedora (IdManzana).
        - Calcula el siguiente NroLote correlativo dentro de esa Manzana.
        """
        outer_coords = coords[0] if coords and isinstance(coords[0][0], list) else coords
        parent_mza = self.lm.find_parent_manzana_for_polygon(outer_coords)
        
        id_mza = parent_mza.id if parent_mza else None
        uv_mza_label = parent_mza.properties.get("UV_MZA", "S/M") if parent_mza else "S/M"
        
        # Buscar todos los lotes de esta manzana para encontrar el siguiente NroLote
        lote_layer = self.lm.get_layer("lotes")
        existing_lotes = list(lote_layer.features.values()) if lote_layer else []
        
        lote_nums = []
        if id_mza is not None:
            for l in existing_lotes:
                if l.properties.get("IdManzana") == id_mza or l.properties.get("Id_MZA") == id_mza:
                    num_str = str(l.properties.get("NroLote", ""))
                    match = re.search(r"\d+", num_str)
                    if match:
                        lote_nums.append(int(match.group()))
                        
        next_lote_num = (max(lote_nums) + 1) if lote_nums else 1
        nro_lote_str = f"{next_lote_num:02d}"
        
        return {
            "NroLote": nro_lote_str,
            "IdManzana": id_mza,
            "UV_MZA": uv_mza_label,
            "TieneAgua": False,
            "IdOrigen": 80000 + next_lote_num
        }

    def assign_codes_for_codigo_fijo(self, lon: float, lat: float) -> Dict[str, Any]:
        """
        Calcula y asigna códigos para un nuevo Código Fijo (punto de servicio/casa):
        - Detecta espacialmente el Lote contenedor (IdLote) y la Manzana.
        - Genera CodFijo correlativo único.
        - Genera CodF_SIG jerárquico (ej: UV.MZA.LOTE.PTO).
        - Asigna coordenadas Lat/Lon y estado inicial.
        """
        parent_lote = self.lm.find_parent_lote_for_point(lon, lat)
        id_lote = parent_lote.id if parent_lote else None
        nro_lote = parent_lote.properties.get("NroLote", "01") if parent_lote else "01"
        
        # Buscar manzana para codificación SIG
        parent_mza = None
        if parent_lote:
            id_mza = parent_lote.properties.get("IdManzana")
            if id_mza is not None:
                parent_mza = self.lm.find_feature("manzanas", id_mza)
        if not parent_mza:
            parent_mza = self.lm.find_parent_manzana_for_point(lon, lat)
            
        uv = parent_mza.properties.get("UV", "105") if parent_mza else "105"
        mza = parent_mza.properties.get("MZA", "01") if parent_mza else "01"
        
        # Correlativo máximo de CodFijo
        cf_layer = self.lm.get_layer("codigosfijos")
        existing_cfs = list(cf_layer.features.values()) if cf_layer else []
        
        cod_fijos = []
        for cf in existing_cfs:
            val = cf.properties.get("CodFijo")
            if isinstance(val, (int, float)):
                cod_fijos.append(int(val))
            elif isinstance(val, str) and val.isdigit():
                cod_fijos.append(int(val))
                
        next_cod_fijo = (max(cod_fijos) + 1) if cod_fijos else 60000
        cod_f_sig = f"{uv}-{mza}-{nro_lote}"
        
        # Si ya existe el lote, marcar que ahora tiene agua
        if parent_lote:
            parent_lote.properties["TieneAgua"] = True
            parent_lote.is_modified = True
            
        return {
            "CodFijo": next_cod_fijo,
            "CodF_SQL": next_cod_fijo,
            "CodF_SIG": cod_f_sig,
            "IdLote": id_lote,
            "Longitud": round(lon, 7),
            "Latitud": round(lat, 7),
            "Estado": 1,                     # 1 = Activo (norma VisorDatosSIG)
            "EstadoVerificado": 1,
            "TieneAgua": True
        }

    def assign_codes_for_via(self, coords: List[List[float]], tipo_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Calcula y asigna códigos para una nueva Vía / Calle:
        - OBJECTID y OSMID únicos.
        - Categorización del tipo de vía.
        """
        vias_layer = self.lm.get_layer("vias")
        existing_vias = list(vias_layer.features.values()) if vias_layer else []
        
        obj_ids = []
        for v in existing_vias:
            oid = v.properties.get("OBJECTID")
            if isinstance(oid, int):
                obj_ids.append(oid)
        next_oid = (max(obj_ids) + 1) if obj_ids else 1000
        
        tipo_via = tipo_hint or "Calle"
        
        return {
            "OBJECTID": next_oid,
            "OSMID": f"v-{next_oid}",
            "TipoVia": tipo_via,
            "highway": "residential" if tipo_via == "Calle" else "primary"
        }
