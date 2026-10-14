/**
 * SIG Vector Studio - Interactive Map Controller
 * Integrates Leaflet with Python Qt via QWebChannel with interactive vertex editing.
 */
let map = null;
let pyBridge = null;

// Base layers
const baseLayers = {};
let currentBaseLayer = null;

// Vector layer groups (initialized in initMap)
const layerGroups = {};

// Internal map of feature ID -> Leaflet layer
const featureMap = {
    manzanas: new Map(),
    lotes: new Map(),
    codigosfijos: new Map(),
    vias: new Map()
};

// Current interaction mode: 'navigate', 'draw_polygon', 'draw_point', 'draw_line', 'select_roi'
let currentMode = 'navigate';
let activeDrawLayer = 'lotes';
let selectedLayerKey = null;
let selectedFeatureId = null;
let selectedGraphic = null;

// Drawing state
let drawPoints = [];
let drawTempPolyline = null;
let drawTempMarkers = [];
let liveGuideLine = null;
let roiStartLatLng = null;
let roiRect = null;

// Editing state
let editVertexMarkers = [];

// Layer styles aligned with VisorDatosSIG
const STYLES = {
    manzanas: {
        color: '#dc2626',
        weight: 2.5,
        fillColor: '#ef4444',
        fillOpacity: 0.12
    },
    lotes: {
        color: '#0284c7',
        weight: 1.5,
        fillColor: '#38bdf8',
        fillOpacity: 0.22
    },
    codigosfijos: {
        radius: 4,
        color: '#f59e0b',
        fillColor: '#fbbf24',
        weight: 1.5,
        fillOpacity: 0.95
    },
    vias: {
        color: '#9333ea',
        weight: 3.5,
        opacity: 0.85
    },
    selected: {
        color: '#f43f5e',
        weight: 4,
        fillColor: '#fb7185',
        fillOpacity: 0.35,
        dashArray: '4, 4'
    }
};

function initMap() {
    if (typeof L === 'undefined') {
        console.warn("Leaflet not loaded yet, retrying in 50ms...");
        setTimeout(initMap, 50);
        return;
    }

    if (map) return;

    // Center at San Ignacio de Velasco / Santa Cruz region
    map = L.map('map', {
        zoomControl: false,
        preferCanvas: true
    }).setView([-16.3900, -60.9650], 15);

    L.control.zoom({ position: 'topright' }).addTo(map);
    L.control.scale({ imperial: false, position: 'bottomleft' }).addTo(map);

    // 1. Base map tile layers
    baseLayers['osm'] = L.tileLayer(
        'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
        { maxZoom: 19, attribution: '&copy; OpenStreetMap' }
    );

    baseLayers['satellite'] = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        { maxZoom: 19, attribution: 'Esri World Imagery' }
    );

    baseLayers['dark'] = L.tileLayer(
        'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        { maxZoom: 19, attribution: '&copy; CartoDB Dark' }
    );

    // Add OpenStreetMap (color and shapes) as the default base layer
    currentBaseLayer = baseLayers['osm'];
    currentBaseLayer.addTo(map);

    // 2. Initialize Layer Groups
    layerGroups['manzanas'] = L.layerGroup().addTo(map);
    layerGroups['lotes'] = L.layerGroup().addTo(map);
    layerGroups['codigosfijos'] = L.layerGroup().addTo(map);
    layerGroups['vias'] = L.layerGroup().addTo(map);
    layerGroups['roi'] = L.layerGroup().addTo(map);
    layerGroups['preview'] = L.layerGroup().addTo(map);

    // Map Event Listeners
    map.on('mousemove', onMapMouseMove);
    map.on('click', onMapClick);
    map.on('mousedown', onMapMouseDown);
    map.on('mouseup', onMapMouseUp);
    map.on('dblclick', onMapDblClick);

    // Force map recalculation
    window.addEventListener('resize', () => { if (map) map.invalidateSize(); });
    setTimeout(() => { if (map) map.invalidateSize(); }, 50);
    setTimeout(() => { if (map) map.invalidateSize(); }, 250);
    setTimeout(() => { if (map) map.invalidateSize(); }, 750);
    setTimeout(() => { if (map) map.invalidateSize(); }, 1500);

    initWebChannel();
}

