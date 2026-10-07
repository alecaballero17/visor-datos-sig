// ── Motor de mapa Arquis ─────────────────────────────────────────────────────
// Inicializado desde Blazor: JS.InvokeVoidAsync("arquis.init", dotNetRef)
// ────────────────────────────────────────────────────────────────────────────
window.arquis = (() => {
    let map, api, dotNetRef = null;
    const layerState = new Map();
    let selectedLayer = null, selectedId = null, selectedFeature = null;
    let selectedGraphic = null, selectedHaloGraphic = null, selectionLabel = null;
    let refreshTimer = null, detailVersion = 0, refreshVersion = 0;
    let currentWaterFilter = 'all'; // 'all', 'with', 'without'

    /* helpers */
    const esc = v => String(v ?? '').replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
    const titleOf = k => ({ manzanas: 'Manzanas', lotes: 'Lotes', codigosfijos: 'Códigos fijos', vias: 'Vías' }[k] || k);
    const waterSymbol = has => `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15h6v-4h11v4h5v6h-6v-2H10v2H4zM15 11V6M10 6h10"/><path d="M23 24s-3 3-3 4a3 3 0 0 0 6 0c0-1-3-4-3-4z"/>${has ? '' : '<path d="M4 4l24 24" stroke-width="3"/>'}</svg>`;
    const $ = id => document.getElementById(id);
    const ww = () => $('showWithWater');
    const wo = () => $('showWithoutWater');

    /* filtros agua */
    function waterVisible(key, feature) {
        if (currentWaterFilter === 'with') {
            if (key === 'codigosfijos') return true;
            if (key === 'lotes') return feature.properties?.TieneAgua === true;
            return true;
        }
        if (currentWaterFilter === 'without') {
            if (key === 'codigosfijos') return false;
            if (key === 'lotes') return feature.properties?.TieneAgua !== true;
            return true;
        }

        // Si no se usa filtro global, usar checkboxes tradicionales del sidebar si existen
        if (key === 'codigosfijos') return ww()?.checked ?? true;
        if (key === 'lotes') return (feature.properties?.TieneAgua ? ww() : wo())?.checked ?? true;
        return true;
    }

    /* capas */
    function syncSymbols(st) {
        if (st.visible && map && map.getZoom() >= 17) st.symbols.addTo(map);
        else if (map) map.removeLayer(st.symbols);
    }
    function renderLayer(st) {
        if (!st) return;
        st.group.clearLayers(); st.symbols.clearLayers();
        if (st.data) st.group.addData(st.data);
        syncSymbols(st);
    }
    function applyWaterFilters() {
        for (const [key, st] of layerState) {
            if (key === 'lotes' || key === 'codigosfijos') renderLayer(st);
        }
        if (selectedFeature && !waterVisible(selectedLayer, selectedFeature)) {
            clearSelectionGraphics();
            selectedFeature = selectedLayer = selectedId = null;
            ++detailVersion;
            $('detailPanel')?.classList.add('d-none');
        }
        renderLegend();
    }

    /* estilos */
    function styleFor(key, meta) {
        return _f => {
            if (key === 'codigosfijos') return meta.style || {};
            if (key === 'lotes') return { color: meta.style?.color || '#38bdf8', weight: 1.5, fillOpacity: .14 };
            return { color: meta.style?.color || '#333', weight: meta.style?.weight || 2, fillOpacity: meta.style?.fillOpacity ?? 0.08 };
        };
    }
    function waterMarker(latlng, has, label) {
        const icon = L.divIcon({ className: `water-marker ${has ? 'water-yes' : 'water-no'}`, html: `<span>${waterSymbol(has)}</span>`, iconSize: [22, 22], iconAnchor: [11, 11] });
        return L.marker(latlng, { icon, title: label }).bindTooltip(esc(label));
    }
    function pointFor(meta, feature, latlng) {
        return L.circleMarker(latlng, { radius: 3, color: meta.style?.color || '#f59e0b', weight: 1, fillOpacity: .8 })
            .bindTooltip(esc(`Código fijo ${feature.properties?.CodFijo ?? feature.id}`));
    }

    /* leyenda */
    function renderLegend() {
        const legend = $('legend'); if (!legend) return;
        const has = currentWaterFilter !== 'without' && (ww()?.checked ?? true);
        const sin = currentWaterFilter !== 'with' && (wo()?.checked ?? true);
        legend.innerHTML = '';
        for (const [key, st] of layerState) {
            if (!st.visible) continue;
            if (key === 'codigosfijos') {
                if (has) legend.insertAdjacentHTML('beforeend', `<div class="small mb-2"><span class="legend-dot" style="background:#f59e0b"></span>Códigos fijos</div>`);
            } else if (key === 'lotes') {
                if (has || sin) legend.insertAdjacentHTML('beforeend', `<div class="small mb-2"><span class="legend-swatch" style="background:${st.meta.style?.color || '#38bdf8'}"></span>Lotes</div>`);
                if (has) legend.insertAdjacentHTML('beforeend', `<div class="small mb-2 water-legend"><span class="water-yes">${waterSymbol(true)}</span>Con agua</div>`);
                if (sin) legend.insertAdjacentHTML('beforeend', `<div class="small mb-2 water-legend"><span class="water-no">${waterSymbol(false)}</span>Sin agua</div>`);
            } else {
                legend.insertAdjacentHTML('beforeend', `<div class="small mb-2"><span class="legend-swatch" style="background:${st.meta.style?.color || '#333'}"></span>${esc(st.meta.title)}</div>`);
            }
        }
        if (!legend.children.length) legend.innerHTML = '<span class="small text-secondary">Sin capas visibles.</span>';
    }

    /* refresh */
    function currentBbox() { if (!map) return ''; const b = map.getBounds(); return [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].join(','); }
    async function refreshVisibleLayers() {
        if (!map) return;
        const version = ++refreshVersion;
        $('loading')?.classList.remove('d-none');
        try {
            const jobs = [];
            for (const [key, st] of layerState) {
                if (!st.visible) continue;
                const limit = key === 'lotes' ? 1200 : key === 'codigosfijos' ? 1200 : 1200;
                jobs.push((async () => {
                    const r = await fetch(`${api}/api/capas/${key}/geojson?bbox=${encodeURIComponent(currentBbox())}&limit=${limit}`, { credentials: 'include' });
                    if (!r.ok) return;
                    const gj = await r.json();
                    if (version !== refreshVersion) return;
                    st.data = gj; renderLayer(st);
                })());
            }
            await Promise.all(jobs);
        } finally { if (version === refreshVersion) $('loading')?.classList.add('d-none'); }
    }
    function scheduleRefresh() { clearTimeout(refreshTimer); refreshTimer = setTimeout(refreshVisibleLayers, 250); }

    /* metadatos */
    async function loadMetadata() {
        const r = await fetch(`${api}/api/capas`, { credentials: 'include' });
        if (r.status === 401) { location.href = '/'; return; }
        if (!r.ok) throw new Error('No se pudo cargar el catálogo de capas.');
        const metas = await r.json();
        const ctl = $('layerControl'); if (ctl) ctl.innerHTML = '';

        metas.forEach(meta => {
            const key = meta.key, symbols = L.layerGroup();
            const g = L.geoJSON(null, {
                filter: f => waterVisible(key, f),
                style: styleFor(key, meta),
                pointToLayer: (f, ll) => pointFor(meta, f, ll),
                onEachFeature: (feature, layer) => {
                    layer.on('click', (e) => {
                        L.DomEvent.stopPropagation(e);
                        selectFeature(key, feature, layer);
                    });
                    if (key === 'lotes') {
                        const p = feature.properties;
                        if (p && p.AguaLatitud && p.AguaLongitud) {
                            waterMarker([p.AguaLatitud, p.AguaLongitud], p.TieneAgua, `${p.TieneAgua ? 'Con agua' : 'Sin agua'} · Lote ${p.NroLote ?? feature.id}`)
                                .on('click', (e) => {
                                    L.DomEvent.stopPropagation(e);
                                    selectFeature(key, feature, layer);
                                }).addTo(symbols);
                        }
                    }
                }
            });
            const state = { meta, group: g, symbols, visible: true };
            layerState.set(key, state); g.addTo(map); syncSymbols(state);

            if (ctl) {
                const id = `layer-${key}`;
                ctl.insertAdjacentHTML('beforeend', `<div class="form-check"><input class="form-check-input" type="checkbox" id="${id}" checked><label class="form-check-label" for="${id}">${esc(meta.title)}</label></div>`);
                $(id).addEventListener('change', e => {
                    const st = layerState.get(key); if (!st) return;
                    st.visible = e.target.checked;
                    if (st.visible) st.group.addTo(map); else map.removeLayer(st.group);
                    syncSymbols(st); renderLegend(); scheduleRefresh();
                });
            }
        });

        renderLegend();
        const extents = metas.map(x => x.extent).filter(x => Array.isArray(x) && x.length === 4);
        if (extents.length) {
            const minX = Math.min(...extents.map(x => Number(x[0])));
            const minY = Math.min(...extents.map(x => Number(x[1])));
            const maxX = Math.max(...extents.map(x => Number(x[2])));
            const maxY = Math.max(...extents.map(x => Number(x[3])));
            if ([minX, minY, maxX, maxY].every(Number.isFinite) && Math.abs(minY) <= 90 && Math.abs(maxY) <= 90) {
                map.fitBounds([[minY, minX], [maxY, maxX]], { padding: [20, 20] });
            }
        }
        await refreshVisibleLayers();
    }

    /* selección y alumbrado */
    function clearSelectionGraphics() {
        if (selectedGraphic && map) map.removeLayer(selectedGraphic);
        if (selectedHaloGraphic && map) map.removeLayer(selectedHaloGraphic);
        if (selectionLabel && map) map.removeLayer(selectionLabel);
        selectedGraphic = selectedHaloGraphic = selectionLabel = null;
    }

    function selectionName(key, feature) {
        const p = feature.properties || {};
        if (key === 'vias') return p.Nombre || 'Vía seleccionada';
        if (key === 'lotes') return `Lote ${p.NroLote ?? feature.id}`;
        if (key === 'manzanas') return `UV ${p.UV ?? '-'} · MZA ${p.MZA ?? feature.id}`;
        return `Código ${p.CodFijo ?? feature.id}`;
    }

    function selectFeature(key, feature, layer, flyTo = false) {
        if (!waterVisible(key, feature)) {
            const rs = $('resultStatus'); if (rs) rs.textContent = 'La entidad está oculta por el filtro de agua.';
            return;
        }
        selectedFeature = feature; selectedLayer = key; selectedId = feature.id;
        clearSelectionGraphics();

        try {
            selectedGraphic = L.geoJSON(feature, {
                pane: 'selectionPane', interactive: false,
                style: {
                    color: '#1a73e8',
                    weight: 3.5,
                    opacity: 0.95,
                    fillColor: '#1a73e8',
                    fillOpacity: 0.18,
                    lineCap: 'round',
                    lineJoin: 'round'
                },
                pointToLayer: (_, ll) => L.circleMarker(ll, {
                    pane: 'selectionPane',
                    radius: 9,
                    color: '#ffffff',
                    weight: 3,
                    fillColor: '#1a73e8',
                    fillOpacity: 1
                })
            }).addTo(map);

            selectedGraphic.eachLayer(i => i.bringToFront?.());

            // Cálculo seguro de coordenadas centrales para evitar NaN
            let centerLatLng = null;
            if (feature.geometry && feature.geometry.type === 'Point' && Array.isArray(feature.geometry.coordinates)) {
                const lng = Number(feature.geometry.coordinates[0]);
                const lat = Number(feature.geometry.coordinates[1]);
                if (Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90) {
                    centerLatLng = L.latLng(lat, lng);
                }
            } else if (selectedGraphic && typeof selectedGraphic.getBounds === 'function') {
                try {
                    const bounds = selectedGraphic.getBounds();
                    if (bounds && typeof bounds.isValid === 'function' && bounds.isValid()) {
                        const c = bounds.getCenter();
                        if (c && Number.isFinite(c.lat) && Number.isFinite(c.lng) && Math.abs(c.lat) <= 90) {
                            centerLatLng = c;
                        }
                    }
                } catch (_) {}
            }

            if (centerLatLng) {
                selectionLabel = L.marker(centerLatLng, {
                    interactive: false,
                    icon: L.divIcon({
                        className: 'selection-label-clean',
                        html: `<span class="google-pin-label">${esc(selectionName(key, feature))}</span>`,
                        iconAnchor: [0, 32]
                    })
                }).addTo(map);
            }

            if (flyTo) {
                if (Array.isArray(feature.bbox) && feature.bbox.length >= 4) {
                    flyToBbox(feature.bbox);
                } else if (centerLatLng) {
                    map.flyTo(centerLatLng, Math.max(map.getZoom(), 18), { animate: true, duration: 1.0 });
                }
            }
        } catch (e) {
            console.warn('Error dibujando selección gráfica:', e);
        }

        // Notificar a Blazor reactivamente
        if (dotNetRef) {
            try {
                dotNetRef.invokeMethodAsync(
                    'OnFeatureSelectedFromMap',
                    key,
                    Number(feature.id),
                    JSON.stringify(feature.properties || {}),
                    feature.bbox || null
                );
            } catch (err) {
                console.warn('Error notificando a Blazor:', err);
            }
        }

        showDetail(key, feature);
        document.querySelectorAll('.result-item').forEach(x => x.classList.toggle('active', x.dataset.layer === key && String(x.dataset.id) === String(feature.id)));
    }

    function flyToBbox(bbox) {
        if (!map || !Array.isArray(bbox) || bbox.length < 4) return;
        const minX = Number(bbox[0]);
        const minY = Number(bbox[1]);
        const maxX = Number(bbox[2]);
        const maxY = Number(bbox[3]);

        if (![minX, minY, maxX, maxY].every(Number.isFinite)) return;
        if (Math.abs(minY) > 90 || Math.abs(maxY) > 90) return;

        // Si es un punto o bbox plano (minX == maxX)
        const isPoint = Math.abs(minX - maxX) < 0.0000001 && Math.abs(minY - maxY) < 0.0000001;
        if (isPoint) {
            map.flyTo([minY, minX], Math.max(map.getZoom(), 18), { animate: true, duration: 1.0 });
        } else {
            const south = Math.min(minY, maxY);
            const north = Math.max(minY, maxY);
            const west = Math.min(minX, maxX);
            const east = Math.max(minX, maxX);
            map.flyToBounds([[south, west], [north, east]], { padding: [50, 50], maxZoom: 19, animate: true, duration: 1.0 });
        }
    }

    /* detalle en DOM legacy (compatibilidad) */
    function showDetail(key, feature) {
        const panel = $('detailPanel'), content = $('detailContent');
        if (!panel || !content) return;
        const version = ++detailVersion, water = key === 'codigosfijos' || key === 'lotes';
        let html = `<div class="small text-secondary mb-2">${titleOf(key)} · ID ${esc(feature.id ?? '')}</div>`;
        if (water) html += '<section id="waterDetail"><h3 class="h6">Agua potable</h3><p class="small anim-pulse">Consultando datos…</p></section>';
        content.innerHTML = html;
        if (water) loadWaterDetail(key, feature.id, version);
    }

    async function loadWaterDetail(key, id, version) {
        const alive = () => version === detailVersion && !$('detailPanel')?.classList.contains('d-none');
        try {
            const r = await fetch(`${api}/api/agua-potable/${key === 'lotes' ? 'lotes' : 'codigos'}/${id}`, { credentials: 'include' });
            if (!r.ok || !alive()) return;
            const ficha = await r.json();
            const section = $('waterDetail'); if (!section) return;
            let html = `<h3 class="h6">Agua potable</h3><p class="fw-semibold ${ficha.tieneAgua ? 'text-primary' : 'text-danger'}">${ficha.tieneAgua ? 'Con código fijo' : 'Sin código fijo'}</p>`;
            section.innerHTML = html;
        } catch (_) {}
    }

    /* búsqueda legacy del sidebar */
    async function doSearch() {
        const text = $('searchText')?.value.trim();
        const rs = $('resultStatus'), res = $('results'), rc = $('resultCount');
        if (!text) { if (rs) rs.textContent = 'Escriba un criterio de búsqueda.'; return; }
        if (rs) rs.textContent = 'Buscando…'; if (res) res.innerHTML = '';
        const r = await fetch(`${api}/api/busqueda?texto=${encodeURIComponent(text)}&tamano=100`, { credentials: 'include' });
        if (!r.ok) { if (rs) rs.textContent = 'No se pudo ejecutar la búsqueda.'; return; }
        const rows = await r.json();
        if (rc) rc.textContent = rows.length;
        if (!rows.length) { if (rs) rs.textContent = 'Sin resultados.'; return; }
        if (rs) rs.textContent = `${rows.length} resultado(s). Seleccione uno para acercar.`;
        rows.forEach(row => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'list-group-item list-group-item-action result-item';
            btn.dataset.layer = row.layer; btn.dataset.id = row.id;
            btn.innerHTML = `<div class="fw-semibold">${esc(row.label)}</div><small class="text-secondary">${titleOf(row.layer)} · ID ${row.id}</small>`;
            btn.addEventListener('click', () => highlightFeature(row.layer, row.id, true));
            res?.appendChild(btn);
        });
    }

    async function highlightFeature(layer, id, flyTo = true) {
        try {
            const r = await fetch(`${api}/api/capas/${layer}/${id}`, { credentials: 'include' });
            if (!r.ok) return;
            const feature = await r.json();
            selectFeature(layer, feature, null, flyTo);
        } catch (e) {
            console.error('Error resaltando entidad:', e);
        }
    }

    function clearResults() {
        if ($('results')) $('results').innerHTML = '';
        if ($('resultCount')) $('resultCount').textContent = '0';
        if ($('resultStatus')) $('resultStatus').textContent = 'Sin consulta activa.';
        if ($('searchText')) $('searchText').value = '';
        clearSelectionGraphics();
        $('detailPanel')?.classList.add('d-none');
    }

    /* control de filtros desde Blazor */
    function setWaterFilter(mode) {
        // mode: 'all' (0), 'with' (1), 'without' (2)
        if (mode === 0 || mode === '0' || mode === 'Todos' || mode === 'all') currentWaterFilter = 'all';
        else if (mode === 1 || mode === '1' || mode === 'SoloConAgua' || mode === 'with') currentWaterFilter = 'with';
        else if (mode === 2 || mode === '2' || mode === 'SoloSinAgua' || mode === 'without') currentWaterFilter = 'without';
        else currentWaterFilter = 'all';

        applyWaterFilters();
    }

    function setLayerVisibility(key, visible) {
        const st = layerState.get(key);
        if (!st || !map) return;
        st.visible = !!visible;
        if (st.visible) st.group.addTo(map); else map.removeLayer(st.group);
        syncSymbols(st); renderLegend(); scheduleRefresh();
    }

    function centerOnCoords(lat, lon, zoom = 18) {
        const latN = Number(lat);
        const lonN = Number(lon);
        if (map && Number.isFinite(latN) && Number.isFinite(lonN) && Math.abs(latN) <= 90) {
            map.flyTo([latN, lonN], zoom, { animate: true, duration: 1.0 });
        }
    }

    /* init */
    async function init(dotNet) {
        if (dotNet) dotNetRef = dotNet;
        const appEl = $('app');
        api = (appEl?.dataset?.api || '').replace(/\/$/, '');

        if (!map) {
            map = L.map('map', { zoomControl: false, preferCanvas: true }).setView([-16.400, -60.960], 15);
            L.control.zoom({ position: 'bottomright' }).addTo(map);
            map.createPane('selectionPane').style.zIndex = 650;
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { 
                maxZoom: 22, 
                maxNativeZoom: 19, 
                attribution: '&copy; OpenStreetMap contributors' 
            }).addTo(map);
            L.control.scale({ imperial: false, position: 'bottomright' }).addTo(map);

            map.on('mousemove', e => { const el = $('coords'); if (el) el.textContent = `Lon: ${e.latlng.lng.toFixed(6)} · Lat: ${e.latlng.lat.toFixed(6)}`; });
            map.on('moveend', scheduleRefresh);
            map.on('zoomend', () => { for (const st of layerState.values()) syncSymbols(st); });

            // Click en fondo del mapa limpia selección
            map.on('click', () => {
                clearSelectionGraphics();
                if (dotNetRef) {
                    try { dotNetRef.invokeMethodAsync('OnClearSelectionFromMap'); } catch (_) {}
                }
            });

            window.addEventListener('resize', () => {
                if (map) map.invalidateSize();
            });
        }

        // Forzar cálculo de dimensiones de Leaflet para prevenir mapa en blanco
        setTimeout(() => { if (map) map.invalidateSize(); }, 60);
        setTimeout(() => { if (map) map.invalidateSize(); }, 250);
        setTimeout(() => { if (map) map.invalidateSize(); }, 700);

        $('showWithWater')?.addEventListener('change', applyWaterFilters);
        $('showWithoutWater')?.addEventListener('change', applyWaterFilters);
        $('searchBtn')?.addEventListener('click', doSearch);
        $('searchText')?.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
        $('clearBtn')?.addEventListener('click', clearResults);
        $('detailClose')?.addEventListener('click', () => $('detailPanel')?.classList.add('d-none'));
        $('toggleSidebar')?.addEventListener('click', () => $('sidebar')?.classList.toggle('open'));

        try { await loadMetadata(); }
        catch (e) {
            const rs = $('resultStatus');
            if (rs) rs.textContent = 'No se pudo conectar con el catálogo cartográfico. Por favor verifica que el servidor esté en funcionamiento.';
            if (dotNetRef) {
                try {
                    dotNetRef.invokeMethodAsync('OnMapError', 'Servidor de Mapas No Disponible', 'No fue posible cargar las capas territoriales. Verifica que el backend esté activo.');
                } catch (_) {}
            }
        }
    }

    return {
        init,
        highlightFeature,
        clearHighlight: clearSelectionGraphics,
        flyToBbox,
        setWaterFilter,
        setLayerVisibility,
        centerOnCoords
    };
})();

// Compatibilidad con invocaciones antiguas
window.mapInterop = {
    flyToBbox: (b) => window.arquis?.flyToBbox?.(b),
    initializeMap: () => {},
    updateLayer: () => {},
    removeLayer: () => {}
};
