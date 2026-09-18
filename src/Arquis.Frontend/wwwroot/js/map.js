(() => {
  const app=document.getElementById('app'); const api=app.dataset.api;
  const map=L.map('map',{zoomControl:true}).setView([-16.39,-60.965],14);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:20,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
  L.control.scale({imperial:false}).addTo(map);

  const layerState=new Map(); let selectedLayer=null; let selectedId=null; let selectedFeature=null; let selectedGraphic=null; let refreshTimer=null; let detailVersion=0; let refreshVersion=0;
  const withWater=document.getElementById('showWithWater'), withoutWater=document.getElementById('showWithoutWater');
  withWater.closest('fieldset').insertAdjacentHTML('beforeend','<p class="small text-secondary mb-0 mt-2">Acércate al mapa para distinguir los símbolos de cada lote.</p>');
  function waterVisible(key,feature){
    if(key==='codigosfijos')return withWater.checked;
    if(key==='lotes')return feature.properties.TieneAgua===true?withWater.checked:withoutWater.checked;
    return true;
  }
  function syncSymbols(st){if(st.visible&&map.getZoom()>=17)st.symbols.addTo(map);else map.removeLayer(st.symbols);}
  function renderLayer(st){st.group.clearLayers();st.symbols.clearLayers();if(st.data)st.group.addData(st.data);syncSymbols(st);}
  function applyWaterFilters(){
    for(const [key,st] of layerState)if(key==='lotes'||key==='codigosfijos')renderLayer(st);
    if(selectedFeature&&!waterVisible(selectedLayer,selectedFeature)){
      if(selectedGraphic)map.removeLayer(selectedGraphic);
      selectedGraphic=null;selectedFeature=null;selectedLayer=null;selectedId=null;++detailVersion;
      document.getElementById('detailPanel').classList.add('d-none');
    }
    renderLegend();
  }
  withWater.addEventListener('change',applyWaterFilters);withoutWater.addEventListener('change',applyWaterFilters);
  const loading=document.getElementById('loading'); const results=document.getElementById('results'); const resultStatus=document.getElementById('resultStatus'); const resultCount=document.getElementById('resultCount');

  const styleFor=(key,meta)=> feature => {
    const s=meta.style||{}; if(key==='codigosfijos') return s;
    if(key==='lotes')return {color:s.color||'#38bdf8',weight:1.5,fillOpacity:.12};
    return {color:s.color||'#333',weight:s.weight||2,fillOpacity:s.fillOpacity??0.08};
  };
  function waterSymbol(hasWater){
    return `<svg viewBox="0 0 32 32" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15h6v-4h11v4h5v6h-6v-2H10v2H4zM15 11V6M10 6h10"/><path d="M23 24s-3 3-3 4a3 3 0 0 0 6 0c0-1-3-4-3-4z"/>${hasWater?'':'<path d="M4 4l24 24" stroke-width="3"/>'}</svg>`;
  }
  function waterMarker(latlng,hasWater,label){
    const icon=L.divIcon({className:`water-marker ${hasWater?'water-yes':'water-no'}`,html:`<span role="img" aria-label="${hasWater?'Agua potable':'Sin agua'}">${waterSymbol(hasWater)}</span>`,iconSize:[22,22],iconAnchor:[11,11]});
    return L.marker(latlng,{icon,title:label,alt:label}).bindTooltip(escapeHtml(label));
  }
  const pointFor=(meta,feature,latlng)=> L.circleMarker(latlng,{radius:3,color:meta.style?.color||'#f59e0b',weight:1,fillOpacity:.8}).bindTooltip(escapeHtml(`Código fijo ${feature.properties.CodFijo??feature.id}`));
  const title=(k)=>({manzanas:'Manzanas',lotes:'Lotes',codigosfijos:'Códigos fijos',vias:'Vías'}[k]||k);

  async function ensureSession(){ const r=await fetch(`${api}/api/autenticacion/sesion`,{credentials:'include'}); if(r.status===401){location.href='/';return null;} if(!r.ok) throw new Error('No se pudo verificar la sesión.'); const s=await r.json(); document.getElementById('userName').textContent=s.nombre||s.usuario; return s; }
  async function loadMetadata(){
    const r=await fetch(`${api}/api/capas`,{credentials:'include'}); if(r.status===401){location.href='/';return;} if(!r.ok) throw new Error('No se pudo cargar el catálogo de capas.');
    const metas=await r.json(); const ctl=document.getElementById('layerControl'); const legend=document.getElementById('legend'); ctl.innerHTML=''; legend.innerHTML='';
    metas.forEach(meta=>{
      const key=meta.key, symbols=L.layerGroup();
      const g=L.geoJSON(null,{filter:feature=>waterVisible(key,feature),style:styleFor(key,meta),pointToLayer:(f,ll)=>pointFor(meta,f,ll),onEachFeature:(feature,layer)=>{
        layer.on('click',()=>selectFeature(key,feature,layer));
        if(key==='lotes'){
          const p=feature.properties;
          waterMarker([p.AguaLatitud,p.AguaLongitud],p.TieneAgua,`${p.TieneAgua?'Con agua':'Sin agua'} · Lote ${p.NroLote??feature.id}`).on('click',()=>selectFeature(key,feature,layer)).addTo(symbols);
        }
      }});
      const state={meta,group:g,symbols,visible:true};layerState.set(key,state);g.addTo(map);syncSymbols(state);
      const id=`layer-${key}`; ctl.insertAdjacentHTML('beforeend',`<div class="form-check"><input class="form-check-input" type="checkbox" id="${id}" checked><label class="form-check-label" for="${id}">${meta.title}</label></div>`);
      document.getElementById(id).addEventListener('change',e=>{const st=layerState.get(key);st.visible=e.target.checked;if(st.visible)st.group.addTo(map);else map.removeLayer(st.group);syncSymbols(st);renderLegend();scheduleRefresh();});
    });
    renderLegend();
    const extents=metas.map(x=>x.extent).filter(x=>Array.isArray(x)&&x.length===4); if(extents.length){const minX=Math.min(...extents.map(x=>x[0])),minY=Math.min(...extents.map(x=>x[1])),maxX=Math.max(...extents.map(x=>x[2])),maxY=Math.max(...extents.map(x=>x[3])); map.fitBounds([[minY,minX],[maxY,maxX]],{padding:[20,20]});}
    await refreshVisibleLayers();
  }
  function renderLegend(){
    const legend=document.getElementById('legend'); legend.innerHTML='';
    for(const [key,st] of layerState){
      if(!st.visible)continue;
      if(key==='codigosfijos'){if(withWater.checked)legend.insertAdjacentHTML('beforeend','<div class="small mb-2"><span class="legend-swatch legend-dot" style="background:#f59e0b"></span>Códigos fijos</div>');}
      else if(key==='lotes'){
        if(withWater.checked||withoutWater.checked)legend.insertAdjacentHTML('beforeend',`<div class="small mb-2"><span class="legend-swatch" style="background:${st.meta.style?.color||'#38bdf8'}"></span>Lotes</div>`);
        if(withWater.checked)legend.insertAdjacentHTML('beforeend',`<div class="small mb-2 water-legend"><span class="water-yes">${waterSymbol(true)}</span>Lotes con agua</div>`);
        if(withoutWater.checked)legend.insertAdjacentHTML('beforeend',`<div class="small mb-2 water-legend"><span class="water-no">${waterSymbol(false)}</span>Sin agua · lote sin código fijo</div>`);
      }
      else legend.insertAdjacentHTML('beforeend',`<div class="small mb-2"><span class="legend-swatch" style="background:${st.meta.style?.color||'#333'}"></span>${escapeHtml(st.meta.title)}</div>`);
    }
    if(!legend.children.length)legend.innerHTML='<span class="small text-secondary">Sin capas visibles.</span>';
  }
  function currentBbox(){ const b=map.getBounds(); return [b.getWest(),b.getSouth(),b.getEast(),b.getNorth()].join(','); }
  async function refreshVisibleLayers(){
    const version=++refreshVersion;
    loading.classList.remove('d-none'); try{
      const jobs=[]; for(const [key,st] of layerState){if(!st.visible)continue;jobs.push((async()=>{const r=await fetch(`${api}/api/capas/${key}/geojson?bbox=${encodeURIComponent(currentBbox())}&limit=1800`,{credentials:'include'});if(!r.ok)return;const gj=await r.json();if(version!==refreshVersion)return;st.data=gj;renderLayer(st);})());} await Promise.all(jobs);
    } finally { if(version===refreshVersion)loading.classList.add('d-none'); }
  }
  function scheduleRefresh(){clearTimeout(refreshTimer);refreshTimer=setTimeout(refreshVisibleLayers,250);} map.on('moveend',scheduleRefresh); map.on('mousemove',e=>document.getElementById('coords').textContent=`Lon: ${e.latlng.lng.toFixed(6)} · Lat: ${e.latlng.lat.toFixed(6)}`);
  map.on('zoomend',()=>{for(const st of layerState.values())syncSymbols(st);});

  const serviceStates={1:'Normal',2:'Para corte',3:'Cortado',4:'Baja parcial',5:'Baja total'};
  function showDetail(key,feature){
    const panel=document.getElementById('detailPanel'),content=document.getElementById('detailContent');
    const version=++detailVersion, water=key==='codigosfijos'||key==='lotes';
    let html=`<div class="small text-secondary mb-2">${title(key)} · ID ${escapeHtml(feature.id??'')}</div>`;
    if(water) html+='<section id="waterDetail" aria-live="polite"><h3 class="h6">Agua potable</h3><p class="small">Consultando datos…</p></section>';
    // La ficha usa las coordenadas de la geometria y explica el estado sin confirmar.
    if(key!=='codigosfijos'){
      html+='<table class="table table-sm prop-table"><tbody>';
      for(const [k,v] of Object.entries(feature.properties||{}))html+=`<tr><th>${escapeHtml(k)}</th><td>${escapeHtml(v??'')}</td></tr>`;
      html+='</tbody></table>';
    }
    content.innerHTML=html; panel.classList.remove('d-none');
    if(water) loadWaterDetail(key,feature.id,version);
  }
  async function loadWaterDetail(key,id,version){
    const current=()=>version===detailVersion&&!document.getElementById('detailPanel').classList.contains('d-none');
    try{
      const resource=key==='lotes'?'lotes':'codigos';
      const r=await fetch(`${api}/api/agua-potable/${resource}/${id}`,{credentials:'include'});
      if(r.status===401){location.href='/';return;}
      if(!r.ok)throw new Error('No se pudo consultar la ficha de agua potable. Seleccione nuevamente la entidad para reintentar.');
      const ficha=await r.json(); if(!current())return;
      const section=document.getElementById('waterDetail');
      let html=`<h3 class="h6">Agua potable</h3><p class="fw-semibold ${ficha.tieneAgua?'text-primary':'text-danger'}">${ficha.tieneAgua?'Agua potable · con código fijo':'Sin agua · lote sin código fijo'}</p>`;
      if(!ficha.registros.length)html+='<p class="small">Este lote no tiene códigos fijos asociados.</p>';
      for(const item of ficha.registros){
        const rows=[['Código fijo',item.codigoFijo],['Código SIG',item.codigoSig],['Nombre registrado',item.nombreRegistrado],['Lote',item.numeroLote],['UV',item.uv],['Manzana',item.manzana],['Longitud',item.longitud],['Latitud',item.latitud],['Estado del servicio',item.estadoVerificado?(serviceStates[item.estadoServicio]||'Sin verificar'):'Sin verificar']];
        html+='<div class="border rounded p-2 mb-2"><table class="table table-sm prop-table mb-0"><tbody>';
        for(const [label,value] of rows)html+=`<tr><th>${escapeHtml(label)}</th><td>${escapeHtml(value??'No disponible')}</td></tr>`;
        html+='</tbody></table>';
        if(!item.estadoVerificado)html+='<p class="small text-secondary mt-2 mb-0">Los archivos originales no indican el estado del servicio.</p>';
        if(key==='lotes')html+=`<button type="button" class="btn btn-sm btn-outline-primary mt-2" data-water-code="${item.idCodigo}">Ubicar código ${escapeHtml(item.codigoFijo??item.idCodigo)}</button>`;
        html+='</div>';
      }
      html+=`<p class="small mb-1"><strong>Datos pendientes:</strong> ${ficha.datosNoDisponibles.map(escapeHtml).join(', ')}.</p><p class="small text-secondary">Fuente: ${escapeHtml(ficha.fuente)}. Disponibilidad de agua según la presencia de código fijo.</p>`;
      section.innerHTML=html;
      section.querySelectorAll('[data-water-code]').forEach(button=>button.addEventListener('click',()=>openSearchResult({layer:'codigosfijos',id:Number(button.dataset.waterCode)})));
    }catch(error){if(current())document.getElementById('waterDetail').innerHTML=`<h3 class="h6">Agua potable</h3><p class="small text-danger">${escapeHtml(error.message)}</p>`;}
  }
  function selectFeature(key,feature,layer){ if(!waterVisible(key,feature)){resultStatus.textContent='La entidad está oculta por el filtro de agua. Active su casilla para mostrarla.';return;} selectedFeature=feature;selectedLayer=key;selectedId=feature.id; if(selectedGraphic)map.removeLayer(selectedGraphic); try{selectedGraphic=L.geoJSON(feature,{style:{color:'#f59e0b',weight:5,fillOpacity:.18},pointToLayer:(f,ll)=>L.circleMarker(ll,{radius:10,color:'#f59e0b',weight:4,fillOpacity:.25})}).addTo(map);}catch{} showDetail(key,feature); highlightResult(key,feature.id); }
  function highlightResult(key,id){document.querySelectorAll('.result-item').forEach(x=>x.classList.toggle('active',x.dataset.layer===key&&String(x.dataset.id)===String(id)));}

  async function doSearch(){
    const text=document.getElementById('searchText').value.trim(); if(!text){resultStatus.textContent='Escriba un criterio de búsqueda.';return;} resultStatus.textContent='Buscando…';results.innerHTML='';
    const r=await fetch(`${api}/api/busqueda?texto=${encodeURIComponent(text)}&tamano=100`,{credentials:'include'}); if(!r.ok){resultStatus.textContent='No se pudo ejecutar la búsqueda.';return;} const rows=await r.json();resultCount.textContent=rows.length;
    if(!rows.length){resultStatus.textContent='Sin resultados.';return;} resultStatus.textContent=`${rows.length} resultado(s). Seleccione uno para acercar.`;
    rows.forEach(row=>{const a=document.createElement('button');a.type='button';a.className='list-group-item list-group-item-action result-item';a.dataset.layer=row.layer;a.dataset.id=row.id;a.innerHTML=`<div class="fw-semibold">${escapeHtml(row.label)}</div><small class="text-secondary">${title(row.layer)} · ID ${row.id}</small>`;a.addEventListener('click',()=>openSearchResult(row));results.appendChild(a);});
  }
  async function openSearchResult(row){
    const r=await fetch(`${api}/api/capas/${row.layer}/${row.id}`,{credentials:'include'});if(!r.ok)return;const feature=await r.json();if(Array.isArray(feature.bbox)){const b=feature.bbox;if(b[0]===b[2]&&b[1]===b[3])map.setView([b[1],b[0]],18);else map.fitBounds([[b[1],b[0]],[b[3],b[2]]],{padding:[40,40],maxZoom:19});}selectFeature(row.layer,feature,null);
  }
  function clearResults(){results.innerHTML='';resultCount.textContent='0';resultStatus.textContent='Sin consulta activa.';document.getElementById('searchText').value='';if(selectedGraphic){map.removeLayer(selectedGraphic);selectedGraphic=null;}document.getElementById('detailPanel').classList.add('d-none');}
  function escapeHtml(v){return String(v).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}

  document.getElementById('searchBtn').addEventListener('click',doSearch);document.getElementById('searchText').addEventListener('keydown',e=>{if(e.key==='Enter')doSearch();});document.getElementById('clearBtn').addEventListener('click',clearResults);document.getElementById('detailClose').addEventListener('click',()=>document.getElementById('detailPanel').classList.add('d-none'));
  document.getElementById('logoutBtn').addEventListener('click',async()=>{await fetch(`${api}/api/autenticacion/cerrar`,{method:'POST',credentials:'include'});location.href='/';});document.getElementById('toggleSidebar').addEventListener('click',()=>document.getElementById('sidebar').classList.toggle('open'));
  (async()=>{try{await ensureSession();await loadMetadata();}catch(e){resultStatus.textContent=e.message;}})();
})();
