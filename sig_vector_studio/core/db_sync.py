"""
Database synchronization and direct injection service for SIG Vector Studio.
Directly injects, updates, and deletes geographic features in SQL Server (VisorDatosSIG)
without requiring manual SQL generation, SSMS copy-pasting, or external scripts.
"""
import subprocess
import tempfile
import os
import re
from typing import Tuple, Optional, Any, Dict, List
from sig_vector_studio.core.models import Feature
from sig_vector_studio.core.geometry import to_wkt

# SQL Server Configuration
DEFAULT_SERVER = r".\SQLSERVER"
DEFAULT_DB = "VisorDatosSIG"
FALLBACK_SERVERS = [r".\SQLSERVER", r"(localdb)\MSSQLLocalDB", "localhost"]

TABLE_CONFIG = {
    "manzanas": {
        "table": "dbo.Manzanas",
        "id_col": "IdManzana"
    },
    "lotes": {
        "table": "dbo.Lotes",
        "id_col": "IdLote"
    },
    "codigosfijos": {
        "table": "dbo.CodigosFijos",
        "id_col": "IdCodigo"
    },
    "vias": {
        "table": "dbo.Vias",
        "id_col": "IdVia"
    }
}

def escape_sql_string(val: Any) -> str:
    if val is None:
        return "NULL"
    s = str(val).strip()
    if not s or s.upper() == "NULL":
        return "NULL"
    escaped = s.replace("'", "''")
    return f"N'{escaped}'"

def sql_int_or_null(val: Any) -> str:
    if val is None:
        return "NULL"
    s = str(val).strip()
    if not s or s.upper() == "NULL":
        return "NULL"
    try:
        return str(int(float(s)))
    except Exception:
        return "NULL"

def sql_float_or_null(val: Any) -> str:
    if val is None:
        return "NULL"
    s = str(val).strip()
    if not s or s.upper() == "NULL":
        return "NULL"
    try:
        return f"{float(s):.7f}"
    except Exception:
        return "NULL"

def make_geography_expr(geom_type: str, wkt: str) -> str:
    """Genera la expresión SQL segura para insertar/actualizar tipo geography con orientación adecuada."""
    if geom_type.lower() in ("polygon", "multipolygon"):
        return (
            f"(SELECT CASE WHEN g.EnvelopeAngle() > 90 THEN g.ReorientObject() ELSE g END "
            f"FROM (SELECT geography::STGeomFromText('{wkt}', 4326).MakeValid() AS g) t)"
        )
    return f"geography::STGeomFromText('{wkt}', 4326).MakeValid()"

def make_safe_id_mza_expr(id_mza_val: Any, geom_expr: str) -> str:
    """
    Garantiza que IdManzana no viole la FK FK_Lotes_Manzanas_IdManzana.
    Verifica si existe en dbo.Manzanas, o lo infiere por intersección espacial, o asigna NULL.
    """
    val = sql_int_or_null(id_mza_val)
    if val != "NULL":
        return (
            f"COALESCE("
            f"(SELECT IdManzana FROM dbo.Manzanas WHERE IdManzana = {val}), "
            f"(SELECT TOP 1 m.IdManzana FROM dbo.Manzanas m WHERE m.Geom.STIntersects({geom_expr}.STPointN(1)) = 1), "
            f"NULL)"
        )
    return f"(SELECT TOP 1 m.IdManzana FROM dbo.Manzanas m WHERE m.Geom.STIntersects({geom_expr}.STPointN(1)) = 1)"

def make_safe_id_lote_expr(id_lote_val: Any, geom_expr: str) -> str:
    """
    Garantiza que IdLote no viole la FK FK_CodigosFijos_Lotes_IdLote.
    Verifica si existe en dbo.Lotes, o lo infiere por intersección espacial, o asigna NULL.
    """
    val = sql_int_or_null(id_lote_val)
    if val != "NULL":
        return (
            f"COALESCE("
            f"(SELECT IdLote FROM dbo.Lotes WHERE IdLote = {val}), "
            f"(SELECT TOP 1 l.IdLote FROM dbo.Lotes l WHERE l.Geom.STIntersects({geom_expr}) = 1), "
            f"NULL)"
        )
    return f"(SELECT TOP 1 l.IdLote FROM dbo.Lotes l WHERE l.Geom.STIntersects({geom_expr}) = 1)"

