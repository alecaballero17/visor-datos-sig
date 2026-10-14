"""
AttributeEditorWidget: Property inspector, attribute editor and code generator for selected features.
Clean vector UI without emojis.
"""
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QGroupBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from sig_vector_studio.core.models import Feature
from sig_vector_studio.generators.code_algorithm import CodeAssignmentAlgorithm
from sig_vector_studio.generators.mock_data_generator import enrich_feature_with_mock_data
from sig_vector_studio.gui.icons import get_svg_icon
from sig_vector_studio.core.layer_manager import LayerManager
from sig_vector_studio.core.db_sync import db_sync

class AttributeEditorWidget(QWidget):
    featureModified = pyqtSignal(str, int)
    featureDeleted = pyqtSignal(str, int)
    zoomRequested = pyqtSignal(object)

    def __init__(self, layer_manager: LayerManager, parent=None):
        super().__init__(parent)
        self.lm = layer_manager
        self.code_algo = CodeAssignmentAlgorithm(layer_manager)
        self.current_feature: Optional[Feature] = None
        self.current_layer_key: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header info
        self.lbl_title = QLabel("Ningún vector seleccionado")
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(self.lbl_title)

        self.lbl_meta = QLabel("Haz clic en un vector en el mapa para inspeccionarlo.")
        self.lbl_meta.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.lbl_meta)

        # Attribute Table
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Campo / Atributo", "Valor"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Quick Actions Group
        action_group = QGroupBox("Herramientas de Codificación y Datos")
        act_layout = QVBoxLayout(action_group)
        act_layout.setSpacing(6)

        self.btn_auto_code = QPushButton("Calcular Código Catastral Automático")
        self.btn_auto_code.setIcon(get_svg_icon("recalc", "#38bdf8"))
        self.btn_auto_code.clicked.connect(self._auto_generate_codes)
        act_layout.addWidget(self.btn_auto_code)

        self.btn_mock_data = QPushButton("Asignar Datos Contextuales del Mapa")
        self.btn_mock_data.setIcon(get_svg_icon("data_generator", "#e2e8f0"))
        self.btn_mock_data.setObjectName("btnSecondary")
        self.btn_mock_data.clicked.connect(self._assign_mock_data)
        act_layout.addWidget(self.btn_mock_data)

        self.btn_zoom = QPushButton("Centrar en este Vector")
        self.btn_zoom.setIcon(get_svg_icon("zoom_all", "#e2e8f0"))
        self.btn_zoom.setObjectName("btnSecondary")
        self.btn_zoom.clicked.connect(self._zoom_to_feature)
        act_layout.addWidget(self.btn_zoom)

        layout.addWidget(action_group)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Guardar Cambios")
        self.btn_save.setIcon(get_svg_icon("save", "#ffffff"))
        self.btn_save.setObjectName("btnSuccess")
        self.btn_save.clicked.connect(self._save_changes)
        btn_layout.addWidget(self.btn_save)

        self.btn_delete = QPushButton("Eliminar")
        self.btn_delete.setIcon(get_svg_icon("delete", "#ffffff"))
        self.btn_delete.setObjectName("btnDanger")
        self.btn_delete.clicked.connect(self._delete_feature)
        btn_layout.addWidget(self.btn_delete)

        layout.addLayout(btn_layout)
        self._set_enabled(False)

    def _set_enabled(self, enabled: bool):
        self.table.setEnabled(enabled)
        self.btn_auto_code.setEnabled(enabled)
        self.btn_mock_data.setEnabled(enabled)
        self.btn_zoom.setEnabled(enabled)
        self.btn_save.setEnabled(enabled)
        self.btn_delete.setEnabled(enabled)

    def load_feature(self, layer_key: str, feature: Feature):
        self.current_layer_key = layer_key
        self.current_feature = feature
        self._set_enabled(True)

        self.lbl_title.setText(f"{layer_key.upper()} · ID: #{feature.id}")
        self.lbl_meta.setText(
            f"Geometría: {feature.geom_type} | "
            f"Estado: {'Nuevo (Sesión)' if feature.is_new else ('Modificado' if feature.is_modified else 'Existente')}"
        )

        props = dict(feature.properties)
        if layer_key == "codigosfijos":
            for k in ["CodFijo", "CodF_SIG", "Nombre", "Estado", "IdLote", "Longitud", "Latitud"]:
                props.setdefault(k, "")
        elif layer_key == "lotes":
            for k in ["NroLote", "IdManzana", "TieneAgua", "IdOrigen"]:
                props.setdefault(k, "")
        elif layer_key == "manzanas":
            for k in ["UV_MZA", "UV", "MZA", "IdOrigen"]:
                props.setdefault(k, "")
        elif layer_key == "vias":
            for k in ["Nombre", "TipoVia", "OBJECTID", "OSMID"]:
                props.setdefault(k, "")

        self.table.setRowCount(0)
        row = 0
        for k, v in props.items():
            if k.startswith("_"):
                continue
            self.table.insertRow(row)
            k_item = QTableWidgetItem(str(k))
            k_item.setFlags(k_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            k_item.setForeground(Qt.GlobalColor.cyan)
            self.table.setItem(row, 0, k_item)
            
            val_str = "" if v is None else str(v)
            v_item = QTableWidgetItem(val_str)
            self.table.setItem(row, 1, v_item)
            row += 1

    def clear(self):
        self.current_feature = None
        self.current_layer_key = None
        self.table.setRowCount(0)
        self.lbl_title.setText("Ningún vector seleccionado")
        self.lbl_meta.setText("Haz clic en un vector en el mapa para inspeccionarlo.")
        self._set_enabled(False)

    def _auto_generate_codes(self):
        if not self.current_feature or not self.current_layer_key:
            return
            
        f = self.current_feature
        key = self.current_layer_key
        
        if key == "manzanas":
            new_props = self.code_algo.assign_codes_for_manzana(f.coordinates)
        elif key == "lotes":
            new_props = self.code_algo.assign_codes_for_lote(f.coordinates)
        elif key == "codigosfijos":
            lon, lat = f.coordinates[0], f.coordinates[1]
            new_props = self.code_algo.assign_codes_for_codigo_fijo(lon, lat)
        elif key == "vias":
            new_props = self.code_algo.assign_codes_for_via(f.coordinates)
        else:
            new_props = {}
            
        f.properties.update(new_props)
        f.is_modified = True
        self.load_feature(key, f)
        self.featureModified.emit(key, f.id)
        QMessageBox.information(self, "Código Asignado", f"Se asignaron automáticamente nuevos códigos para {key}.")

    def _assign_mock_data(self):
        if not self.current_feature or not self.current_layer_key:
            return
        f = self.current_feature
        key = self.current_layer_key
        enriched = enrich_feature_with_mock_data(key, f.properties, layer_manager=self.lm)
        f.properties.update(enriched)
        f.is_modified = True
        self.load_feature(key, f)
        self.featureModified.emit(key, f.id)

    def _zoom_to_feature(self):
        if self.current_feature:
            self.zoomRequested.emit(self.current_feature.bbox)

    def _save_changes(self):
        if not self.current_feature or not self.current_layer_key:
            return
            
        new_props = {}
        for r in range(self.table.rowCount()):
            k = self.table.item(r, 0).text()
            v = self.table.item(r, 1).text()
            if v.isdigit():
                new_props[k] = int(v)
            elif v.lower() in ("true", "false"):
                new_props[k] = (v.lower() == "true")
            else:
                new_props[k] = v
                
        self.current_feature.properties.update(new_props)
        self.current_feature.is_modified = True
        self.featureModified.emit(self.current_layer_key, self.current_feature.id)

        # Sincronización directa en la Base de Datos SQL Server
        ok, msg = db_sync.save_single_feature(self.current_layer_key, self.current_feature)
        if ok:
            QMessageBox.information(
                self,
                "Guardado en Base de Datos",
                f"¡Zas! Cambios guardados directamente en la base de datos SQL Server (VisorDatosSIG).\n\n"
                f"Vector #{self.current_feature.id} sincronizado."
            )
        else:
            QMessageBox.information(
                self,
                "Guardado en Memoria",
                f"Cambios guardados en memoria del mapa.\n(Aviso de Base de Datos: {msg})"
            )

    def _delete_feature(self):
        if not self.current_feature or not self.current_layer_key:
            return
            
        reply = QMessageBox.question(
            self, "Confirmar Eliminación",
            f"¿Deseas eliminar el vector #{self.current_feature.id} de la capa '{self.current_layer_key}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            fid = self.current_feature.id
            key = self.current_layer_key
            layer = self.lm.get_layer(key)
            if layer:
                layer.remove_feature(fid)
            db_sync.delete_feature(key, fid)
            self.clear()
            self.featureDeleted.emit(key, fid)

    def clear(self):
        self.current_feature = None
        self.current_layer_key = None
        self.lbl_title.setText("Ningún vector seleccionado")
        self.lbl_meta.setText("Haz clic en un vector en el mapa para inspeccionarlo.")
        self.table.setRowCount(0)
        self._set_enabled(False)
