"""
Extractor y Generador de Datos Contextuales del Mapa.
Extrae nombres de calles, prefijos viales, nombres de propietarios y patrones
DIRECTAMENTE del conjunto de datos y capas activas del mapa en VisorDatosSIG.
"""
import re
import random
from typing import Dict, Any, List, Set, Optional, Tuple
from pathlib import Path
import shapefile
from sig_vector_studio.config import DEFAULT_SHP_DIR

class MapDatasetVocabulary:
    """Extrae y almacena el vocabulario y patrones reales del mapa."""
    def __init__(self):
        self.street_names: List[str] = []
        self.street_prefixes: List[str] = []
        self.street_bases: List[str] = []
        self.person_first_names: List[str] = []
        self.person_surnames: List[str] = []
        self.is_loaded = False

    def load_from_layer_manager_or_shapefiles(self, layer_manager=None):
        """Carga el vocabulario directamente de las capas cargadas o de los shapefiles del proyecto."""
        if self.is_loaded and len(self.street_names) > 0 and len(self.person_surnames) > 0:
            return

        # 1. Extraer nombres y tipos de vías de la capa de vías o del shapefile
        found_vias = False
        if layer_manager:
            via_layer = layer_manager.get_layer("vias")
            if via_layer and via_layer.count() > 0:
                for feat in via_layer.features.values():
                    name = feat.properties.get("Nombre") or feat.properties.get("name")
                    if name and isinstance(name, str) and name.strip():
                        self.street_names.append(name.strip())
                found_vias = True

        if not found_vias:
            vias_shp = DEFAULT_SHP_DIR / "Exp_MapaBase_VIAS_4326.shp"
            if vias_shp.exists():
                try:
                    sf = shapefile.Reader(str(vias_shp), encoding="utf-8")
                    for r in sf.records():
                        name = r["Nombre"] or r["name"]
                        if name and isinstance(name, str) and name.strip():
                            self.street_names.append(name.strip())
                except Exception:
                    pass

        # 2. Descomponer prefijos y nombres base de vías reales del mapa
        prefixes_detected = set()
        bases_detected = set()
        for s in self.street_names:
            parts = s.split(maxsplit=1)
            if len(parts) == 2 and parts[0].lower() in ("avenida", "calle", "pasaje", "camino", "sldo.", "radial", "prolongación", "prolongacion"):
                prefixes_detected.add(parts[0])
                bases_detected.add(parts[1])
            else:
                bases_detected.add(s)

        self.street_prefixes = list(prefixes_detected) if prefixes_detected else ["Calle", "Avenida", "Pasaje", "Camino"]
        self.street_bases = list(bases_detected) if bases_detected else ["24 de Septiembre", "Warnes", "San José Obrero"]

        # 3. Extraer nombres reales de propietarios de la capa CodigosFijos
        found_cfs = False
        raw_owner_names = []
        if layer_manager:
            cf_layer = layer_manager.get_layer("codigosfijos")
            if cf_layer and cf_layer.count() > 0:
                for feat in cf_layer.features.values():
                    n = feat.properties.get("Nombre")
                    if n and isinstance(n, str) and n.strip():
                        raw_owner_names.append(n.strip())
                found_cfs = True

        if not found_cfs:
            cf_shp = DEFAULT_SHP_DIR / "Exp_CodigoFijo_4326.shp"
            if cf_shp.exists():
                try:
                    sf = shapefile.Reader(str(cf_shp), encoding="utf-8")
                    for r in sf.records():
                        n = r["Nombre"]
                        if n and isinstance(n, str) and n.strip():
                            raw_owner_names.append(n.strip())
                except Exception:
                    pass

        # Procesar nombres y apellidos reales del mapa
        fn_set = set()
        sn_set = set()
        for raw in raw_owner_names:
            # Descartar personas jurídicas para nombres individuales (o agregarlas a catálogo)
            if any(term in raw for term in ["ASOCIACION", "DIOCESIS", "IGLESIA", "ALCALDIA", "COLEGIO", "S.R.L.", "S.A."]):
                continue
            words = [w for w in re.split(r"\s+", raw) if len(w) > 2 and w.isalpha()]
            if len(words) >= 3:
                # Estilo catastral: APELLIDO_PATERNO APELLIDO_MATERNO NOMBRES
                sn_set.add(words[0].capitalize())
                sn_set.add(words[1].capitalize())
                fn_set.add(" ".join(w.capitalize() for w in words[2:]))
            elif len(words) == 2:
                sn_set.add(words[0].capitalize())
                fn_set.add(words[1].capitalize())

        self.person_first_names = list(fn_set) if fn_set else ["Carlos Alberto", "María René", "Jorge", "Silvia"]
        self.person_surnames = list(sn_set) if sn_set else ["Limpias", "Duran", "Chuviru", "Mercado", "Justiniano", "Candia"]
        self.is_loaded = True

