"""
CVVectorizeDialog: Diálogo de Vectorización, Clasificación y Alimentación Cartográfica.
Permite:
1. Alimentar directamente desde la Base Cartográfica Oficial (Shapefiles reales del sector con 100% de precisión).
2. Detectar trazados urbanos mediante Visión Computacional (Esqueletización morfológica de Zhang-Suen sin falsas líneas transversales).
3. Modo Híbrido: Combina vectores oficiales con nuevos trazados detectados.
"""
from typing import List, Dict, Any, Tuple, Optional
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QSpinBox, QGroupBox, QCheckBox,
    QMessageBox, QProgressBar, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from sig_vector_studio.cv_vectorizer.tile_downloader import TileImageStitcher
from sig_vector_studio.cv_vectorizer.contour_detector import OSMUrbanMLDetector
from sig_vector_studio.core.sector_feeder import SectorFeeder
from sig_vector_studio.generators.code_algorithm import CodeAssignmentAlgorithm
from sig_vector_studio.generators.mock_data_generator import enrich_feature_with_mock_data
from sig_vector_studio.gui.icons import get_svg_icon
from sig_vector_studio.core.layer_manager import LayerManager
from sig_vector_studio.core.db_sync import db_sync

class CVProcessingThread(QThread):
    finished = pyqtSignal(object, object, object)

    def __init__(self, stitcher, detector, bbox, target_layer, min_area, max_area, epsilon, sensitivity):
        super().__init__()
        self.stitcher = stitcher
        self.detector = detector
        self.bbox = bbox
        self.target_layer = target_layer
        self.min_area = min_area
        self.max_area = max_area
        self.epsilon = epsilon
        self.sensitivity = sensitivity

    def run(self):
        try:
            min_lon, min_lat, max_lon, max_lat = self.bbox
            bgr_img, actual_bounds = self.stitcher.fetch_bbox_image(min_lon, min_lat, max_lon, max_lat, zoom=17)
            results, annotated = self.detector.detect_vectors(
                bgr_img,
                actual_bounds,
                target_layer=self.target_layer,
                min_area=self.min_area,
                max_area=self.max_area,
                epsilon_ratio=self.epsilon,
                sensitivity=self.sensitivity
            )
            self.finished.emit((results, bgr_img, actual_bounds), annotated, None)
        except Exception as e:
            self.finished.emit(None, None, str(e))