function initWebChannel() {
    if (typeof QWebChannel === 'undefined' || typeof qt === 'undefined' || !qt.webChannelTransport) {
        setTimeout(initWebChannel, 100);
        return;
    }

    new QWebChannel(qt.webChannelTransport, function(channel) {
        pyBridge = channel.objects.pyBridge;
        console.log("QWebChannel connected to pyBridge");
        if (pyBridge && pyBridge.onMapReady) {
            pyBridge.onMapReady();
        }
    });
}

// ----------------- Base Maps & Layer Control -----------------

function setBaseMap(type) {
    if (baseLayers[type]) {
        if (currentBaseLayer) map.removeLayer(currentBaseLayer);
        currentBaseLayer = baseLayers[type];
        currentBaseLayer.addTo(map);
    }
}

function toggleLayerVisibility(key, visible) {
    if (layerGroups[key]) {
        if (visible) {
            map.addLayer(layerGroups[key]);
        } else {
            map.removeLayer(layerGroups[key]);
        }
    }
}

// ----------------- Load & Render GeoJSON -----------------

function loadLayerGeoJson(layerKey, geoJson) {
    const group = layerGroups[layerKey];
    if (!group) return;

    group.clearLayers();
    featureMap[layerKey].clear();

    const layerStyle = STYLES[layerKey] || {};

    L.geoJSON(geoJson, {
        style: function(feature) {
            return layerStyle;
        },
        pointToLayer: function(feature, latlng) {
            const marker = L.circleMarker(latlng, layerStyle);
            return marker;
        },
        onEachFeature: function(feature, layer) {
            const fid = feature.id;
            featureMap[layerKey].set(fid, layer);

            let title = `${layerKey}: #${fid}`;
            if (feature.properties) {
                if (feature.properties.Nombre) title += ` - ${feature.properties.Nombre}`;
                else if (feature.properties.NroLote) title += ` - Lote ${feature.properties.NroLote}`;
                else if (feature.properties.UV_MZA) title += ` - MZA ${feature.properties.UV_MZA}`;
            }
            layer.bindTooltip(title, { sticky: true, className: 'sig-tooltip' });

            layer.on('click', function(e) {
                if (currentMode === 'navigate') {
                    L.DomEvent.stopPropagation(e);
                    selectFeature(layerKey, fid, layer);
                }
            });
        }
    }).addTo(group);
}

function updateFeatureInMap(layerKey, featureGeoJson) {
    const fid = featureGeoJson.id;
    const existing = featureMap[layerKey].get(fid);
    if (existing) {
        if (existing.remove) existing.remove();
        if (layerGroups[layerKey]) layerGroups[layerKey].removeLayer(existing);
        featureMap[layerKey].delete(fid);
    }

    const group = layerGroups[layerKey];
    const layerStyle = STYLES[layerKey] || {};
    let createdLeafletLayer = null;

    L.geoJSON(featureGeoJson, {
        style: () => layerStyle,
        pointToLayer: (feat, latlng) => L.circleMarker(latlng, layerStyle),
        onEachFeature: (feature, layer) => {
            createdLeafletLayer = layer;
            featureMap[layerKey].set(fid, layer);
            let title = `${layerKey}: #${fid}`;
            if (feature.properties && feature.properties.Nombre) title += ` - ${feature.properties.Nombre}`;
            else if (feature.properties && feature.properties.NroLote) title += ` - Lote ${feature.properties.NroLote}`;
            layer.bindTooltip(title, { sticky: true, className: 'sig-tooltip' });
            layer.on('click', (e) => {
                if (currentMode === 'navigate') {
                    L.DomEvent.stopPropagation(e);
                    selectFeature(layerKey, fid, layer);
                }
            });
        }
    }).addTo(group);

    if (createdLeafletLayer) {
        selectFeature(layerKey, fid, createdLeafletLayer);
        showToast(`Elemento #${fid} (${layerKey}) guardado y visible.`);
    }
}

