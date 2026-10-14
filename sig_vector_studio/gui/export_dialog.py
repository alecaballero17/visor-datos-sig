"""
ExportDialog: Wizard to export vectors to SQL Server T-SQL script, GeoJSON, and Shapefiles (.shp).
Ensures 100% compatibility with VisorDatosSIG database and frontend platform.
Includes direct execution into SQL Server (VisorDatosSIG).
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTextEdit, QCheckBox, QFileDialog, QMessageBox,
    QWidget, QGroupBox, QApplication
)
from PyQt6.QtCore import Qt
from sig_vector_studio.core.layer_manager import LayerManager
from sig_vector_studio.core.db_sync import db_sync
from sig_vector_studio.exporters.sql_exporter import generate_sql_migration
from sig_vector_studio.exporters.geojson_exporter import export_all_layers_to_directory
from sig_vector_studio.exporters.shp_exporter import export_all_layers_to_shapefiles
from sig_vector_studio.gui.icons import get_svg_icon

class ExportDialog(QDialog):
    def __init__(self, layer_manager: LayerManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exportar Datos y Sincronizar Base de Datos")
        self.resize(880, 640)
        self.lm = layer_manager
        self._init_ui()
        self._refresh_sql_preview()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel(
            "<h3>Sincronización y Exportador VisorDatosSIG</h3>"
            "<p style='color: #94a3b8;'>Guarda directamente en la base de datos SQL Server o exporta a GeoJSON / Shapefile.</p>"
        )
        layout.addWidget(header)

        self.tabs = QTabWidget()

        # Tab 1: SQL Server Migration (.sql)
        tab_sql = QWidget()
        sql_layout = QVBoxLayout(tab_sql)

        top_sql_bar = QHBoxLayout()
        self.chk_only_new = QCheckBox("Exportar únicamente vectores nuevos y modificados de esta sesión")
        self.chk_only_new.setChecked(True)
        self.chk_only_new.stateChanged.connect(self._refresh_sql_preview)
        top_sql_bar.addWidget(self.chk_only_new)

        btn_refresh = QPushButton("Actualizar Vista")
        btn_refresh.setIcon(get_svg_icon("recalc", "#e2e8f0"))
        btn_refresh.setObjectName("btnSecondary")
        btn_refresh.clicked.connect(self._refresh_sql_preview)
        top_sql_bar.addWidget(btn_refresh)
        sql_layout.addLayout(top_sql_bar)

        self.txt_sql = QTextEdit()
        self.txt_sql.setReadOnly(True)
        self.txt_sql.setFontFamily("Consolas")
        self.txt_sql.setStyleSheet("background-color: #090d16; color: #38bdf8; font-size: 12px;")
        sql_layout.addWidget(self.txt_sql)

        # SQL Action Buttons
        sql_btn_bar = QHBoxLayout()

        self.btn_execute_db = QPushButton("🚀 Guardar Directamente en Base de Datos (SQL Server)")
        self.btn_execute_db.setIcon(get_svg_icon("database_export", "#ffffff"))
        self.btn_execute_db.setObjectName("btnSuccess")
        self.btn_execute_db.setStyleSheet("background-color: #059669; color: #ffffff; font-weight: bold; padding: 8px 16px;")
        self.btn_execute_db.clicked.connect(self._execute_to_database)
        sql_btn_bar.addWidget(self.btn_execute_db)

        self.btn_copy_sql = QPushButton("Copiar SQL")
        self.btn_copy_sql.setIcon(get_svg_icon("copy", "#ffffff"))
        self.btn_copy_sql.clicked.connect(self._copy_sql)
        sql_btn_bar.addWidget(self.btn_copy_sql)

        self.btn_save_sql = QPushButton("Guardar Archivo .sql")
        self.btn_save_sql.setIcon(get_svg_icon("save", "#ffffff"))
        self.btn_save_sql.setObjectName("btnSecondary")
        self.btn_save_sql.clicked.connect(self._save_sql_file)
        sql_btn_bar.addWidget(self.btn_save_sql)

        sql_layout.addLayout(sql_btn_bar)

        self.tabs.addTab(tab_sql, "1. Base de Datos SQL Server (Directo / .sql)")

        # Tab 2: GeoJSON Export
        tab_geojson = QWidget()
        geo_layout = QVBoxLayout(tab_geojson)
        geo_info = QLabel(
            "<b>Exportar en formato GeoJSON</b><br>"
            "Genera archivos <code>manzanas.geojson</code>, <code>lotes.geojson</code>, <code>codigosfijos.geojson</code> y <code>vias.geojson</code> "
            "compatibles directamente con Leaflet y el servicio <code>GeoDataService</code> de C# Blazor."
        )
        geo_info.setWordWrap(True)
        geo_layout.addWidget(geo_info)
        geo_layout.addStretch()

        self.btn_export_geojson = QPushButton("Exportar Carpeta de Archivos GeoJSON...")
        self.btn_export_geojson.setIcon(get_svg_icon("folder", "#ffffff"))
        self.btn_export_geojson.clicked.connect(self._export_geojson)
        geo_layout.addWidget(self.btn_export_geojson)
        self.tabs.addTab(tab_geojson, "2. Formato GeoJSON (.geojson)")

        # Tab 3: Shapefiles (.shp)
        tab_shp = QWidget()
        shp_layout = QVBoxLayout(tab_shp)
        shp_info = QLabel(
            "<b>Exportar Capas Shapefile (.shp + .dbf + .prj + .shx)</b><br>"
            "Genera capas vectoriales con proyección <b>EPSG:4326 (WGS 84)</b> listas para importar en SQL Server "
            "mediante QGIS o <code>ogr2ogr</code> siguiendo las instrucciones de <code>02_BaseDatos/02_Importar_SHP.md</code>."
        )
        shp_info.setWordWrap(True)
        shp_layout.addWidget(shp_info)
        shp_layout.addStretch()

        self.btn_export_shp = QPushButton("Exportar Capas Shapefiles (.shp)...")
        self.btn_export_shp.setIcon(get_svg_icon("folder", "#ffffff"))
        self.btn_export_shp.clicked.connect(self._export_shp)
        shp_layout.addWidget(self.btn_export_shp)
        self.tabs.addTab(tab_shp, "3. Formato Shapefile (.shp)")

        layout.addWidget(self.tabs)

        btn_close = QPushButton("Cerrar")
        btn_close.setObjectName("btnSecondary")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _refresh_sql_preview(self):
        only_new = self.chk_only_new.isChecked()
        sql_text = generate_sql_migration(self.lm, only_new_or_modified=only_new)
        self.txt_sql.setPlainText(sql_text)

    def _execute_to_database(self):
        """Ejecuta directamente las sentencias SQL en SQL Server VisorDatosSIG."""
        sql_text = self.txt_sql.toPlainText().strip()
        if not sql_text:
            QMessageBox.warning(self, "Sin datos", "No hay instrucciones SQL para ejecutar.")
            return

        reply = QMessageBox.question(
            self,
            "Guardar en Base de Datos",
            "¿Deseas guardar e insertar directamente todos estos vectores en la base de datos SQL Server (VisorDatosSIG)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.btn_execute_db.setEnabled(False)
            self.btn_execute_db.setText("Guardando en SQL Server...")
            QApplication.processEvents()

            ok, out = db_sync.execute_sql(sql_text)
            self.btn_execute_db.setEnabled(True)
            self.btn_execute_db.setText("🚀 Guardar Directamente en Base de Datos (SQL Server)")

            if ok:
                # Marcar los vectores como guardados
                for layer in self.lm.layers.values():
                    for f in layer.features.values():
                        f.is_new = False
                        f.is_modified = False

                QMessageBox.information(
                    self,
                    "Base de Datos Actualizada",
                    f"¡Los vectores se han guardado exitosamente en SQL Server!\n\n"
                    f"Base de Datos: VisorDatosSIG\n"
                    f"Servidor: {db_sync.get_active_server()}\n\n"
                    f"Detalle:\n{out}"
                )
                self._refresh_sql_preview()
            else:
                QMessageBox.critical(
                    self,
                    "Error al Guardar en Base de Datos",
                    f"Ocurrió un error al ejecutar en SQL Server:\n\n{out}"
                )

    def _copy_sql(self):
        QApplication.clipboard().setText(self.txt_sql.toPlainText())
        QMessageBox.information(self, "Copiado", "El script SQL ha sido copiado al portapapeles.")

    def _save_sql_file(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Guardar Script SQL", "Actualizacion_Vectores_SIG.sql", "SQL Files (*.sql)"
        )
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.txt_sql.toPlainText())
            QMessageBox.information(self, "Guardado", f"Archivo guardado exitosamente en:\n{filepath}")

    def _export_geojson(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta para GeoJSON")
        if folder:
            stats = export_all_layers_to_directory(self.lm, folder)
            total = sum(stats.values())
            QMessageBox.information(
                self, "Exportación GeoJSON Completada",
                f"Se exportaron {total} vectores en {len(stats)} capas a:\n{folder}"
            )

    def _export_shp(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta para Shapefiles")
        if folder:
            stats = export_all_layers_to_shapefiles(self.lm, folder)
            total = sum(stats.values())
            QMessageBox.information(
                self, "Exportación Shapefile Completada",
                f"Se exportaron {total} vectores en formato ESRI Shapefile a:\n{folder}\n\nListos para importar con QGIS o ogr2ogr."
            )