class DatabaseSyncService:
    def __init__(self, server: str = DEFAULT_SERVER, database: str = DEFAULT_DB):
        self.server = server
        self.database = database
        self._active_server: Optional[str] = None

    def get_active_server(self) -> str:
        if self._active_server:
            return self._active_server

        for srv in [self.server] + FALLBACK_SERVERS:
            try:
                cmd = ["sqlcmd", "-S", srv, "-C", "-d", self.database, "-Q", "SELECT 1", "-t", "3"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    self._active_server = srv
                    return srv
            except Exception:
                pass
        self._active_server = self.server
        return self._active_server

    def test_connection(self) -> Tuple[bool, str]:
        srv = self.get_active_server()
        try:
            cmd = ["sqlcmd", "-S", srv, "-C", "-d", self.database, "-Q", "SELECT DB_NAME(), COUNT(*) FROM dbo.Manzanas;", "-t", "5"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            if res.returncode == 0:
                return True, f"Conexión exitosa a SQL Server ({srv} -> {self.database})"
            return False, f"Error conectando a SQL Server ({srv}): {res.stderr or res.stdout}"
        except Exception as e:
            return False, f"No se pudo ejecutar sqlcmd: {e}"

    def execute_sql(self, sql_content: str) -> Tuple[bool, str]:
        """Ejecuta un script SQL directamente en SQL Server mediante sqlcmd con las opciones de índice espacial."""
        srv = self.get_active_server()
        
        with tempfile.NamedTemporaryFile("w", suffix=".sql", encoding="utf-8", delete=False) as tmp:
            tmp_path = tmp.name
            full_sql = (
                "SET QUOTED_IDENTIFIER ON;\n"
                "SET ANSI_NULLS ON;\n"
                "SET NOCOUNT ON;\n"
                f"{sql_content}"
            )
            tmp.write(full_sql)

        try:
            cmd = [
                "sqlcmd",
                "-S", srv,
                "-C",
                "-d", self.database,
                "-i", tmp_path,
                "-b",
                "-t", "40"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=50)
            if res.returncode == 0:
                output = res.stdout.strip()
                return True, output or "Operación completada exitosamente en la base de datos."
            else:
                err_msg = res.stderr.strip() or res.stdout.strip()
                return False, f"Error SQL: {err_msg}"
        except Exception as e:
            return False, f"Excepción de base de datos: {e}"
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def insert_feature(self, layer_key: str, feat: Feature) -> Tuple[bool, str, Optional[int]]:
        """Inyecta un nuevo vector geográfico directamente en la tabla correspondiente y devuelve su ID generado."""
        wkt = feat.wkt
        if not wkt:
            return False, "Geometría vacía o inválida.", None

        props = feat.properties
        geom_expr = make_geography_expr(feat.geom_type, wkt)

        if layer_key == "manzanas":
            id_orig = sql_int_or_null(props.get("IdOrigen"))
            uv_mza = escape_sql_string(props.get("UV_MZA"))
            uv = escape_sql_string(props.get("UV"))
            mza = escape_sql_string(props.get("MZA"))
            sql = f"""
            INSERT INTO dbo.Manzanas (IdOrigen, UV_MZA, UV, MZA, Geom)
            VALUES ({id_orig}, {uv_mza}, {uv}, {mza}, {geom_expr});
            SELECT SCOPE_IDENTITY() AS NewId;
            """

        elif layer_key == "lotes":
            id_orig = sql_int_or_null(props.get("IdOrigen"))
            nro_lote = escape_sql_string(props.get("NroLote"))
            safe_id_mza = make_safe_id_mza_expr(props.get("IdManzana"), geom_expr)
            sql = f"""
            INSERT INTO dbo.Lotes (IdOrigen, NroLote, IdManzana, Geom)
            VALUES ({id_orig}, {nro_lote}, {safe_id_mza}, {geom_expr});
            SELECT SCOPE_IDENTITY() AS NewId;
            """

        elif layer_key == "codigosfijos":
            cod_f_sql = sql_int_or_null(props.get("CodF_SQL"))
            cod_f_sig = escape_sql_string(props.get("CodF_SIG"))
            cod_fijo = sql_int_or_null(props.get("CodFijo"))
            nombre = escape_sql_string(props.get("Nombre", "Propietario"))
            estado = sql_int_or_null(props.get("Estado", 1))
            lon = sql_float_or_null(props.get("Longitud", feat.coordinates[0]))
            lat = sql_float_or_null(props.get("Latitud", feat.coordinates[1]))
            safe_id_lote = make_safe_id_lote_expr(props.get("IdLote"), geom_expr)
            sql = f"""
            INSERT INTO dbo.CodigosFijos (CodF_SQL, CodF_SIG, CodFijo, Nombre, Estado, FechaCambioEstado, IdLote, Longitud, Latitud, Geom)
            VALUES ({cod_f_sql}, {cod_f_sig}, {cod_fijo}, {nombre}, {estado}, SYSDATETIME(), {safe_id_lote}, {lon}, {lat}, {geom_expr});
            SELECT SCOPE_IDENTITY() AS NewId;
            """

        elif layer_key == "vias":
            obj_id = sql_int_or_null(props.get("OBJECTID"))
            nombre = escape_sql_string(props.get("Nombre", "Calle S/N"))
            tipo_via = escape_sql_string(props.get("TipoVia", "Calle"))
            osmid = escape_sql_string(props.get("OSMID", ""))
            sql = f"""
            INSERT INTO dbo.Vias (OBJECTID, Nombre, TipoVia, OSMID, Geom)
            VALUES ({obj_id}, {nombre}, {tipo_via}, {osmid}, {geom_expr});
            SELECT SCOPE_IDENTITY() AS NewId;
            """
        else:
            return False, f"Capa no reconocida: {layer_key}", None

        ok, out = self.execute_sql(sql)
        new_id = None
        if ok:
            feat.is_new = False
            feat.is_modified = False
            digits = re.findall(r"\b(\d+)\b", out)
            if digits:
                try:
                    new_id = int(digits[-1])
                    if layer_key == "manzanas":
                        feat.properties["IdManzana"] = new_id
                    elif layer_key == "lotes":
                        feat.properties["IdLote"] = new_id
                    elif layer_key == "codigosfijos":
                        feat.properties["IdCodigo"] = new_id
                    elif layer_key == "vias":
                        feat.properties["IdVia"] = new_id
                except Exception:
                    pass

        return ok, out, new_id

    def update_feature_properties(self, layer_key: str, feat: Feature) -> Tuple[bool, str]:
        """Actualiza atributos y geometría de un vector existente directamente en la base de datos."""
        wkt = feat.wkt
        props = feat.properties
        geom_expr = make_geography_expr(feat.geom_type, wkt)

        if layer_key == "manzanas":
            id_mza = sql_int_or_null(props.get("IdManzana") or feat.id)
            uv_mza = escape_sql_string(props.get("UV_MZA"))
            uv = escape_sql_string(props.get("UV"))
            mza = escape_sql_string(props.get("MZA"))
            id_orig = sql_int_or_null(props.get("IdOrigen"))
            sql = f"""
            UPDATE dbo.Manzanas
               SET UV_MZA = {uv_mza}, UV = {uv}, MZA = {mza}, IdOrigen = {id_orig},
                   Geom = {geom_expr}
             WHERE IdManzana = {id_mza};
            """

        elif layer_key == "lotes":
            id_lote = sql_int_or_null(props.get("IdLote") or feat.id)
            id_orig = sql_int_or_null(props.get("IdOrigen"))
            nro_lote = escape_sql_string(props.get("NroLote"))
            safe_id_mza = make_safe_id_mza_expr(props.get("IdManzana"), geom_expr)
            sql = f"""
            UPDATE dbo.Lotes
               SET IdOrigen = {id_orig}, NroLote = {nro_lote}, IdManzana = {safe_id_mza},
                   Geom = {geom_expr}
             WHERE IdLote = {id_lote};
            """

        elif layer_key == "codigosfijos":
            id_cod = sql_int_or_null(props.get("IdCodigo") or feat.id)
            cod_f_sql = sql_int_or_null(props.get("CodF_SQL"))
            cod_f_sig = escape_sql_string(props.get("CodF_SIG"))
            cod_fijo = sql_int_or_null(props.get("CodFijo"))
            nombre = escape_sql_string(props.get("Nombre", "Propietario"))
            estado = sql_int_or_null(props.get("Estado", 1))
            lon = sql_float_or_null(props.get("Longitud", feat.coordinates[0]))
            lat = sql_float_or_null(props.get("Latitud", feat.coordinates[1]))
            safe_id_lote = make_safe_id_lote_expr(props.get("IdLote"), geom_expr)
            sql = f"""
            UPDATE dbo.CodigosFijos
               SET CodF_SQL = {cod_f_sql}, CodF_SIG = {cod_f_sig}, CodFijo = {cod_fijo},
                   Nombre = {nombre}, Estado = {estado}, IdLote = {safe_id_lote},
                   Longitud = {lon}, Latitud = {lat},
                   Geom = {geom_expr},
                   FechaCambioEstado = SYSDATETIME()
             WHERE IdCodigo = {id_cod};
            """

        elif layer_key == "vias":
            id_via = sql_int_or_null(props.get("IdVia") or feat.id)
            obj_id = sql_int_or_null(props.get("OBJECTID"))
            nombre = escape_sql_string(props.get("Nombre", "Calle S/N"))
            tipo_via = escape_sql_string(props.get("TipoVia", "Calle"))
            osmid = escape_sql_string(props.get("OSMID", ""))
            sql = f"""
            UPDATE dbo.Vias
               SET OBJECTID = {obj_id}, Nombre = {nombre}, TipoVia = {tipo_via}, OSMID = {osmid},
                   Geom = {geom_expr}
             WHERE IdVia = {id_via};
            """
        else:
            return False, f"Capa desconocida: {layer_key}"

        ok, out = self.execute_sql(sql)
        if ok:
            feat.is_modified = False
        return ok, out

    def save_single_feature(self, layer_key: str, feat: Feature) -> Tuple[bool, str]:
        """Guarda un vector individual insertándolo si es nuevo o actualizándolo si ya existe."""
        if getattr(feat, "is_new", False):
            ok, out, new_id = self.insert_feature(layer_key, feat)
            return ok, out
        return self.update_feature_properties(layer_key, feat)

    def update_feature_geometry(self, layer_key: str, feature_id: int, geom_type: str, coords: Any) -> Tuple[bool, str]:
        """Actualiza instantáneamente la columna Geom de un vector en SQL Server cuando se mueven vértices."""
        wkt = to_wkt(geom_type, coords)
        if not wkt:
            return False, "WKT inválido"

        conf = TABLE_CONFIG.get(layer_key)
        if not conf:
            return False, f"Capa no configurada: {layer_key}"

        table = conf["table"]
        id_col = conf["id_col"]
        geom_expr = make_geography_expr(geom_type, wkt)

        extra_set = ""
        if layer_key == "codigosfijos" and geom_type == "Point" and len(coords) >= 2:
            lon_f = sql_float_or_null(coords[0])
            lat_f = sql_float_or_null(coords[1])
            extra_set = f", Longitud = {lon_f}, Latitud = {lat_f}"

        sql = f"""
        UPDATE {table}
           SET Geom = {geom_expr}{extra_set}
         WHERE {id_col} = {feature_id};
        """
        return self.execute_sql(sql)

    def delete_feature(self, layer_key: str, feature_id: int) -> Tuple[bool, str]:
        """Elimina instantáneamente un vector de la base de datos SQL Server."""
        conf = TABLE_CONFIG.get(layer_key)
        if not conf:
            return False, f"Capa no configurada: {layer_key}"

        table = conf["table"]
        id_col = conf["id_col"]

        sql = f"DELETE FROM {table} WHERE {id_col} = {feature_id};"
        return self.execute_sql(sql)

    def delete_features_batch(self, items: List[Tuple[str, int]]) -> Tuple[bool, str]:
        """Elimina un lote de vectores agrupados por capa."""
        by_layer: Dict[str, List[int]] = {}
        for l_key, fid in items:
            by_layer.setdefault(l_key, []).append(fid)

        lines = ["BEGIN TRANSACTION;", "BEGIN TRY"]
        for l_key, ids in by_layer.items():
            conf = TABLE_CONFIG.get(l_key)
            if not conf:
                continue
            table = conf["table"]
            id_col = conf["id_col"]
            id_list = ",".join(str(i) for i in ids)
            lines.append(f"DELETE FROM {table} WHERE {id_col} IN ({id_list});")

        lines.extend([
            "COMMIT TRANSACTION;",
            "END TRY",
            "BEGIN CATCH",
            "    ROLLBACK TRANSACTION;",
            "    DECLARE @ErrMsg NVARCHAR(4000) = ERROR_MESSAGE();",
            "    RAISERROR(@ErrMsg, 16, 1);",
            "END CATCH;"
        ])
        return self.execute_sql("\n".join(lines))

    def inject_batch(self, items_by_layer: Dict[str, List[Dict[str, Any]]]) -> Tuple[bool, str, int]:
        """
        Inyecta masivamente lotes, manzanas, vías y códigos fijos directamente en VisorDatosSIG
        dentro de una transacción segura y recalcula relaciones espaciales al terminar.
        """
        lines = [
            "BEGIN TRANSACTION;",
            "BEGIN TRY"
        ]
        total_count = 0

        # 1. Manzanas
        for item in items_by_layer.get("manzanas", []):
            coords = item.get("coordinates", [])
            wkt = to_wkt("Polygon", coords)
            if not wkt:
                continue
            props = item.get("properties", {})
            id_orig = sql_int_or_null(props.get("IdOrigen"))
            uv_mza = escape_sql_string(props.get("UV_MZA"))
            uv = escape_sql_string(props.get("UV"))
            mza = escape_sql_string(props.get("MZA"))
            geom_expr = make_geography_expr("Polygon", wkt)
            lines.append(
                f"INSERT INTO dbo.Manzanas (IdOrigen, UV_MZA, UV, MZA, Geom) "
                f"VALUES ({id_orig}, {uv_mza}, {uv}, {mza}, {geom_expr});"
            )
            total_count += 1

        # 2. Lotes
        for item in items_by_layer.get("lotes", []):
            coords = item.get("coordinates", [])
            wkt = to_wkt("Polygon", coords)
            if not wkt:
                continue
            props = item.get("properties", {})
            id_orig = sql_int_or_null(props.get("IdOrigen"))
            nro_lote = escape_sql_string(props.get("NroLote"))
            geom_expr = make_geography_expr("Polygon", wkt)
            safe_id_mza = make_safe_id_mza_expr(props.get("IdManzana"), geom_expr)
            lines.append(
                f"INSERT INTO dbo.Lotes (IdOrigen, NroLote, IdManzana, Geom) "
                f"VALUES ({id_orig}, {nro_lote}, {safe_id_mza}, {geom_expr});"
            )
            total_count += 1

        # 3. Vías
        for item in items_by_layer.get("vias", []):
            coords = item.get("coordinates", [])
            wkt = to_wkt("LineString", coords)
            if not wkt:
                continue
            props = item.get("properties", {})
            obj_id = sql_int_or_null(props.get("OBJECTID"))
            nombre = escape_sql_string(props.get("Nombre", "Calle S/N"))
            tipo_via = escape_sql_string(props.get("TipoVia", "Calle"))
            osmid = escape_sql_string(props.get("OSMID", ""))
            geom_expr = make_geography_expr("LineString", wkt)
            lines.append(
                f"INSERT INTO dbo.Vias (OBJECTID, Nombre, TipoVia, OSMID, Geom) "
                f"VALUES ({obj_id}, {nombre}, {tipo_via}, {osmid}, {geom_expr});"
            )
            total_count += 1

        # 4. Códigos Fijos
        for item in items_by_layer.get("codigosfijos", []):
            coords = item.get("coordinates", [])
            wkt = to_wkt("Point", coords)
            if not wkt:
                continue
            props = item.get("properties", {})
            cod_f_sql = sql_int_or_null(props.get("CodF_SQL"))
            cod_f_sig = escape_sql_string(props.get("CodF_SIG"))
            cod_fijo = sql_int_or_null(props.get("CodFijo"))
            nombre = escape_sql_string(props.get("Nombre", "Propietario"))
            estado = sql_int_or_null(props.get("Estado", 1))
            lon = sql_float_or_null(coords[0] if len(coords) > 0 else None)
            lat = sql_float_or_null(coords[1] if len(coords) > 1 else None)
            geom_expr = make_geography_expr("Point", wkt)
            safe_id_lote = make_safe_id_lote_expr(props.get("IdLote"), geom_expr)
            lines.append(
                f"INSERT INTO dbo.CodigosFijos (CodF_SQL, CodF_SIG, CodFijo, Nombre, Estado, FechaCambioEstado, IdLote, Longitud, Latitud, Geom) "
                f"VALUES ({cod_f_sql}, {cod_f_sig}, {cod_fijo}, {nombre}, {estado}, SYSDATETIME(), {safe_id_lote}, {lon}, {lat}, {geom_expr});"
            )
            total_count += 1

        if total_count == 0:
            return True, "No se seleccionaron elementos para inyectar.", 0

        lines.extend([
            "COMMIT TRANSACTION;",
            f"PRINT 'Inyección masiva completada: {total_count} registros inyectados';",
            "END TRY",
            "BEGIN CATCH",
            "    ROLLBACK TRANSACTION;",
            "    DECLARE @ErrMsg NVARCHAR(4000) = ERROR_MESSAGE();",
            "    RAISERROR(@ErrMsg, 16, 1);",
            "END CATCH;"
        ])

        sql_script = "\n".join(lines)
        ok, out = self.execute_sql(sql_script)
        return ok, out, total_count

    def inject_layer_manager(self, layer_manager: Any, only_new_or_modified: bool = True) -> Tuple[bool, str, int]:
        """Inyecta directamente todos los vectores nuevos o modificados presentes en el gestor de capas."""
        items_by_layer: Dict[str, List[Dict[str, Any]]] = {}
        total_candidates = 0

        for key in ["manzanas", "lotes", "vias", "codigosfijos"]:
            layer = layer_manager.get_layer(key)
            if not layer:
                continue
            items_by_layer[key] = []
            for feat in layer.features.values():
                if not only_new_or_modified or feat.is_new or feat.is_modified:
                    items_by_layer[key].append({
                        "coordinates": feat.coordinates,
                        "properties": feat.properties,
                        "geom_type": feat.geom_type
                    })
                    total_candidates += 1

        if total_candidates == 0:
            return True, "No hay vectores nuevos ni modificados pendientes de inyectar.", 0

        ok, out, count = self.inject_batch(items_by_layer)
        if ok:
            for layer in layer_manager.layers.values():
                for feat in layer.features.values():
                    feat.is_new = False
                    feat.is_modified = False
        return ok, out, count

    def load_layers_from_database(self, layer_manager: Any, max_per_layer: int = 5000) -> Tuple[bool, Dict[str, int], str]:
        """
        Carga las capas cartográficas directamente desde SQL Server (VisorDatosSIG) hacia LayerManager.
        Preserva los IDs reales de la base de datos, las geometrías y los atributos de la plataforma.
        """
        from sig_vector_studio.core.geometry import from_wkt
        srv = self.get_active_server()
        stats = {"manzanas": 0, "vias": 0, "lotes": 0, "codigosfijos": 0}

        # 1. Manzanas
        try:
            cmd_mza = [
                "sqlcmd", "-S", srv, "-C", "-d", self.database, "-y", "0",
                "-Q", f"SET NOCOUNT ON; SELECT TOP {max_per_layer} IdManzana, ISNULL(UV_MZA,''), ISNULL(UV,''), ISNULL(MZA,''), ISNULL(IdOrigen,0), Geom.STAsText() FROM dbo.Manzanas WHERE Geom IS NOT NULL ORDER BY IdManzana ASC;",
                "-s", "\t"
            ]
            res_mza = subprocess.run(cmd_mza, capture_output=True, text=True, timeout=25)
            if res_mza.returncode == 0:
                layer_mza = layer_manager.get_layer("manzanas")
                if layer_mza:
                    layer_mza.features.clear()
                    data_lines = [l for l in res_mza.stdout.splitlines() if l and not l.startswith("IdManzana") and not l.startswith("---")]
                    for line in data_lines:
                        parts = line.split("\t")
                        if len(parts) >= 6:
                            try:
                                fid = int(parts[0].strip())
                                uv_mza = parts[1].strip()
                                uv = parts[2].strip()
                                mza = parts[3].strip()
                                id_orig = int(parts[4].strip())
                                wkt_str = parts[5].strip()
                                g_type, coords = from_wkt(wkt_str)
                                if g_type and coords:
                                    layer_mza.add_feature(g_type, coords, {
                                        "IdManzana": fid, "UV_MZA": uv_mza, "UV": uv, "MZA": mza, "IdOrigen": id_orig
                                    }, feature_id=fid, is_new=False)
                                    stats["manzanas"] += 1
                            except Exception:
                                pass
        except Exception:
            pass

        # 2. Vías
        try:
            cmd_via = [
                "sqlcmd", "-S", srv, "-C", "-d", self.database, "-y", "0",
                "-Q", f"SET NOCOUNT ON; SELECT TOP {max_per_layer} IdVia, ISNULL(OBJECTID,0), ISNULL(Nombre,''), ISNULL(TipoVia,''), ISNULL(OSMID,''), Geom.STAsText() FROM dbo.Vias WHERE Geom IS NOT NULL ORDER BY IdVia ASC;",
                "-s", "\t"
            ]
            res_via = subprocess.run(cmd_via, capture_output=True, text=True, timeout=25)
            if res_via.returncode == 0:
                layer_via = layer_manager.get_layer("vias")
                if layer_via:
                    layer_via.features.clear()
                    data_lines = [l for l in res_via.stdout.splitlines() if l and not l.startswith("IdVia") and not l.startswith("---")]
                    for line in data_lines:
                        parts = line.split("\t")
                        if len(parts) >= 6:
                            try:
                                fid = int(parts[0].strip())
                                obj_id = int(parts[1].strip())
                                nom = parts[2].strip()
                                tipo = parts[3].strip()
                                osmid = parts[4].strip()
                                wkt_str = parts[5].strip()
                                g_type, coords = from_wkt(wkt_str)
                                if g_type and coords:
                                    layer_via.add_feature(g_type, coords, {
                                        "IdVia": fid, "OBJECTID": obj_id, "Nombre": nom, "TipoVia": tipo, "OSMID": osmid
                                    }, feature_id=fid, is_new=False)
                                    stats["vias"] += 1
                            except Exception:
                                pass
        except Exception:
            pass

        # 3. Lotes
        try:
            cmd_lote = [
                "sqlcmd", "-S", srv, "-C", "-d", self.database, "-y", "0",
                "-Q", f"SET NOCOUNT ON; SELECT TOP {max_per_layer} IdLote, ISNULL(IdOrigen,0), ISNULL(NroLote,''), ISNULL(IdManzana,0), Geom.STAsText() FROM dbo.Lotes WHERE Geom IS NOT NULL ORDER BY IdLote DESC;",
                "-s", "\t"
            ]
            res_lote = subprocess.run(cmd_lote, capture_output=True, text=True, timeout=35)
            if res_lote.returncode == 0:
                layer_lote = layer_manager.get_layer("lotes")
                if layer_lote:
                    layer_lote.features.clear()
                    data_lines = [l for l in res_lote.stdout.splitlines() if l and not l.startswith("IdLote") and not l.startswith("---")]
                    for line in data_lines:
                        parts = line.split("\t")
                        if len(parts) >= 5:
                            try:
                                fid = int(parts[0].strip())
                                id_orig = int(parts[1].strip())
                                nro = parts[2].strip()
                                id_mza = int(parts[3].strip())
                                wkt_str = parts[4].strip()
                                g_type, coords = from_wkt(wkt_str)
                                if g_type and coords:
                                    layer_lote.add_feature(g_type, coords, {
                                        "IdLote": fid, "IdOrigen": id_orig, "NroLote": nro, "IdManzana": id_mza
                                    }, feature_id=fid, is_new=False)
                                    stats["lotes"] += 1
                            except Exception:
                                pass
        except Exception:
            pass

        # 4. Códigos Fijos
        try:
            cmd_cf = [
                "sqlcmd", "-S", srv, "-C", "-d", self.database, "-y", "0",
                "-Q", f"SET NOCOUNT ON; SELECT TOP {max_per_layer} IdCodigo, ISNULL(CodF_SQL,0), ISNULL(CodF_SIG,''), ISNULL(CodFijo,0), ISNULL(Nombre,''), ISNULL(Estado,1), ISNULL(IdLote,0), ISNULL(Longitud,0.0), ISNULL(Latitud,0.0), Geom.STAsText() FROM dbo.CodigosFijos WHERE Geom IS NOT NULL ORDER BY IdCodigo DESC;",
                "-s", "\t"
            ]
            res_cf = subprocess.run(cmd_cf, capture_output=True, text=True, timeout=30)
            if res_cf.returncode == 0:
                layer_cf = layer_manager.get_layer("codigosfijos")
                if layer_cf:
                    layer_cf.features.clear()
                    data_lines = [l for l in res_cf.stdout.splitlines() if l and not l.startswith("IdCodigo") and not l.startswith("---")]
                    for line in data_lines:
                        parts = line.split("\t")
                        if len(parts) >= 10:
                            try:
                                fid = int(parts[0].strip())
                                c_sql = int(parts[1].strip())
                                c_sig = parts[2].strip()
                                c_fijo = int(parts[3].strip())
                                nom = parts[4].strip()
                                est = int(parts[5].strip())
                                id_lt = int(parts[6].strip())
                                lon_raw = parts[7].strip()
                                lat_raw = parts[8].strip()
                                lon = float(lon_raw) if lon_raw and lon_raw.upper() != "NULL" else None
                                lat = float(lat_raw) if lat_raw and lat_raw.upper() != "NULL" else None
                                wkt_str = parts[9].strip()
                                g_type, coords = from_wkt(wkt_str)
                                if g_type and coords:
                                    layer_cf.add_feature(g_type, coords, {
                                        "IdCodigo": fid, "CodF_SQL": c_sql, "CodF_SIG": c_sig, "CodFijo": c_fijo,
                                        "Nombre": nom, "Estado": est, "IdLote": id_lt, "Longitud": lon, "Latitud": lat
                                    }, feature_id=fid, is_new=False)
                                    stats["codigosfijos"] += 1
                            except Exception:
                                pass
        except Exception:
            pass

        total = sum(stats.values())
        if total > 0:
            return True, stats, f"Cargados {total} vectores directamente desde SQL Server ({srv} -> {self.database})"
        return False, stats, "No se encontraron vectores en la base de datos."

# Instancia global del servicio
db_sync = DatabaseSyncService()