function removeFeatureFromMap(layerKey, featureId) {
    const fid = parseInt(featureId);
    const existing = featureMap[layerKey].get(fid) || featureMap[layerKey].get(featureId);
    if (existing) {
        if (existing.remove) existing.remove();
        if (layerGroups[layerKey]) layerGroups[layerKey].removeLayer(existing);
        featureMap[layerKey].delete(fid);
        featureMap[layerKey].delete(featureId);
    }
    if (selectedFeatureId == featureId && selectedLayerKey === layerKey) {
        clearSelection();
    }
    showToast(`Elemento #${featureId} eliminado.`);
}

// ----------------- Selection & Vertex Editing -----------------

function selectFeature(layerKey, featureId, layer) {
    clearSelection();
    selectedLayerKey = layerKey;
    selectedFeatureId = featureId;

    if (layer.setStyle) {
        layer.setStyle(STYLES.selected);
    }
    selectedGraphic = layer;

    // Enable interactive vertex handles for editing existing vector
    enableVertexEditing(layerKey, featureId, layer);

    if (pyBridge && pyBridge.onFeatureSelected) {
        pyBridge.onFeatureSelected(layerKey, parseInt(featureId));
    }
}

function clearSelection() {
    disableVertexEditing();
    if (selectedGraphic && selectedLayerKey) {
        const origStyle = STYLES[selectedLayerKey];
        if (selectedGraphic.setStyle && origStyle) {
            selectedGraphic.setStyle(origStyle);
        }
    }
    selectedGraphic = null;
    selectedLayerKey = null;
    selectedFeatureId = null;
}

function enableVertexEditing(layerKey, featureId, layer) {
    disableVertexEditing();
    if (!layer) return;

    if (layer instanceof L.Polygon || layer instanceof L.Polyline) {
        let latlngs = layer.getLatLngs();
        let ring = Array.isArray(latlngs[0]) ? latlngs[0] : latlngs;

        // Si el polígono tiene punto de cierre repetido al final, editar sólo los vértices únicos
        let pointsToEdit = ring;
        if (layer instanceof L.Polygon && ring.length > 2) {
            const first = ring[0];
            const last = ring[ring.length - 1];
            if (Math.abs(first.lat - last.lat) < 1e-7 && Math.abs(first.lng - last.lng) < 1e-7) {
                pointsToEdit = ring.slice(0, ring.length - 1);
            }
        }

        pointsToEdit.forEach((ll, idx) => {
            const handle = L.circleMarker(ll, {
                radius: 6,
                color: '#ffffff',
                fillColor: '#0284c7',
                fillOpacity: 1,
                weight: 2
            }).addTo(map);

            handle.on('mousedown', (e) => {
                L.DomEvent.stopPropagation(e);
                map.dragging.disable();
                const onMove = (ev) => {
                    handle.setLatLng(ev.latlng);
                    ring[idx] = ev.latlng;
                    // Si se mueve el primer vértice y el polígono estaba cerrado, actualizar también el último
                    if (layer instanceof L.Polygon && idx === 0 && ring.length > pointsToEdit.length) {
                        ring[ring.length - 1] = ev.latlng;
                    }
                    layer.setLatLngs(latlngs);
                };
                const onUp = () => {
                    map.off('mousemove', onMove);
                    map.off('mouseup', onUp);
                    map.dragging.enable();
                    notifyGeometryModified(layerKey, featureId, layer);
                };
                map.on('mousemove', onMove);
                map.on('mouseup', onUp);
            });

            editVertexMarkers.push(handle);
        });
    } else if (layer instanceof L.CircleMarker) {
        const handle = L.circleMarker(layer.getLatLng(), {
            radius: 8,
            color: '#ffffff',
            fillColor: '#10b981',
            fillOpacity: 0.9,
            weight: 2
        }).addTo(map);

        handle.on('mousedown', (e) => {
            L.DomEvent.stopPropagation(e);
            map.dragging.disable();
            const onMove = (ev) => {
                handle.setLatLng(ev.latlng);
                layer.setLatLng(ev.latlng);
            };
            const onUp = () => {
                map.off('mousemove', onMove);
                map.off('mouseup', onUp);
                map.dragging.enable();
                notifyGeometryModified(layerKey, featureId, layer);
            };
            map.on('mousemove', onMove);
            map.on('mouseup', onUp);
        });
        editVertexMarkers.push(handle);
    }
}

