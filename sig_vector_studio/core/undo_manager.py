"""
UndoManager: Gestor de historial de operaciones para Deshacer / Retroceder (Ctrl+Z).
Permite deshacer adiciones, eliminaciones individuales o por sección, y modificaciones geométricas.
"""
import copy
from typing import List, Tuple, Dict, Any, Optional
from sig_vector_studio.core.models import Feature

class UndoAction:
    ADD = "add"
    BATCH_ADD = "batch_add"
    DELETE = "delete"
    BATCH_DELETE = "batch_delete"
    MODIFY = "modify"

    def __init__(self, action_type: str, layer_key: str, data: Any, description: str = ""):
        self.action_type = action_type
        self.layer_key = layer_key
        self.data = data
        self.description = description

class UndoManager:
    def __init__(self, max_history: int = 60):
        self.stack: List[UndoAction] = []
        self.max_history = max_history

    def push(self, action: UndoAction):
        self.stack.append(action)
        if len(self.stack) > self.max_history:
            self.stack.pop(0)

    def push_add(self, layer_key: str, feature_id: int):
        self.push(UndoAction(UndoAction.ADD, layer_key, feature_id, f"Adición de vector #{feature_id}"))

    def push_batch_add(self, layer_key: str, feature_ids: List[int]):
        self.push(UndoAction(UndoAction.BATCH_ADD, layer_key, feature_ids, f"Adición de {len(feature_ids)} vectores"))

    def push_delete(self, layer_key: str, feature: Feature):
        self.push(UndoAction(UndoAction.DELETE, layer_key, feature, f"Eliminación de vector #{feature.id}"))

    def push_batch_delete(self, items: List[Tuple[str, Feature]]):
        self.push(UndoAction(UndoAction.BATCH_DELETE, "multiple", items, f"Eliminación de {len(items)} vectores en sección"))

    def push_modify(self, layer_key: str, feature_id: int, prev_geom_type: str, prev_coords: Any, prev_props: Dict[str, Any]):
        self.push(UndoAction(
            UndoAction.MODIFY, layer_key,
            (feature_id, prev_geom_type, copy.deepcopy(prev_coords), copy.deepcopy(prev_props)),
            f"Modificación de vector #{feature_id}"
        ))

    def can_undo(self) -> bool:
        return len(self.stack) > 0

    def undo(self, layer_manager) -> Tuple[bool, str, List[Tuple[str, str, Any]]]:
        """
        Deshace la última acción y devuelve:
        (éxito, descripción, lista de cambios para sincronizar con Leaflet [(layer_key, action, fid_or_geojson)])
        """
        if not self.stack:
            return False, "No hay acciones para deshacer.", []

        action = self.stack.pop()
        sync_items = []

        if action.action_type == UndoAction.ADD:
            layer = layer_manager.get_layer(action.layer_key)
            fid = action.data
            if layer and fid in layer.features:
                del layer.features[fid]
                sync_items.append((action.layer_key, "remove", fid))
            return True, f"Deshecho: se eliminó el vector #{fid} recién creado.", sync_items

        elif action.action_type == UndoAction.BATCH_ADD:
            layer = layer_manager.get_layer(action.layer_key)
            fids = action.data
            count = 0
            if layer:
                for fid in fids:
                    if fid in layer.features:
                        del layer.features[fid]
                        sync_items.append((action.layer_key, "remove", fid))
                        count += 1
            return True, f"Deshecho: se eliminaron {count} vectores recién creados.", sync_items

        elif action.action_type == UndoAction.DELETE:
            feat = action.data
            layer = layer_manager.get_layer(action.layer_key)
            if layer:
                layer.features[feat.id] = feat
                sync_items.append((action.layer_key, "update", feat.to_geojson_dict()))
            return True, f"Deshecho: se restauró el vector #{feat.id}.", sync_items

        elif action.action_type == UndoAction.BATCH_DELETE:
            items = action.data
            count = 0
            for l_key, feat in items:
                layer = layer_manager.get_layer(l_key)
                if layer:
                    layer.features[feat.id] = feat
                    sync_items.append((l_key, "update", feat.to_geojson_dict()))
                    count += 1
            return True, f"Deshecho: se restauraron {count} vectores eliminados de la sección.", sync_items

        elif action.action_type == UndoAction.MODIFY:
            fid, prev_geom_type, prev_coords, prev_props = action.data
            layer = layer_manager.get_layer(action.layer_key)
            if layer and fid in layer.features:
                feat = layer.features[fid]
                feat.geom_type = prev_geom_type
                feat.coordinates = prev_coords
                feat.properties = prev_props
                sync_items.append((action.layer_key, "update", feat.to_geojson_dict()))
            return True, f"Deshecho: se restauró el estado anterior de #{fid}.", sync_items

        return False, "Tipo de acción desconocido.", []
