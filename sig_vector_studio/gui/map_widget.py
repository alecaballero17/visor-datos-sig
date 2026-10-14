"""
MapWidget: PyQt6 QWebEngineView hosting interactive Leaflet map with Python-JavaScript bridge.
"""
import json
from pathlib import Path
from typing import Dict, Any, Tuple
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from sig_vector_studio.config import WEB_DIR

class MapWebPage(QWebEnginePage):
    """Custom WebEnginePage with console logging."""
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        # Filter noisy messages
        lvl_name = getattr(level, "name", str(level))
        if "warning" in lvl_name.lower() or "error" in lvl_name.lower():
            print(f"[Map JS {lvl_name}] {message} (line {lineNumber})")

class PyBridge(QObject):
    """Bridge object exposed to JavaScript window.pyBridge."""
    mapReady = pyqtSignal()
    mouseMoved = pyqtSignal(float, float)
    featureSelected = pyqtSignal(str, int)
    featureCreated = pyqtSignal(str, str, str)               # layerKey, geomType, coordsJson
    geometryModified = pyqtSignal(str, int, str, str)        # layerKey, fid, geomType, coordsJson
    roiSelected = pyqtSignal(float, float, float, float)     # minLon, minLat, maxLon, maxLat
    undoRequested = pyqtSignal()
    deleteFeatureRequested = pyqtSignal(str, int)            # layerKey, featureId
    deleteBoxSelected = pyqtSignal(float, float, float, float) # minLon, minLat, maxLon, maxLat

    @pyqtSlot()
    def onMapReady(self):
        self.mapReady.emit()

    @pyqtSlot(float, float)
    def onMouseMove(self, lat: float, lon: float):
        self.mouseMoved.emit(lat, lon)

    @pyqtSlot(str, int)
    def onFeatureSelected(self, layer_key: str, feature_id: int):
        self.featureSelected.emit(layer_key, feature_id)

    @pyqtSlot(str, str, str)
    def onFeatureCreated(self, layer_key: str, geom_type: str, coords_json: str):
        self.featureCreated.emit(layer_key, geom_type, coords_json)

    @pyqtSlot(str, int, str, str)
    def onGeometryModified(self, layer_key: str, feature_id: int, geom_type: str, coords_json: str):
        self.geometryModified.emit(layer_key, feature_id, geom_type, coords_json)

    @pyqtSlot(float, float, float, float)
    def onRoiSelected(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float):
        self.roiSelected.emit(min_lon, min_lat, max_lon, max_lat)

    @pyqtSlot()
    def onUndoRequested(self):
        self.undoRequested.emit()

    @pyqtSlot(str, int)
    def onFeatureDeleteRequested(self, layer_key: str, feature_id: int):
        self.deleteFeatureRequested.emit(layer_key, feature_id)

    @pyqtSlot(float, float, float, float)
    def onDeleteBoxSelected(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float):
        self.deleteBoxSelected.emit(min_lon, min_lat, max_lon, max_lat)

class MapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.web_view = QWebEngineView(self)
        self.custom_page = MapWebPage(self.web_view)
        self.web_view.setPage(self.custom_page)
        layout.addWidget(self.web_view)

        # Configure WebEngine Settings for local file tile and remote access
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)

        # WebChannel setup
        self.channel = QWebChannel(self.web_view.page())
        self.bridge = PyBridge()
        self.channel.registerObject("pyBridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        self.is_map_ready = False
        self.pending_layers: Dict[str, Dict[str, Any]] = {}
        self.bridge.mapReady.connect(self._on_map_ready_internal)

        # Load local HTML
        index_file = (WEB_DIR / "index.html").resolve()
        self.web_view.setUrl(QUrl.fromLocalFile(str(index_file)))

    def _on_map_ready_internal(self):
        self.is_map_ready = True
        # Flush pending layers
        for key, data in list(self.pending_layers.items()):
            self._send_layer_geojson(key, data)
        self.pending_layers.clear()

    def run_js(self, script: str):
        """Execute JavaScript inside Leaflet environment."""
        self.web_view.page().runJavaScript(script)

    def _send_layer_geojson(self, layer_key: str, geojson_dict: Dict[str, Any]):
        json_str = json.dumps(geojson_dict)
        js = f"loadLayerGeoJson('{layer_key}', {json_str});"
        self.run_js(js)

    def load_layer_geojson(self, layer_key: str, geojson_dict: Dict[str, Any]):
        if not self.is_map_ready:
            self.pending_layers[layer_key] = geojson_dict
            return
        self._send_layer_geojson(layer_key, geojson_dict)

    def update_feature(self, layer_key: str, feature_geojson: Dict[str, Any]):
        json_str = json.dumps(feature_geojson)
        js = f"updateFeatureInMap('{layer_key}', {json_str});"
        self.run_js(js)

    def remove_feature(self, layer_key: str, feature_id: int):
        js = f"removeFeatureFromMap('{layer_key}', {feature_id});"
        self.run_js(js)

    def set_mode(self, mode: str, layer_key: str = "lotes"):
        js = f"setInteractionMode('{mode}', '{layer_key}');"
        self.run_js(js)

    def set_basemap(self, basemap_type: str):
        js = f"setBaseMap('{basemap_type}');"
        self.run_js(js)

    def toggle_layer(self, layer_key: str, visible: bool):
        js = f"toggleLayerVisibility('{layer_key}', {'true' if visible else 'false'});"
        self.run_js(js)

    def fly_to_extent(self, bbox: Tuple[float, float, float, float]):
        min_lon, min_lat, max_lon, max_lat = bbox
        js = f"flyToExtent({min_lon}, {min_lat}, {max_lon}, {max_lat});"
        self.run_js(js)