function disableVertexEditing() {
    editVertexMarkers.forEach(m => map.removeLayer(m));
    editVertexMarkers = [];
}

function notifyGeometryModified(layerKey, featureId, layer) {
    if (!pyBridge || !pyBridge.onGeometryModified) return;

    if (layer instanceof L.Polygon) {
        let latlngs = layer.getLatLngs();
        let ring = Array.isArray(latlngs[0]) ? latlngs[0] : latlngs;
        let coords = ring.map(p => [p.lng, p.lat]);
        if (coords.length >= 3) {
            const first = coords[0];
            const last = coords[coords.length - 1];
            const isClosed = Math.abs(first[0] - last[0]) < 1e-9 && Math.abs(first[1] - last[1]) < 1e-9;
            if (!isClosed) {
                coords.push([first[0], first[1]]);
            }
        }
        pyBridge.onGeometryModified(layerKey, featureId, 'Polygon', JSON.stringify([coords]));
        showToast(`Geometría de #${featureId} actualizada`);
    } else if (layer instanceof L.Polyline) {
        let latlngs = layer.getLatLngs();
        let coords = latlngs.map(p => [p.lng, p.lat]);
        pyBridge.onGeometryModified(layerKey, featureId, 'LineString', JSON.stringify(coords));
        showToast(`Geometría de #${featureId} actualizada`);
    } else if (layer instanceof L.CircleMarker) {
        let p = layer.getLatLng();
        pyBridge.onGeometryModified(layerKey, featureId, 'Point', JSON.stringify([p.lng, p.lat]));
        showToast(`Posición de #${featureId} actualizada`);
    }
}

// ----------------- Mouse & Mode Handlers -----------------

function onMapMouseMove(e) {
    const lat = e.latlng.lat;
    const lon = e.latlng.lng;
    
    if (pyBridge && pyBridge.onMouseMove) {
        pyBridge.onMouseMove(lat, lon);
    }

    const hudCoords = document.getElementById('hudCoords');
    if (hudCoords) {
        hudCoords.innerText = `Lat: ${lat.toFixed(5)}, Lon: ${lon.toFixed(5)} | Zoom: ${map.getZoom()}`;
    }

    // Live guide line when drawing polygon or polyline
    if ((currentMode === 'draw_polygon' || currentMode === 'draw_line') && drawPoints.length > 0) {
        const lastPt = drawPoints[drawPoints.length - 1];
        if (!liveGuideLine) {
            liveGuideLine = L.polyline([lastPt, e.latlng], {
                color: '#38bdf8',
                weight: 2,
                dashArray: '3, 6'
            }).addTo(map);
        } else {
            liveGuideLine.setLatLngs([lastPt, e.latlng]);
        }
    }

    // Handle ROI drag rectangle
    if ((currentMode === 'select_roi' || currentMode === 'delete_box') && roiStartLatLng) {
        const bounds = L.latLngBounds(roiStartLatLng, e.latlng);
        const isDelete = currentMode === 'delete_box';
        if (!roiRect) {
            roiRect = L.rectangle(bounds, {
                color: isDelete ? '#ef4444' : '#f59e0b',
                weight: 2,
                dashArray: '5, 5',
                fillColor: isDelete ? '#dc2626' : '#fbbf24',
                fillOpacity: isDelete ? 0.25 : 0.15
            }).addTo(layerGroups.roi);
        } else {
            roiRect.setBounds(bounds);
        }
    }
}

function setInteractionMode(mode, layerKey) {
    currentMode = mode;
    activeDrawLayer = layerKey || 'lotes';
    cancelActiveDrawing();
    
    const modeLabels = {
        'navigate': 'Modo: Exploración / Selección (Clic para editar, Supr para borrar, Ctrl+Z deshacer)',
        'draw_polygon': `Modo: Dibujar Polígono (${activeDrawLayer})`,
        'draw_point': `Modo: Agregar Punto (${activeDrawLayer})`,
        'draw_line': `Modo: Dibujar Línea (${activeDrawLayer})`,
        'select_roi': 'Modo: Seleccionar Cuadro con Mouse',
        'select_roi_polygon': 'Modo: Seleccionar Área por Puntos (Doble clic termina)',
        'delete_box': 'Modo: Arrastrar Cuadro para Eliminar Sección'
    };

    const ind = document.getElementById('modeIndicator');
    if (ind) {
        ind.innerText = modeLabels[mode] || mode;
    }

    if (mode === 'select_roi' || mode === 'delete_box') {
        map.dragging.disable();
    } else {
        map.dragging.enable();
    }
}