class CVVectorizeDialog(QDialog):
    def __init__(self, bbox: Tuple[float, float, float, float], layer_manager: LayerManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vectorización y Alimentación Cartográfica Inteligente")
        self.resize(1080, 750)
        self.bbox = bbox
        self.lm = layer_manager
        self.stitcher = TileImageStitcher()
        self.detector = OSMUrbanMLDetector()
        self.code_algo = CodeAssignmentAlgorithm(layer_manager)

        # Consultar datos oficiales disponibles en este cuadrante
        self.official_data = SectorFeeder.get_features_in_bbox(bbox)
        self.detected_data: Any = None
        self.raw_image: Optional[np.ndarray] = None
        self.actual_bounds: Optional[Tuple[float, float, float, float]] = None
        self.annotated_image: Optional[np.ndarray] = None

        self._init_ui()
        self._start_processing()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        # Panel Izquierdo: Vista Previa y Leyenda
        left_layout = QVBoxLayout()
        preview_group = QGroupBox("Vista Previa del Sector")
        p_layout = QVBoxLayout(preview_group)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.lbl_image = QLabel("Descargando sector cartográfico...")
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_image.setStyleSheet("background-color: #090d16; color: #94a3b8; font-size: 13px;")
        self.scroll_area.setWidget(self.lbl_image)
        p_layout.addWidget(self.scroll_area)

        # Leyenda de Colores
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(self._create_legend_badge("Vías", "#a855f7"))
        legend_layout.addWidget(self._create_legend_badge("Manzanas", "#ef4444"))
        legend_layout.addWidget(self._create_legend_badge("Lotes / Terrenos", "#38bdf8"))
        legend_layout.addWidget(self._create_legend_badge("Casas / Medidores", "#f59e0b"))
        p_layout.addLayout(legend_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        p_layout.addWidget(self.progress_bar)

        left_layout.addWidget(preview_group)
        main_layout.addLayout(left_layout, stretch=2)

        # Panel Derecho: Configuración y Selección de Fuente
        right_group = QGroupBox("Opciones de Detección y Cartografía")
        param_layout = QVBoxLayout(right_group)

        # 1. Selector de Fuente
        param_layout.addWidget(QLabel("<b>Origen de los Datos:</b>"))
        self.cmb_source = QComboBox()

        off_vias = len(self.official_data.get("vias", []))
        off_mza = len(self.official_data.get("manzanas", []))
        off_lotes = len(self.official_data.get("lotes", []))
        off_casas = len(self.official_data.get("codigosfijos", []))
        has_official = (off_vias + off_mza + off_lotes + off_casas) > 0

        if has_official:
            self.cmb_source.addItem("📁 Base Oficial (Shapefiles del Sector - Recomendado)", "official")
            self.cmb_source.addItem("🌟 Modo Híbrido: Oficial + Nuevos Trazados", "hybrid")
            self.cmb_source.addItem("🧠 Visión Computacional (Esqueletización Urbana)", "vision")
        else:
            self.cmb_source.addItem("🧠 Visión Computacional (Esqueletización Urbana)", "vision")
            self.cmb_source.addItem("🌟 Modo Híbrido: Oficial + Nuevos Trazados", "hybrid")
            self.cmb_source.addItem("📁 Base Oficial (Shapefiles del Sector)", "official")

        self.cmb_source.currentIndexChanged.connect(self._update_layer_counts_ui)
        param_layout.addWidget(self.cmb_source)

        # Resumen de Base Oficial
        status_text = "Disponibles en este cuadrante" if has_official else "Fuera del rango oficial"
        lbl_off_info = QLabel(
            f"<b>Base Oficial ({status_text}):</b><br>"
            f"• Vías: {off_vias} &nbsp;|&nbsp; Manzanas: {off_mza}<br>"
            f"• Lotes: {off_lotes} &nbsp;|&nbsp; Casas/Medidores: {off_casas}"
        )
        lbl_off_info.setStyleSheet("color: #38bdf8; font-size: 11px; background: #0f172a; padding: 6px; border-radius: 4px;")
        param_layout.addWidget(lbl_off_info)

        # 2. Selector de Capa a Mapear
        param_layout.addWidget(QLabel("<b>Capas a Extraer:</b>"))
        self.cmb_layer = QComboBox()
        self.cmb_layer.addItem("🌟 Todo el Sector (Vías + Manzanas + Lotes + Casas)", "all")
        self.cmb_layer.addItem("🛣️ Sólo Vías / Calles (Líneas)", "vias")
        self.cmb_layer.addItem("🧱 Sólo Manzanas (Polígonos)", "manzanas")
        self.cmb_layer.addItem("📐 Sólo Lotes / Terrenos (Polígonos)", "lotes")
        self.cmb_layer.addItem("🏠 Sólo Casas / Códigos Fijos (Puntos)", "codigosfijos")
        self.cmb_layer.currentIndexChanged.connect(self._on_layer_mode_changed)
        param_layout.addWidget(self.cmb_layer)

        # 3. Checkboxes de Capas
        self.box_layers = QGroupBox("Capas Seleccionadas para Importar:")
        b_layout = QVBoxLayout(self.box_layers)

        self.chk_vias = QCheckBox("Vías / Calles (0)")
        self.chk_vias.setChecked(True)
        self.chk_vias.stateChanged.connect(self._render_current_preview)
        b_layout.addWidget(self.chk_vias)

        self.chk_manzanas = QCheckBox("Manzanas Urbanas (0)")
        self.chk_manzanas.setChecked(True)
        self.chk_manzanas.stateChanged.connect(self._render_current_preview)
        b_layout.addWidget(self.chk_manzanas)

        self.chk_lotes = QCheckBox("Lotes / Terrenos (0)")
        self.chk_lotes.setChecked(True)
        self.chk_lotes.stateChanged.connect(self._render_current_preview)
        b_layout.addWidget(self.chk_lotes)

        self.chk_casas = QCheckBox("Casas / Códigos Fijos (0)")
        self.chk_casas.setChecked(True)
        self.chk_casas.stateChanged.connect(self._render_current_preview)
        b_layout.addWidget(self.chk_casas)

        param_layout.addWidget(self.box_layers)

        # 4. Ajustes del Algoritmo de Visión
        param_layout.addWidget(QLabel("<b>Sensibilidad de Detección de Calles:</b>"))
        self.slider_sens = QSlider(Qt.Orientation.Horizontal)
        self.slider_sens.setRange(20, 100)
        self.slider_sens.setValue(55)
        self.lbl_sens_val = QLabel("55")
        h_sens = QHBoxLayout()
        h_sens.addWidget(self.slider_sens)
        h_sens.addWidget(self.lbl_sens_val)
        self.slider_sens.valueChanged.connect(lambda v: (self.lbl_sens_val.setText(str(v)), self._start_processing()))
        param_layout.addLayout(h_sens)

        param_layout.addWidget(QLabel("<b>Área Mínima de Manzana (px):</b>"))
        self.spin_min_area = QSpinBox()
        self.spin_min_area.setRange(50, 10000)
        self.spin_min_area.setValue(180)
        self.spin_min_area.setSingleStep(50)
        self.spin_min_area.valueChanged.connect(self._start_processing)
        param_layout.addWidget(self.spin_min_area)

        self.lbl_stats = QLabel("Analizando...")
        self.lbl_stats.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px; margin-top: 6px;")
        param_layout.addWidget(self.lbl_stats)

        param_layout.addStretch()

        # Botones de Acción
        self.btn_accept = QPushButton("Asignar Códigos e Importar al Mapa")
        self.btn_accept.setIcon(get_svg_icon("check", "#ffffff"))
        self.btn_accept.setObjectName("btnSuccess")
        self.btn_accept.setEnabled(False)
        self.btn_accept.clicked.connect(self._accept_and_import)
        param_layout.addWidget(self.btn_accept)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setIcon(get_svg_icon("cross", "#e2e8f0"))
        btn_cancel.setObjectName("btnSecondary")
        btn_cancel.clicked.connect(self.reject)
        param_layout.addWidget(btn_cancel)

        main_layout.addWidget(right_group, stretch=1)

    def _create_legend_badge(self, text: str, color_hex: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"background: #0f172a; border-left: 4px solid {color_hex}; border-radius: 4px; padding: 3px 6px;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(4, 2, 4, 2)
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #e2e8f0; font-size: 11px; font-weight: 500;")
        layout.addWidget(lbl)
        return frame

    def _on_layer_mode_changed(self):
        mode = self.cmb_layer.currentData()
        if mode == "all":
            self.chk_vias.setVisible(True)
            self.chk_manzanas.setVisible(True)
            self.chk_lotes.setVisible(True)
            self.chk_casas.setVisible(True)
        else:
            self.chk_vias.setVisible(mode == "vias")
            self.chk_manzanas.setVisible(mode == "manzanas")
            self.chk_lotes.setVisible(mode == "lotes")
            self.chk_casas.setVisible(mode == "codigosfijos")
        self._start_processing()

    def _start_processing(self):
        self.progress_bar.setVisible(True)
        self.btn_accept.setEnabled(False)
        self.lbl_stats.setText("Analizando sector cartográfico...")

        target_layer = self.cmb_layer.currentData()
        min_area = self.spin_min_area.value()
        sensitivity = self.slider_sens.value()

        self.thread = CVProcessingThread(
            self.stitcher, self.detector, self.bbox, target_layer,
            min_area=min_area, max_area=200000, epsilon=0.02, sensitivity=sensitivity
        )
        self.thread.finished.connect(self._on_processing_finished)
        self.thread.start()

    def _on_processing_finished(self, data, annotated_bgr, error):
        self.progress_bar.setVisible(False)
        if error or data is None:
            self.lbl_image.setText(f"Error al procesar: {error or 'Imagen no disponible'}")
            return

        results, bgr_img, actual_bounds = data
        self.detected_data = results
        self.raw_image = bgr_img
        self.actual_bounds = actual_bounds

        self._update_layer_counts_ui()
        self._render_current_preview()

    def _render_current_preview(self):
        """Renderiza dinámicamente sobre la imagen base las capas seleccionadas según la fuente activa."""
        if self.raw_image is None or self.actual_bounds is None:
            return

        canvas = self.raw_image.copy()
        h, w = canvas.shape[:2]
        bounds = self.actual_bounds
        source = self.cmb_source.currentData()
        mode = self.cmb_layer.currentData()

        def get_items(key: str) -> List[Dict[str, Any]]:
            off_items = self.official_data.get(key, [])
            vis_items = []
            if isinstance(self.detected_data, dict):
                vis_items = self.detected_data.get(key, [])
            elif isinstance(self.detected_data, list) and mode == key:
                vis_items = self.detected_data

            if source == "official":
                return off_items
            elif source == "vision":
                return vis_items
            else:  # hybrid
                return off_items if len(off_items) > 0 else vis_items

        # 1. Lotes (Cian)
        if self.chk_lotes.isChecked() and (mode in ("all", "lotes")):
            for item in get_items("lotes"):
                coords = item.get("coordinates", [])
                if coords:
                    ring = coords[0] if isinstance(coords[0][0], (list, tuple)) else coords
                    pts = [self.detector.geo_to_pixel(p[0], p[1], w, h, bounds) for p in ring]
                    if len(pts) >= 3:
                        poly_arr = np.array(pts, dtype=np.int32)
                        cv2.polylines(canvas, [poly_arr], True, (248, 189, 56), 1)

        # 2. Manzanas (Rojo)
        if self.chk_manzanas.isChecked() and (mode in ("all", "manzanas")):
            for item in get_items("manzanas"):
                coords = item.get("coordinates", [])
                if coords:
                    ring = coords[0] if isinstance(coords[0][0], (list, tuple)) else coords
                    pts = [self.detector.geo_to_pixel(p[0], p[1], w, h, bounds) for p in ring]
                    if len(pts) >= 3:
                        poly_arr = np.array(pts, dtype=np.int32)
                        cv2.polylines(canvas, [poly_arr], True, (38, 38, 220), 2)

        # 3. Vías (Púrpura)
        if self.chk_vias.isChecked() and (mode in ("all", "vias")):
            for item in get_items("vias"):
                coords = item.get("coordinates", [])
                if len(coords) >= 2:
                    pts = [self.detector.geo_to_pixel(p[0], p[1], w, h, bounds) for p in coords]
                    for i in range(len(pts) - 1):
                        cv2.line(canvas, pts[i], pts[i + 1], (168, 85, 247), 3)

        # 4. Casas / Códigos Fijos (Ámbar)
        if self.chk_casas.isChecked() and (mode in ("all", "codigosfijos")):
            for item in get_items("codigosfijos"):
                coords = item.get("coordinates", [])
                if len(coords) >= 2:
                    px, py = self.detector.geo_to_pixel(coords[0], coords[1], w, h, bounds)
                    cv2.circle(canvas, (px, py), 4, (11, 158, 245), -1)
                    cv2.circle(canvas, (px, py), 5, (255, 255, 255), 1)

        self.annotated_image = canvas

        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        ch_h, ch_w, ch_c = rgb.shape
        qimg = QImage(rgb.data, ch_w, ch_h, ch_c * ch_w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        self.lbl_image.setPixmap(pix.scaled(
            self.lbl_image.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))

    def _update_layer_counts_ui(self):
        source = self.cmb_source.currentData()
        mode = self.cmb_layer.currentData()

        # Conteo por Visión
        vis_vias = len(self.detected_data.get("vias", [])) if isinstance(self.detected_data, dict) else (len(self.detected_data) if mode == "vias" else 0)
        vis_mza = len(self.detected_data.get("manzanas", [])) if isinstance(self.detected_data, dict) else (len(self.detected_data) if mode == "manzanas" else 0)
        vis_lotes = len(self.detected_data.get("lotes", [])) if isinstance(self.detected_data, dict) else (len(self.detected_data) if mode == "lotes" else 0)
        vis_casas = len(self.detected_data.get("codigosfijos", [])) if isinstance(self.detected_data, dict) else (len(self.detected_data) if mode == "codigosfijos" else 0)

        # Conteo Oficial
        off_vias = len(self.official_data.get("vias", []))
        off_mza = len(self.official_data.get("manzanas", []))
        off_lotes = len(self.official_data.get("lotes", []))
        off_casas = len(self.official_data.get("codigosfijos", []))

        if source == "official":
            total_vias, total_mza, total_lotes, total_casas = off_vias, off_mza, off_lotes, off_casas
        elif source == "vision":
            total_vias, total_mza, total_lotes, total_casas = vis_vias, vis_mza, vis_lotes, vis_casas
        else:  # hybrid
            total_vias = off_vias if off_vias > 0 else vis_vias
            total_mza = off_mza if off_mza > 0 else vis_mza
            total_lotes = off_lotes if off_lotes > 0 else vis_lotes
            total_casas = off_casas if off_casas > 0 else vis_casas

        self.chk_vias.setText(f"Vías / Calles ({total_vias})")
        self.chk_manzanas.setText(f"Manzanas Urbanas ({total_mza})")
        self.chk_lotes.setText(f"Lotes / Terrenos ({total_lotes})")
        self.chk_casas.setText(f"Casas / Códigos Fijos ({total_casas})")

        total = total_vias + total_mza + total_lotes + total_casas
        self.lbl_stats.setText(f"Elementos listos para mapear: {total}")
        self.btn_accept.setEnabled(total > 0)

        # Refrescar vista previa
        self._render_current_preview()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.annotated_image is not None:
            rgb = cv2.cvtColor(self.annotated_image, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
            pix = QPixmap.fromImage(qimg)
            self.lbl_image.setPixmap(pix.scaled(
                self.lbl_image.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            ))

    def _accept_and_import(self):
        source = self.cmb_source.currentData()
        mode = self.cmb_layer.currentData()
        imported_summary = []

        def get_layer_items(key: str) -> List[Dict[str, Any]]:
            off_items = self.official_data.get(key, [])
            vis_items = []
            if isinstance(self.detected_data, dict):
                vis_items = self.detected_data.get(key, [])
            elif isinstance(self.detected_data, list) and mode == key:
                vis_items = self.detected_data

            if source == "official":
                return off_items
            elif source == "vision":
                return vis_items
            else:  # hybrid
                return off_items if len(off_items) > 0 else vis_items

        # Diccionario para inyección directa masiva en SQL Server
        batch_to_inject: Dict[str, List[Dict[str, Any]]] = {
            "vias": [],
            "manzanas": [],
            "lotes": [],
            "codigosfijos": []
        }
        added_feats_by_layer: Dict[str, List[Any]] = {
            "vias": [],
            "manzanas": [],
            "lotes": [],
            "codigosfijos": []
        }

        # 1. Importar Vías
        if self.chk_vias.isChecked() and (mode in ("all", "vias")):
            items = get_layer_items("vias")
            layer = self.lm.get_layer("vias")
            count = 0
            for it in items:
                coords = it["coordinates"]
                props = dict(it.get("properties", {}))
                if not props.get("Nombre") and not props.get("NOM_VIA"):
                    props = self.code_algo.assign_codes_for_via(coords)
                    props = enrich_feature_with_mock_data("vias", props, layer_manager=self.lm)
                feat = layer.add_feature("LineString", coords, properties=props, is_new=True)
                added_feats_by_layer["vias"].append(feat)
                batch_to_inject["vias"].append({"coordinates": coords, "properties": props, "geom_type": "LineString"})
                count += 1
            if count > 0:
                imported_summary.append(f"{count} Vías / Calles")

        # 2. Importar Manzanas
        if self.chk_manzanas.isChecked() and (mode in ("all", "manzanas")):
            items = get_layer_items("manzanas")
            layer = self.lm.get_layer("manzanas")
            count = 0
            for it in items:
                coords = it["coordinates"]
                props = dict(it.get("properties", {}))
                if not props.get("UV_MZA"):
                    props = self.code_algo.assign_codes_for_manzana(coords)
                    props = enrich_feature_with_mock_data("manzanas", props, layer_manager=self.lm)
                feat = layer.add_feature("Polygon", coords, properties=props, is_new=True)
                added_feats_by_layer["manzanas"].append(feat)
                batch_to_inject["manzanas"].append({"coordinates": coords, "properties": props, "geom_type": "Polygon"})
                count += 1
            if count > 0:
                imported_summary.append(f"{count} Manzanas Urbanas")

        # 3. Importar Lotes
        if self.chk_lotes.isChecked() and (mode in ("all", "lotes")):
            items = get_layer_items("lotes")
            layer = self.lm.get_layer("lotes")
            count = 0
            for it in items:
                coords = it["coordinates"]
                props = dict(it.get("properties", {}))
                if not props.get("NroLote"):
                    props = self.code_algo.assign_codes_for_lote(coords)
                    props = enrich_feature_with_mock_data("lotes", props, layer_manager=self.lm)
                feat = layer.add_feature("Polygon", coords, properties=props, is_new=True)
                added_feats_by_layer["lotes"].append(feat)
                batch_to_inject["lotes"].append({"coordinates": coords, "properties": props, "geom_type": "Polygon"})
                count += 1
            if count > 0:
                imported_summary.append(f"{count} Lotes / Terrenos")

        # 4. Importar Casas / Códigos Fijos
        if self.chk_casas.isChecked() and (mode in ("all", "codigosfijos")):
            items = get_layer_items("codigosfijos")
            layer = self.lm.get_layer("codigosfijos")
            count = 0
            for it in items:
                coords = it["coordinates"]
                props = dict(it.get("properties", {}))
                if not props.get("CodFijo"):
                    props = self.code_algo.assign_codes_for_codigo_fijo(coords[0], coords[1])
                    props = enrich_feature_with_mock_data("codigosfijos", props, layer_manager=self.lm)
                feat = layer.add_feature("Point", coords, properties=props, is_new=True)
                added_feats_by_layer["codigosfijos"].append(feat)
                batch_to_inject["codigosfijos"].append({"coordinates": coords, "properties": props, "geom_type": "Point"})
                count += 1
            if count > 0:
                imported_summary.append(f"{count} Casas / Códigos Fijos")

        # Inyección directa inmediata en SQL Server (VisorDatosSIG)
        ok_db, out_db, cnt_db = db_sync.inject_batch(batch_to_inject)
        if ok_db and cnt_db > 0:
            for l_key, feats in added_feats_by_layer.items():
                for f in feats:
                    f.is_new = False
                    f.is_modified = False

        summary_text = "\n• ".join(imported_summary) if imported_summary else "Ningún elemento seleccionado"
        if ok_db and cnt_db > 0:
            QMessageBox.information(
                self,
                "Inyección Directa en Base de Datos Exitosa",
                f"¡Zas! Se inyectaron {cnt_db} registros directamente en la base de datos de la plataforma:\n\n"
                f"• {summary_text}\n\n"
                f"Servidor: {db_sync.get_active_server()}\nBase de Datos: {db_sync.database}\n\n"
                f"Los vectores ya se encuentran persistidos en SQL Server y cargados en el mapa listos para su uso."
            )
        else:
            QMessageBox.information(
                self,
                "Mapeo Incorporado",
                f"Se han incorporado al visor:\n• {summary_text}\n\n"
                f"(Aviso de Base de Datos: {out_db})"
            )
        self.accept()