# Instancia singleton para acceso global
_VOCABULARY = MapDatasetVocabulary()

def get_map_vocabulary(layer_manager=None) -> MapDatasetVocabulary:
    if not _VOCABULARY.is_loaded:
        _VOCABULARY.load_from_layer_manager_or_shapefiles(layer_manager)
    return _VOCABULARY

def generate_street_name_from_map(layer_manager=None) -> Tuple[str, str]:
    """Genera un nombre de vía extraído de la distribución real del mapa."""
    vocab = get_map_vocabulary(layer_manager)
    if vocab.street_names and random.random() < 0.6:
        # Usar directamente una vía existente del mapa
        full_name = random.choice(vocab.street_names)
        tipo = full_name.split()[0] if full_name.split()[0] in vocab.street_prefixes else "Calle"
        return (full_name, tipo)
    
    # Combinar prefijo y base del mapa
    prefix = random.choice(vocab.street_prefixes) if vocab.street_prefixes else "Calle"
    base = random.choice(vocab.street_bases) if vocab.street_bases else "24 de Septiembre"
    return (f"{prefix} {base}", prefix)

def generate_owner_name_from_map(layer_manager=None) -> str:
    """Genera un nombre completo combinando nombres y apellidos extraídos del mapa."""
    vocab = get_map_vocabulary(layer_manager)
    fn = random.choice(vocab.person_first_names) if vocab.person_first_names else "Juan Carlos"
    sn1 = random.choice(vocab.person_surnames) if vocab.person_surnames else "Justiniano"
    sn2 = random.choice(vocab.person_surnames) if vocab.person_surnames else "Mercado"
    return f"{fn} {sn1} {sn2}"

def generate_service_state() -> int:
    """
    1 = Activo (80%)
    2 = Cortado (10%)
    3 = En mora (5%)
    4 = Reconectado (3%)
    5 = Inactivo (2%)
    """
    return random.choices([1, 2, 3, 4, 5], weights=[80, 10, 5, 3, 2])[0]

def enrich_feature_with_mock_data(layer_key: str, existing_props: Dict[str, Any], layer_manager=None) -> Dict[str, Any]:
    """
    Asigna atributos basados en la distribución real del mapa cargado.
    """
    props = dict(existing_props)
    
    if layer_key == "codigosfijos":
        if "Nombre" not in props or not props["Nombre"]:
            props["Nombre"] = generate_owner_name_from_map(layer_manager)
        if "Estado" not in props:
            props["Estado"] = generate_service_state()
        if "EstadoVerificado" not in props:
            props["EstadoVerificado"] = 1
        props["TieneAgua"] = True
        
    elif layer_key == "lotes":
        if "TieneAgua" not in props:
            props["TieneAgua"] = random.choice([True, False])
        if "UsoSuelo" not in props:
            props["UsoSuelo"] = random.choices(["Residencial", "Comercial", "Baldío"], weights=[75, 15, 10])[0]
            
    elif layer_key == "vias":
        if "Nombre" not in props or not props["Nombre"]:
            nombre, tipo = generate_street_name_from_map(layer_manager)
            props["Nombre"] = nombre
            props["TipoVia"] = tipo
            
    return props