function cancelActiveDrawing() {
    drawPoints = [];
    if (drawTempPolyline) {
        map.removeLayer(drawTempPolyline);
        drawTempPolyline = null;
    }
    if (liveGuideLine) {
        map.removeLayer(liveGuideLine);
        liveGuideLine = null;
    }
    drawTempMarkers.forEach(m => map.removeLayer(m));
    drawTempMarkers = [];
    roiStartLatLng = null;
    if (roiRect && layerGroups.roi) {
        layerGroups.roi.clearLayers();
        roiRect = null;
    }
}

function onMapMouseDown(e) {
    if (currentMode === 'select_roi' || currentMode === 'delete_box') {
        roiStartLatLng = e.latlng;
        if (layerGroups.roi) layerGroups.roi.clearLayers();
        roiRect = null;
    }
}

function onMapMouseUp(e) {
    if ((currentMode === 'select_roi' || currentMode === 'delete_box') && roiStartLatLng) {
        const b = L.latLngBounds(roiStartLatLng, e.latlng);
        const isDelete = currentMode === 'delete_box';
        roiStartLatLng = null;

        const minLon = Math.min(b.getWest(), b.getEast());
        const maxLon = Math.max(b.getWest(), b.getEast());
        const minLat = Math.min(b.getSouth(), b.getNorth());
        const maxLat = Math.max(b.getSouth(), b.getNorth());

        if (Math.abs(maxLon - minLon) > 0.0001 && Math.abs(maxLat - minLat) > 0.0001) {
            if (isDelete) {
                if (pyBridge && pyBridge.onDeleteBoxSelected) {
                    pyBridge.onDeleteBoxSelected(minLon, minLat, maxLon, maxLat);
                }
            } else {
                if (pyBridge && pyBridge.onRoiSelected) {
                    pyBridge.onRoiSelected(minLon, minLat, maxLon, maxLat);
                }
            }
        }
        setInteractionMode('navigate');
    }
}

function onMapClick(e) {
    if (currentMode === 'draw_point') {
        const lon = e.latlng.lng;
        const lat = e.latlng.lat;
        if (pyBridge && pyBridge.onFeatureCreated) {
            pyBridge.onFeatureCreated(activeDrawLayer, 'Point', JSON.stringify([lon, lat]));
        }
        setInteractionMode('navigate');
    } else if (currentMode === 'draw_polygon' || currentMode === 'select_roi_polygon') {
        addDrawVertex(e.latlng, true);
    } else if (currentMode === 'draw_line') {
        addDrawVertex(e.latlng, false);
    }
}

function onMapDblClick(e) {
    if (currentMode === 'draw_polygon' || currentMode === 'draw_line' || currentMode === 'select_roi_polygon') {
        L.DomEvent.stopPropagation(e);
        finishDrawing();
    }
}

function addDrawVertex(latlng, isPolygon) {
    drawPoints.push(latlng);

    const isRoiPoly = currentMode === 'select_roi_polygon';
    const m = L.circleMarker(latlng, {
        radius: 5,
        color: '#ffffff',
        fillColor: isRoiPoly ? '#10b981' : '#38bdf8',
        fillOpacity: 1,
        weight: 2
    }).addTo(map);
    drawTempMarkers.push(m);

    if (drawPoints.length > 1) {
        if (!drawTempPolyline) {
            drawTempPolyline = L.polyline(drawPoints, {
                color: isRoiPoly ? '#10b981' : '#38bdf8',
                dashArray: isRoiPoly ? '4, 4' : null,
                weight: 2.5
            }).addTo(map);
        } else {
            drawTempPolyline.setLatLngs(drawPoints);
        }
    }
}

