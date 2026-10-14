"""
MainWindow: Core graphical interface for SIG Vector Studio.
Uses clean SVG vector icons and extracts vocabularies directly from the map.
"""
import json
import time
from typing import Optional, Dict, Any, Tuple
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QToolBar,
    QDockWidget, QTreeWidget, QTreeWidgetItem, QPushButton,
    QLabel, QComboBox, QMessageBox, QFileDialog, QStatusBar
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QAction, QColor, QKeySequence

from sig_vector_studio.core.layer_manager import LayerManager
from sig_vector_studio.core.undo_manager import UndoManager
from sig_vector_studio.gui.map_widget import MapWidget
from sig_vector_studio.gui.attribute_editor import AttributeEditorWidget
from sig_vector_studio.gui.cv_dialog import CVVectorizeDialog
from sig_vector_studio.gui.export_dialog import ExportDialog
from sig_vector_studio.gui.icons import get_svg_icon
from sig_vector_studio.generators.code_algorithm import CodeAssignmentAlgorithm
from sig_vector_studio.generators.mock_data_generator import enrich_feature_with_mock_data
from sig_vector_studio.generators.subdivision import subdivide_manzana_into_lots
from sig_vector_studio.core.db_sync import db_sync
from sig_vector_studio.exporters.sql_exporter import generate_sql_migration
from sig_vector_studio.config import LAYER_CONFIG, DEFAULT_SHP_DIR

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SIG Vector Studio - Editor Cartográfico y Vectorizador")
        self.resize(1380, 850)
        
        self.lm = LayerManager()
        self.undo_mgr = UndoManager()
        self.code_algo = CodeAssignmentAlgorithm(self.lm)
        
        self._init_ui()
        self._connect_signals()
        # Pre-load data from SQL Server database (or fallback to shapefiles) immediately
        self._load_initial_data()

    def _init_ui(self):
        # 1. Central Map Widget
        self.map_widget = MapWidget(self)
        self.setCentralWidget(self.map_widget)

        # 2. Main Action ToolBar with SVG icons
        self.toolbar = QToolBar("Herramientas de Edición")
        self.toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        self._build_toolbar()

        # 3. Left Dock: Layers Tree & Base Maps
        self._build_layers_dock()

        # 4. Right Dock: Feature Inspector & Attribute Editor
        self._build_inspector_dock()

        # 5. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_status_coords = QLabel("Lat: --, Lon: --")
        self.lbl_status_mode = QLabel("Modo: Exploración")
        self.status_bar.addPermanentWidget(self.lbl_status_mode)
        self.status_bar.addPermanentWidget(self.lbl_status_coords)
        self.status_bar.showMessage("Listo. Iniciando entorno geoespacial...", 4000)

    def _build_toolbar(self):
        # Navigation & History
        self.act_nav = QAction(get_svg_icon("navigate", "#38bdf8"), "Navegar / Seleccionar", self)
        self.act_nav.setCheckable(True)
        self.act_nav.setChecked(True)
        self.act_nav.triggered.connect(lambda: self._set_mode("navigate"))
        self.toolbar.addAction(self.act_nav)

        self.act_undo = QAction(get_svg_icon("undo", "#38bdf8"), "Deshacer (Ctrl+Z)", self)
        self.act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.act_undo.triggered.connect(self._on_undo)
        self.toolbar.addAction(self.act_undo)

        self.act_delete = QAction(get_svg_icon("delete", "#ef4444"), "Eliminar Seleccionado (Supr)", self)
        self.act_delete.setShortcut(QKeySequence.StandardKey.Delete)
        self.act_delete.triggered.connect(self._delete_selected_feature)
        self.toolbar.addAction(self.act_delete)

        self.act_del_box = QAction(get_svg_icon("delete", "#f43f5e"), "Eliminar Sección por Cuadro", self)
        self.act_del_box.setCheckable(True)
        self.act_del_box.triggered.connect(lambda: self._set_mode("delete_box"))
        self.toolbar.addAction(self.act_del_box)

        self.toolbar.addSeparator()

        # Vector Drawing Tools
        self.act_draw_lote = QAction(get_svg_icon("draw_polygon", "#38bdf8"), "Dibujar Lote / Terreno", self)
        self.act_draw_lote.setCheckable(True)
        self.act_draw_lote.triggered.connect(lambda: self._set_mode("draw_polygon", "lotes"))
        self.toolbar.addAction(self.act_draw_lote)

        self.act_draw_mza = QAction(get_svg_icon("draw_manzana", "#ef4444"), "Dibujar Manzana", self)
        self.act_draw_mza.setCheckable(True)
        self.act_draw_mza.triggered.connect(lambda: self._set_mode("draw_polygon", "manzanas"))
        self.toolbar.addAction(self.act_draw_mza)

        self.act_draw_point = QAction(get_svg_icon("draw_point", "#f59e0b"), "Agregar Código Fijo / Casa", self)
        self.act_draw_point.setCheckable(True)
        self.act_draw_point.triggered.connect(lambda: self._set_mode("draw_point", "codigosfijos"))
        self.toolbar.addAction(self.act_draw_point)

        self.act_draw_via = QAction(get_svg_icon("draw_via", "#a855f7"), "Dibujar Vía / Calle", self)
        self.act_draw_via.setCheckable(True)
        self.act_draw_via.triggered.connect(lambda: self._set_mode("draw_line", "vias"))
        self.toolbar.addAction(self.act_draw_via)

        self.toolbar.addSeparator()

        # Computer Vision AI Vectorization (Cuadro y Puntos)
        self.act_cv = QAction(get_svg_icon("satellite_ai", "#10b981"), "Vectorizar por Cuadro (Mouse)", self)
        self.act_cv.setCheckable(True)
        self.act_cv.triggered.connect(lambda: self._set_mode("select_roi"))
        self.toolbar.addAction(self.act_cv)

        self.act_cv_poly = QAction(get_svg_icon("draw_polygon", "#10b981"), "Vectorizar por Puntos (Lazo ROI)", self)
        self.act_cv_poly.setCheckable(True)
        self.act_cv_poly.triggered.connect(lambda: self._set_mode("select_roi_polygon"))
        self.toolbar.addAction(self.act_cv_poly)

        # Automatic Subdivision
        self.act_subdivide = QAction(get_svg_icon("draw_polygon", "#38bdf8"), "Auto-Generar Lotes en Manzana", self)
        self.act_subdivide.triggered.connect(self._auto_subdivide_manzana)
        self.toolbar.addAction(self.act_subdivide)

        self.toolbar.addSeparator()

        # Batch Operations
        self.act_batch_mock = QAction(get_svg_icon("data_generator", "#94a3b8"), "Generar Datos del Mapa", self)
        self.act_batch_mock.triggered.connect(self._batch_assign_mock_data)
        self.toolbar.addAction(self.act_batch_mock)

        self.act_recalc = QAction(get_svg_icon("recalc", "#94a3b8"), "Recalcular Códigos SIG", self)
        self.act_recalc.triggered.connect(self._batch_recalc_codes)
        self.toolbar.addAction(self.act_recalc)

        # Inyección directa a Base de Datos (Ctrl+S) para VisorDatosSIG
        self.act_save_db = QAction(get_svg_icon("database_export", "#10b981"), "⚡ Inyectar Cambios en BD (Ctrl+S)", self)
        self.act_save_db.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save_db.setToolTip("Inyecta directamente todos los vectores nuevos y modificados en las tablas de VisorDatosSIG (SQL Server)")
        self.act_save_db.triggered.connect(self._save_all_to_database)
        self.toolbar.addAction(self.act_save_db)

    def _build_layers_dock(self):
        dock = QDockWidget("Capas y Mapa Base", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)

        # Base Map selector
        layout.addWidget(QLabel("<b>Mapa Base:</b>"))
        self.cmb_basemap = QComboBox()
        self.cmb_basemap.addItem("OpenStreetMap (Colores y Formas)", "osm")
        self.cmb_basemap.addItem("CartoDB Dark Matter", "dark")
        self.cmb_basemap.addItem("Satelital (Esri)", "satellite")
        self.cmb_basemap.currentIndexChanged.connect(lambda: self.map_widget.set_basemap(self.cmb_basemap.currentData()))
        layout.addWidget(self.cmb_basemap)

        layout.addSpacing(10)

        # Layer Tree
        layout.addWidget(QLabel("<b>Capas del Sistema (VisorDatosSIG):</b>"))
        self.tree_layers = QTreeWidget()
        self.tree_layers.setHeaderLabels(["Capa", "Elementos"])
        self.tree_layers.itemChanged.connect(self._on_layer_visibility_changed)
        layout.addWidget(self.tree_layers)

        # Quick Layer Actions with SVG icons
        btn_reload_db = QPushButton("🔄 Sincronizar desde Base de Datos")
        btn_reload_db.setIcon(get_svg_icon("save_db", "#38bdf8"))
        btn_reload_db.clicked.connect(self._reload_from_database)
        layout.addWidget(btn_reload_db)

        btn_load_default = QPushButton("Cargar Capas Base (03_DatosPrueba)")
        btn_load_default.setIcon(get_svg_icon("folder", "#ffffff"))
        btn_load_default.setObjectName("btnSecondary")
        btn_load_default.clicked.connect(self._load_default_shapefiles)
        layout.addWidget(btn_load_default)

        btn_zoom_all = QPushButton("Extensión Completa")
        btn_zoom_all.setIcon(get_svg_icon("zoom_all", "#e2e8f0"))
        btn_zoom_all.setObjectName("btnSecondary")
        btn_zoom_all.clicked.connect(self._zoom_to_all)
        layout.addWidget(btn_zoom_all)

        dock.setWidget(panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    def _build_inspector_dock(self):
        dock = QDockWidget("Inspector de Vectores y Atributos", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
        
        self.inspector = AttributeEditorWidget(self.lm, self)
        dock.setWidget(self.inspector)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def _connect_signals(self):
        bridge = self.map_widget.bridge
        bridge.mapReady.connect(self._on_map_ready)
        bridge.mouseMoved.connect(lambda lat, lon: self.lbl_status_coords.setText(f"Lat: {lat:.5f}, Lon: {lon:.5f}"))
        bridge.featureSelected.connect(self._on_feature_selected)
        bridge.featureCreated.connect(self._on_feature_created)
        bridge.geometryModified.connect(self._on_geometry_modified)
        bridge.roiSelected.connect(self._on_roi_selected)
        bridge.undoRequested.connect(self._on_undo)
        bridge.deleteFeatureRequested.connect(self._delete_feature_by_id)
        bridge.deleteBoxSelected.connect(self._on_delete_box_selected)

        # Inspector signals
        self.inspector.featureModified.connect(self._on_feature_modified)
        self.inspector.featureDeleted.connect(self._on_feature_deleted)
        self.inspector.zoomRequested.connect(lambda bbox: self.map_widget.fly_to_extent(bbox))

    def _set_mode(self, mode: str, layer_key: str = "lotes"):
        actions = [
            self.act_nav, self.act_draw_lote, self.act_draw_mza,
            self.act_draw_point, self.act_draw_via, self.act_cv,
            self.act_cv_poly, self.act_del_box
        ]
        for a in actions:
            a.setChecked(False)

        if mode == "navigate":
            self.act_nav.setChecked(True)
            self.lbl_status_mode.setText("Modo: Exploración / Selección (Clic para editar, Supr para borrar, Ctrl+Z deshacer)")
        elif mode == "draw_polygon" and layer_key == "lotes":
            self.act_draw_lote.setChecked(True)
            self.lbl_status_mode.setText("Modo: Dibujar Lote")
        elif mode == "draw_polygon" and layer_key == "manzanas":
            self.act_draw_mza.setChecked(True)
            self.lbl_status_mode.setText("Modo: Dibujar Manzana")
        elif mode == "draw_point":
            self.act_draw_point.setChecked(True)
            self.lbl_status_mode.setText("Modo: Agregar Casa / Código Fijo")
        elif mode == "draw_line":
            self.act_draw_via.setChecked(True)
            self.lbl_status_mode.setText("Modo: Dibujar Vía")
        elif mode == "select_roi":
            self.act_cv.setChecked(True)
            self.lbl_status_mode.setText("Modo: Arrastra un cuadro con el mouse para vectorizar")
        elif mode == "select_roi_polygon":
            self.act_cv_poly.setChecked(True)
            self.lbl_status_mode.setText("Modo: Clic para marcar puntos del sector (Doble clic para terminar)")
        elif mode == "delete_box":
            self.act_del_box.setChecked(True)
            self.lbl_status_mode.setText("Modo: Arrastra un cuadro rojo sobre los vectores que deseas eliminar")

        self.map_widget.set_mode(mode, layer_key)

    @pyqtSlot()
    def _on_map_ready(self):
        self.status_bar.showMessage("Mapa Leaflet conectado exitosamente.", 3000)
        self._load_initial_data()

    def _load_initial_data(self):
        """Intenta cargar primero desde la Base de Datos SQL Server; si falla o está vacía, recurre a los shapefiles."""
        self.status_bar.showMessage(f"Conectando y cargando capas desde SQL Server ({db_sync.database})...")
        ok, stats, msg = db_sync.load_layers_from_database(self.lm, max_per_layer=20000)
        if ok and sum(stats.values()) > 0:
            self._update_layers_tree()
            self._sync_all_layers_to_map()
            self.status_bar.showMessage(f"Capas sincronizadas con la Base de Datos ({sum(stats.values())} elementos cargados).", 5000)
        else:
            self._load_default_shapefiles()

    def _reload_from_database(self):
        self.status_bar.showMessage("Recargando capas desde SQL Server (VisorDatosSIG)...")
        ok, stats, msg = db_sync.load_layers_from_database(self.lm, max_per_layer=20000)
        if ok and sum(stats.values()) > 0:
            self._update_layers_tree()
            self._sync_all_layers_to_map()
            self.status_bar.showMessage(f"Sincronización con BD completa ({sum(stats.values())} elementos).", 4000)
            QMessageBox.information(
                self,
                "Base de Datos Cargada",
                f"Se cargaron exitosamente {sum(stats.values())} vectores desde SQL Server ({db_sync.database}):\n\n"
                f"• Manzanas: {stats.get('manzanas', 0)}\n"
                f"• Lotes: {stats.get('lotes', 0)}\n"
                f"• Conexiones / Códigos Fijos: {stats.get('codigosfijos', 0)}\n"
                f"• Vías: {stats.get('vias', 0)}"
            )
        else:
            QMessageBox.warning(self, "Aviso de Base de Datos", f"No se pudo cargar desde la base de datos:\n\n{msg}")

    def _load_default_shapefiles(self):
        self.status_bar.showMessage("Cargando capas cartográficas desde 03_DatosPrueba/DatosSIG_Reproj...")
        stats = self.lm.load_from_default_directory(max_per_layer=2500)
        self._update_layers_tree()
        self._sync_all_layers_to_map()
        self.status_bar.showMessage(f"Capas cargadas ({sum(stats.values())} elementos).", 4000)

    def _update_layers_tree(self):
        self.tree_layers.blockSignals(True)
        self.tree_layers.clear()
        for key, conf in LAYER_CONFIG.items():
            layer = self.lm.get_layer(key)
            cnt = layer.count() if layer else 0
            
            item = QTreeWidgetItem(self.tree_layers)
            item.setText(0, conf["title"])
            item.setText(1, f"{cnt} rasgos")
            item.setCheckState(0, Qt.CheckState.Checked if (layer and layer.visible) else Qt.CheckState.Unchecked)
            item.setData(0, Qt.ItemDataRole.UserRole, key)
            item.setForeground(0, QColor(conf["color"]))
        self.tree_layers.blockSignals(False)

    def _sync_all_layers_to_map(self):
        for key, layer in self.lm.layers.items():
            if layer.visible and layer.count() > 0:
                self.map_widget.load_layer_geojson(key, layer.to_geojson())

    def _on_layer_visibility_changed(self, item: QTreeWidgetItem, column: int):
        key = item.data(0, Qt.ItemDataRole.UserRole)
        visible = (item.checkState(0) == Qt.CheckState.Checked)
        layer = self.lm.get_layer(key)
        if layer:
            layer.visible = visible
            self.map_widget.toggle_layer(key, visible)

    def _zoom_to_all(self):
        extent = self.lm.get_global_extent()
        self.map_widget.fly_to_extent(extent)

    @pyqtSlot(str, int)
    def _on_feature_selected(self, layer_key: str, feature_id: int):
        feat = self.lm.find_feature(layer_key, feature_id)
        if feat:
            self.inspector.load_feature(layer_key, feat)
            self.status_bar.showMessage(f"Vector #{feature_id} seleccionado de {layer_key}.", 3000)

    @pyqtSlot(str, str, str)
    def _on_feature_created(self, layer_key: str, geom_type: str, coords_json: str):
        coords = json.loads(coords_json)
        layer = self.lm.get_layer(layer_key)
        if not layer:
            return

        # 1. Hierarchical coding algorithm
        if layer_key == "manzanas":
            props = self.code_algo.assign_codes_for_manzana(coords)
        elif layer_key == "lotes":
            props = self.code_algo.assign_codes_for_lote(coords)
        elif layer_key == "codigosfijos":
            props = self.code_algo.assign_codes_for_codigo_fijo(coords[0], coords[1])
        elif layer_key == "vias":
            props = self.code_algo.assign_codes_for_via(coords)
        else:
            props = {}

        # 2. Enrich with real map dataset vocabulary
        props = enrich_feature_with_mock_data(layer_key, props, layer_manager=self.lm)

        # 3. Add to layer as new vector
        feat = layer.add_feature(geom_type, coords, properties=props, is_new=True)
        self.undo_mgr.push_add(layer_key, feat.id)

        # Inyección directa a Base de Datos (SQL Server VisorDatosSIG)
        ok_db, out_db, db_id = db_sync.insert_feature(layer_key, feat)
        if ok_db and db_id:
            old_id = feat.id
            if old_id != db_id:
                layer.features.pop(old_id, None)
                feat.id = db_id
                layer.features[db_id] = feat
            feat.is_new = False
            feat.is_modified = False
            db_status = f"⚡ Inyectado en Base de Datos (ID #{feat.id})"
        else:
            db_status = f"En memoria (Aviso BD: {out_db[:50]})" if not ok_db else f"Inyectado #{feat.id}"

        # 4. Push to Leaflet map
        self.map_widget.update_feature(layer_key, feat.to_geojson_dict())
        self._update_layers_tree()
        self.inspector.load_feature(layer_key, feat)
        self._set_mode("navigate")
        self.map_widget.fly_to_extent(feat.bbox)

        self.status_bar.showMessage(f"Nuevo vector #{feat.id} en {layer.title}. {db_status}", 4000)

    @pyqtSlot(float, float, float, float)
    def _on_roi_selected(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float):
        dlg = CVVectorizeDialog((min_lon, min_lat, max_lon, max_lat), self.lm, self)
        if dlg.exec():
            self._update_layers_tree()
            self._sync_all_layers_to_map()
            self.map_widget.fly_to_extent((min_lon, min_lat, max_lon, max_lat))
        self._set_mode("navigate")

    @pyqtSlot(str, int, str, str)
    def _on_geometry_modified(self, layer_key: str, feature_id: int, geom_type: str, coords_json: str):
        coords = json.loads(coords_json)
        layer = self.lm.get_layer(layer_key)
        if layer:
            old_feat = layer.get_feature(feature_id)
            if old_feat:
                self.undo_mgr.push_modify(layer_key, feature_id, old_feat.geom_type, old_feat.coordinates, dict(old_feat.properties))
            layer.update_geometry(feature_id, geom_type, coords)
            feat = layer.get_feature(feature_id)
            if feat:
                # Sincronización live en SQL Server
                db_sync.update_feature_geometry(layer_key, feature_id, geom_type, coords)
                self.inspector.load_feature(layer_key, feat)
                self.status_bar.showMessage(f"Geometría de #{feature_id} actualizada en BD y mapa. (Ctrl+Z para deshacer)", 3000)

    @pyqtSlot(str, int)
    def _on_feature_modified(self, layer_key: str, feature_id: int):
        feat = self.lm.find_feature(layer_key, feature_id)
        if feat:
            self.map_widget.update_feature(layer_key, feat.to_geojson_dict())

    @pyqtSlot(str, int)
    def _on_feature_deleted(self, layer_key: str, feature_id: int):
        self.map_widget.remove_feature(layer_key, feature_id)
        self._update_layers_tree()

    @pyqtSlot()
    def _on_undo(self):
        # Evitar doble ejecución por atajo de teclado simultáneo en Qt y WebView
        now = time.time()
        if hasattr(self, "_last_undo_time") and (now - self._last_undo_time < 0.25):
            return
        self._last_undo_time = now

        success, msg, sync_items = self.undo_mgr.undo(self.lm)
        if success:
            for l_key, action, data in sync_items:
                if action == "remove":
                    self.map_widget.remove_feature(l_key, data)
                elif action == "update":
                    self.map_widget.update_feature(l_key, data)
            self._update_layers_tree()
            self.inspector.clear()
            self.status_bar.showMessage(msg, 4000)
            self.map_widget.run_js(f"showToast('{msg}');")
        else:
            self.status_bar.showMessage(msg, 2500)

    @pyqtSlot()
    def _delete_selected_feature(self):
        feat = self.inspector.current_feature
        layer_key = self.inspector.current_layer_key
        if feat and layer_key:
            deleted_feat = self.lm.delete_feature(layer_key, feat.id)
            if deleted_feat:
                self.undo_mgr.push_delete(layer_key, deleted_feat)
                db_sync.delete_feature(layer_key, feat.id)
                self.map_widget.remove_feature(layer_key, feat.id)
                self._update_layers_tree()
                self.inspector.clear()
                msg = f"Vector #{feat.id} de {layer_key} eliminado de la base de datos y del mapa."
                self.status_bar.showMessage(msg, 4000)
                self.map_widget.run_js(f"showToast('{msg}');")
        else:
            self.status_bar.showMessage("Selecciona primero un vector en el mapa para eliminarlo.", 3000)

    @pyqtSlot(str, int)
    def _delete_feature_by_id(self, layer_key: str, feature_id: int):
        deleted_feat = self.lm.delete_feature(layer_key, feature_id)
        if deleted_feat:
            self.undo_mgr.push_delete(layer_key, deleted_feat)
            db_sync.delete_feature(layer_key, feature_id)
            self.map_widget.remove_feature(layer_key, feature_id)
            self._update_layers_tree()
            if self.inspector.current_feature and self.inspector.current_feature.id == feature_id:
                self.inspector.clear()
            msg = f"Vector #{feature_id} eliminado de la base de datos y mapa."
            self.status_bar.showMessage(msg, 4000)
            self.map_widget.run_js(f"showToast('{msg}');")

    @pyqtSlot(float, float, float, float)
    def _on_delete_box_selected(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float):
        deleted_items = self.lm.delete_features_in_bbox((min_lon, min_lat, max_lon, max_lat))
        if deleted_items:
            self.undo_mgr.push_batch_delete(deleted_items)
            db_sync.delete_features_batch([(k, f.id) for k, f in deleted_items])
            for l_key, feat in deleted_items:
                self.map_widget.remove_feature(l_key, feat.id)
            self._update_layers_tree()
            self.inspector.clear()
            msg = f"Se eliminaron {len(deleted_items)} vectores de la base de datos y del mapa."
            self.status_bar.showMessage(msg, 5000)
            self.map_widget.run_js(f"showToast('{msg}');")
        else:
            self.status_bar.showMessage("No se encontraron vectores dentro del cuadro para eliminar.", 3000)
        self._set_mode("navigate")

    def _auto_subdivide_manzana(self):
        current_feat = self.inspector.current_feature
        current_key = self.inspector.current_layer_key

        target_mza = None
        if current_feat and current_key == "manzanas":
            target_mza = current_feat
        else:
            mza_layer = self.lm.get_layer("manzanas")
            if mza_layer and mza_layer.count() > 0:
                target_mza = list(mza_layer.features.values())[0]

        if not target_mza:
            QMessageBox.warning(self, "Subdivisión", "Selecciona una manzana en el mapa para subdividirla en lotes.")
            return

        uv = target_mza.properties.get("UV", "S/N")
        mza = target_mza.properties.get("MZA", "S/N")
        reply = QMessageBox.question(
            self, "Auto-Generar Lotes en Manzana",
            f"¿Deseas subdividir automáticamente la Manzana #{target_mza.id} (UV {uv} MZA {mza}) en lotes regulares, generar sus conexiones de agua e inyectarlos en la base de datos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            lotes_layer = self.lm.get_layer("lotes")
            cf_layer = self.lm.get_layer("codigosfijos")

            new_lotes, new_cfs = subdivide_manzana_into_lots(target_mza, layer_manager=self.lm)
            for l in new_lotes:
                feat = lotes_layer.add_feature(l["geom_type"], l["coordinates"], properties=l["properties"], is_new=True)
                self.map_widget.update_feature("lotes", feat.to_geojson_dict())
            for c in new_cfs:
                feat = cf_layer.add_feature(c["geom_type"], c["coordinates"], properties=c["properties"], is_new=True)
                self.map_widget.update_feature("codigosfijos", feat.to_geojson_dict())

            # Inyección directa a la BD VisorDatosSIG
            batch_data = {
                "lotes": [{"coordinates": l["coordinates"], "properties": l["properties"], "geom_type": "Polygon"} for l in new_lotes],
                "codigosfijos": [{"coordinates": c["coordinates"], "properties": c["properties"], "geom_type": "Point"} for c in new_cfs]
            }
            ok_inj, out_inj, cnt_inj = db_sync.inject_batch(batch_data)
            self._update_layers_tree()
            self.map_widget.fly_to_extent(target_mza.bbox)
            if ok_inj and cnt_inj > 0:
                self.status_bar.showMessage(f"Generados e inyectados {cnt_inj} registros en BD ({db_sync.database}).", 5000)
                QMessageBox.information(
                    self,
                    "Lotes Inyectados en BD",
                    f"¡Zas! Se generaron e inyectaron {cnt_inj} lotes y conexiones de agua directamente en la base de datos de la plataforma ({db_sync.database})."
                )
            else:
                self.status_bar.showMessage(f"Generados {len(new_lotes)} lotes en memoria.", 4000)
                QMessageBox.information(
                    self,
                    "Lotes Generados",
                    f"Se generaron {len(new_lotes)} lotes y {len(new_cfs)} conexiones en memoria."
                )

    def _batch_assign_mock_data(self):
        reply = QMessageBox.question(
            self, "Generar Datos del Mapa",
            "¿Deseas asignar nombres reales de vías y propietarios extraídos del mapa a los vectores seleccionados?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            count = 0
            for key, layer in self.lm.layers.items():
                for feat in layer.features.values():
                    enriched = enrich_feature_with_mock_data(key, feat.properties, layer_manager=self.lm)
                    feat.properties.update(enriched)
                    feat.is_modified = True
                    count += 1
            self._sync_all_layers_to_map()
            QMessageBox.information(self, "Proceso Completado", f"Se asignaron datos a {count} vectores.")

    def _batch_recalc_codes(self):
        reply = QMessageBox.question(
            self, "Recalcular Códigos SIG",
            "¿Deseas recalcular las relaciones espaciales (Lotes dentro de Manzanas, Casas en Lotes)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            lotes_layer = self.lm.get_layer("lotes")
            count = 0
            if lotes_layer:
                for f in lotes_layer.features.values():
                    parent_mza = self.lm.find_parent_manzana_for_polygon(f.coordinates[0])
                    if parent_mza:
                        f.properties["IdManzana"] = parent_mza.id
                        f.properties["UV_MZA"] = parent_mza.properties.get("UV_MZA", "")
                        f.is_modified = True
                        count += 1
            self._sync_all_layers_to_map()
            QMessageBox.information(self, "Códigos Recalculados", f"Se re-sincronizaron códigos para {count} elementos.")

    def _save_all_to_database(self):
        """Inyecta directamente todos los vectores nuevos y modificados en SQL Server (VisorDatosSIG)."""
        self.status_bar.showMessage("Inyectando cambios en la base de datos SQL Server (VisorDatosSIG)...")
        ok, msg, count = db_sync.inject_layer_manager(self.lm, only_new_or_modified=True)
        if ok:
            self._update_layers_tree()
            if count > 0:
                success_msg = f"¡Éxito! Se inyectaron {count} registros directamente en la base de datos VisorDatosSIG."
                self.status_bar.showMessage(success_msg, 5000)
                self.map_widget.run_js(f"showToast('{success_msg}');")
                QMessageBox.information(
                    self,
                    "Base de Datos Sincronizada",
                    f"{success_msg}\n\nServidor: {db_sync.get_active_server()}\nBase de Datos: {db_sync.database}\n\nLos cambios ya están reflejados en tu plataforma web y backend sin necesidad de scripts manuales."
                )
            else:
                self.status_bar.showMessage("No hay cambios pendientes por inyectar en la base de datos.", 3000)
                QMessageBox.information(self, "Base de Datos al Día", "Todos los vectores ya están sincronizados en la base de datos.")
        else:
            QMessageBox.critical(
                self,
                "Error al Inyectar en Base de Datos",
                f"Ocurrió un error al inyectar en SQL Server:\n\n{msg}"
            )

