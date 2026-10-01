window.mapInterop = {
    map: null,
    layerGroups: {},
    dotNetRef: null,

    initializeMap: function (elementId, dotNetRef, lat, lng, zoom) {
        this.dotNetRef = dotNetRef;
        this.map = L.map(elementId).setView([lat, lng], zoom);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 20,
            attribution: '© OpenStreetMap'
        }).addTo(this.map);

        this.map.on('moveend', () => {
            const bounds = this.map.getBounds();
            const bbox = `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;
            this.dotNetRef.invokeMethodAsync('OnMapMoveEnd', bbox);
        });
    },

    // Colores por Estado del código fijo
    _codigoColor: function(estado) {
        const colores = {
            1: '#22c55e', // Activo - verde
            2: '#ef4444', // Cortado - rojo
            3: '#f59e0b', // Pendiente - ámbar
            4: '#8b5cf6', // Inactivo - violeta
        };
        return colores[estado] || '#64748b';
    },

    updateLayer: function (layerId, geoJsonData, color, weight, fillOpacity) {
        if (this.layerGroups[layerId]) {
            this.map.removeLayer(this.layerGroups[layerId]);
        }

        const style = { color: color, weight: weight, fillOpacity: fillOpacity };
        const self = this;

        this.layerGroups[layerId] = L.geoJSON(geoJsonData, {
            style: style,
            // Renderizar puntos (CodigosFijos) como círculos coloreados por categoría
            pointToLayer: function(feature, latlng) {
                const p = feature.properties || {};
                const estado = p.Estado || p.estado || 0;
                const col = self._codigoColor(estado);
                return L.circleMarker(latlng, {
                    radius: 6,
                    fillColor: col,
                    color: '#fff',
                    weight: 1.5,
                    opacity: 1,
                    fillOpacity: 0.9
                });
            },
            onEachFeature: function (feature, layer) {
                const p = feature.properties || {};
                // Popup con datos relevantes
                const estadoLabel = { 1: 'Activo', 2: 'Cortado', 3: 'Pendiente', 4: 'Inactivo' };
                let popupHtml = `<div style="min-width:180px;font-size:13px">`;
                if (p.CodFijo || p.codFijo)   popupHtml += `<b>Cód. Fijo:</b> ${p.CodFijo ?? p.codFijo}<br>`;
                if (p.CodF_SIG || p.codF_SIG) popupHtml += `<b>Cód. SIG:</b> ${p.CodF_SIG ?? p.codF_SIG}<br>`;
                if (p.Nombre || p.nombre)      popupHtml += `<b>Nombre:</b> ${p.Nombre ?? p.nombre}<br>`;
                if (p.Estado != null)          popupHtml += `<b>Estado:</b> ${estadoLabel[p.Estado] ?? p.Estado}<br>`;
                if (p.UV_MZA || p.uV_MZA)     popupHtml += `<b>UV/MZA:</b> ${p.UV_MZA ?? p.uV_MZA}<br>`;
                if (p.NroLote || p.nroLote)    popupHtml += `<b>Lote:</b> ${p.NroLote ?? p.nroLote}<br>`;
                if (p.IdManzana || p.idManzana) popupHtml += `<b>Manzana:</b> ${p.IdManzana ?? p.idManzana}<br>`;
                popupHtml += `</div>`;
                layer.bindPopup(popupHtml);

                layer.on('click', function () {
                    self.dotNetRef.invokeMethodAsync('OnFeatureClicked', layerId, JSON.stringify(feature));
                });
            }
        }).addTo(this.map);
    },

    removeLayer: function (layerId) {
        if (this.layerGroups[layerId]) {
            this.map.removeLayer(this.layerGroups[layerId]);
            delete this.layerGroups[layerId];
        }
    },

    // Volar a un bbox [minX, minY, maxX, maxY] o a un punto [lng, lat]
    flyToBbox: function (bbox) {
        if (!this.map || !bbox || bbox.length < 4) return;
        const [minX, minY, maxX, maxY] = bbox;
        if (minX === maxX && minY === maxY) {
            // Es un punto: zoom 18
            this.map.flyTo([minY, minX], 18, { duration: 1.2 });
        } else {
            this.map.flyToBounds([[minY, minX], [maxY, maxX]], { duration: 1.2, maxZoom: 19 });
        }
    }
};