function finishDrawing() {
    if (drawPoints.length < 2) {
        cancelActiveDrawing();
        return;
    }

    if (currentMode === 'select_roi_polygon') {
        if (drawPoints.length >= 3) {
            const bounds = L.latLngBounds(drawPoints);
            const minLon = bounds.getWest();
            const maxLon = bounds.getEast();
            const minLat = bounds.getSouth();
            const maxLat = bounds.getNorth();
            if (pyBridge && pyBridge.onRoiSelected) {
                pyBridge.onRoiSelected(minLon, minLat, maxLon, maxLat);
            }
        }
    } else if (currentMode === 'draw_polygon') {
        if (drawPoints.length < 3) {
            cancelActiveDrawing();
            return;
        }
        const ring = drawPoints.map(p => [p.lng, p.lat]);
        const first = ring[0];
        const last = ring[ring.length - 1];
        if (Math.abs(first[0] - last[0]) > 1e-9 || Math.abs(first[1] - last[1]) > 1e-9) {
            ring.push([first[0], first[1]]);
        }
        if (pyBridge && pyBridge.onFeatureCreated) {
            pyBridge.onFeatureCreated(activeDrawLayer, 'Polygon', JSON.stringify([ring]));
        }
    } else if (currentMode === 'draw_line') {
        const pts = drawPoints.map(p => [p.lng, p.lat]);
        if (pyBridge && pyBridge.onFeatureCreated) {
            pyBridge.onFeatureCreated(activeDrawLayer, 'LineString', JSON.stringify(pts));
        }
    }

    cancelActiveDrawing();
    setInteractionMode('navigate');
}

function undoLastDrawVertex() {
    if (drawPoints.length === 0) return;

    drawPoints.pop();

    if (drawTempMarkers.length > 0) {
        const lastMarker = drawTempMarkers.pop();
        map.removeLayer(lastMarker);
    }

    if (drawPoints.length > 1) {
        if (drawTempPolyline) {
            drawTempPolyline.setLatLngs(drawPoints);
        }
    } else {
        if (drawTempPolyline) {
            map.removeLayer(drawTempPolyline);
            drawTempPolyline = null;
        }
    }

    if (liveGuideLine) {
        if (drawPoints.length === 0) {
            map.removeLayer(liveGuideLine);
            liveGuideLine = null;
        }
    }

    showToast(`Punto deshecho. Vértices activos: ${drawPoints.length}`);
}

function flyToExtent(minLon, minLat, maxLon, maxLat) {
    if (!map) return;
    const bounds = L.latLngBounds([[minLat, minLon], [maxLat, maxLon]]);
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 18 });
}

function showToast(message) {
    const existing = document.querySelector('.sig-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'sig-toast';
    toast.innerText = message;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 400);
    }, 2500);
}

function onKeyDown(e) {
    if (e.key === 'Backspace') {
        if ((currentMode === 'draw_polygon' || currentMode === 'draw_line' || currentMode === 'select_roi_polygon') && drawPoints.length > 0) {
            e.preventDefault();
            undoLastDrawVertex();
            return;
        }
        if (selectedLayerKey && selectedFeatureId !== null) {
            if (pyBridge && pyBridge.onFeatureDeleteRequested) {
                pyBridge.onFeatureDeleteRequested(selectedLayerKey, selectedFeatureId);
            }
        }
    } else if (e.key === 'Delete') {
        if (selectedLayerKey && selectedFeatureId !== null) {
            if (pyBridge && pyBridge.onFeatureDeleteRequested) {
                pyBridge.onFeatureDeleteRequested(selectedLayerKey, selectedFeatureId);
            }
        }
    } else if (e.key === 'z' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        // Si se está trazando activamente un polígono o línea con el mouse, deshacer sólo el último punto
        if ((currentMode === 'draw_polygon' || currentMode === 'draw_line' || currentMode === 'select_roi_polygon') && drawPoints.length > 0) {
            undoLastDrawVertex();
            return;
        }
        if (pyBridge && pyBridge.onUndoRequested) {
            pyBridge.onUndoRequested();
        }
    } else if (e.key === 'Escape') {
        cancelActiveDrawing();
        setInteractionMode('navigate');
    }
}

window.addEventListener('keydown', onKeyDown);
window.addEventListener('DOMContentLoaded', initMap);
