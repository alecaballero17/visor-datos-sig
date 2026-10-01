// ── Motor de mapa Arquis ─────────────────────────────────────────────────────
// Inicializado desde Blazor: JS.InvokeVoidAsync("arquis.init")
// ────────────────────────────────────────────────────────────────────────────
window.arquis = (() => {
  let map, api;
  const layerState = new Map();
  let selectedLayer=null,selectedId=null,selectedFeature=null;
  let selectedGraphic=null,selectionLabel=null;
  let refreshTimer=null,detailVersion=0,refreshVersion=0;

  /* helpers */
  const esc = v => String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const titleOf = k => ({manzanas:'Manzanas',lotes:'Lotes',codigosfijos:'Códigos fijos',vias:'Vías'}[k]||k);
  const waterSymbol = has => `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15h6v-4h11v4h5v6h-6v-2H10v2H4zM15 11V6M10 6h10"/><path d="M23 24s-3 3-3 4a3 3 0 0 0 6 0c0-1-3-4-3-4z"/>${has?'':'<path d="M4 4l24 24" stroke-width="3"/>'}</svg>`;
  const $  = id => document.getElementById(id);
  const ww = () => $('showWithWater');
  const wo = () => $('showWithoutWater');

  /* filtros agua */
  function waterVisible(key,feature){
    if(key==='codigosfijos') return ww()?.checked??true;
    if(key==='lotes') return (feature.properties?.TieneAgua ? ww() : wo())?.checked??true;
    return true;
  }

  /* capas */
  function syncSymbols(st){
    if(st.visible && map.getZoom()>=17) st.symbols.addTo(map);
    else map.removeLayer(st.symbols);
  }
  function renderLayer(st){
    st.group.clearLayers(); st.symbols.clearLayers();
    if(st.data) st.group.addData(st.data);
    syncSymbols(st);
  }
  function applyWaterFilters(){
    for(const [key,st] of layerState)
      if(key==='lotes'||key==='codigosfijos') renderLayer(st);
    if(selectedFeature && !waterVisible(selectedLayer,selectedFeature)){
      if(selectedGraphic) map.removeLayer(selectedGraphic);
      if(selectionLabel)  map.removeLayer(selectionLabel);
      selectedGraphic=selectionLabel=selectedFeature=selectedLayer=selectedId=null;
      ++detailVersion;
      $('detailPanel')?.classList.add('d-none');
    }
    renderLegend();
  }

  /* estilos */
  function styleFor(key,meta){ return _f=>{
    if(key==='codigosfijos') return meta.style||{};
    if(key==='lotes') return {color:meta.style?.color||'#38bdf8',weight:1.5,fillOpacity:.12};
    return {color:meta.style?.color||'#333',weight:meta.style?.weight||2,fillOpacity:meta.style?.fillOpacity??0.08};
  };}
  function waterMarker(latlng,has,label){
    const icon=L.divIcon({className:`water-marker ${has?'water-yes':'water-no'}`,html:`<span>${waterSymbol(has)}</span>`,iconSize:[22,22],iconAnchor:[11,11]});
    return L.marker(latlng,{icon,title:label}).bindTooltip(esc(label));
  }
  function pointFor(meta,feature,latlng){
    return L.circleMarker(latlng,{radius:3,color:meta.style?.color||'#f59e0b',weight:1,fillOpacity:.8})
      .bindTooltip(esc(`Código fijo ${feature.properties?.CodFijo??feature.id}`));
  }

  /* leyenda */
  function renderLegend(){
    const legend=$('legend'); if(!legend) return;
    const has=ww()?.checked, sin=wo()?.checked;
    legend.innerHTML='';
    for(const [key,st] of layerState){
      if(!st.visible) continue;
      if(key==='codigosfijos'){
        if(has) legend.insertAdjacentHTML('beforeend',`<div class="small mb-2"><span class="legend-dot" style="background:#f59e0b"></span>Códigos fijos</div>`);
      } else if(key==='lotes'){
        if(has||sin) legend.insertAdjacentHTML('beforeend',`<div class="small mb-2"><span class="legend-swatch" style="background:${st.meta.style?.color||'#38bdf8'}"></span>Lotes</div>`);
        if(has) legend.insertAdjacentHTML('beforeend',`<div class="small mb-2 water-legend"><span class="water-yes">${waterSymbol(true)}</span>Con agua</div>`);
        if(sin) legend.insertAdjacentHTML('beforeend',`<div class="small mb-2 water-legend"><span class="water-no">${waterSymbol(false)}</span>Sin agua</div>`);
      } else {
        legend.insertAdjacentHTML('beforeend',`<div class="small mb-2"><span class="legend-swatch" style="background:${st.meta.style?.color||'#333'}"></span>${esc(st.meta.title)}</div>`);
      }
    }
    if(!legend.children.length) legend.innerHTML='<span class="small text-secondary">Sin capas visibles.</span>';
  }

  /* refresh */
  function currentBbox(){const b=map.getBounds();return[b.getWest(),b.getSouth(),b.getEast(),b.getNorth()].join(',');}
  async function refreshVisibleLayers(){
    const version=++refreshVersion;
    $('loading')?.classList.remove('d-none');
    try{
      const jobs=[];
      for(const [key,st] of layerState){
        if(!st.visible) continue;
        if((key==='lotes'||key==='codigosfijos')&&map.getZoom()<16){
          st.data={type:'FeatureCollection',features:[]}; renderLayer(st); continue;
        }
        const limit=key==='lotes'?350:key==='codigosfijos'?600:900;
        jobs.push((async()=>{
          const r=await fetch(`${api}/api/capas/${key}/geojson?bbox=${encodeURIComponent(currentBbox())}&limit=${limit}`,{credentials:'include'});
          if(!r.ok) return;
          const gj=await r.json();
          if(version!==refreshVersion) return;
          st.data=gj; renderLayer(st);
        })());
      }
      await Promise.all(jobs);
    } finally { if(version===refreshVersion) $('loading')?.classList.add('d-none'); }
  }
  function scheduleRefresh(){clearTimeout(refreshTimer);refreshTimer=setTimeout(refreshVisibleLayers,250);}

  /* metadatos */
  async function loadMetadata(){
    const r=await fetch(`${api}/api/capas`,{credentials:'include'});
    if(r.status===401){location.href='/';return;}
    if(!r.ok) throw new Error('No se pudo cargar el catálogo de capas.');
    const metas=await r.json();
    const ctl=$('layerControl'); if(ctl) ctl.innerHTML='';

    metas.forEach(meta=>{
      const key=meta.key, symbols=L.layerGroup();
      const g=L.geoJSON(null,{
        filter:f=>waterVisible(key,f),
        style:styleFor(key,meta),
        pointToLayer:(f,ll)=>pointFor(meta,f,ll),
        onEachFeature:(feature,layer)=>{
          layer.on('click',()=>selectFeature(key,feature,layer));
          if(key==='lotes'){
            const p=feature.properties;
            if(p.AguaLatitud&&p.AguaLongitud)
              waterMarker([p.AguaLatitud,p.AguaLongitud],p.TieneAgua,`${p.TieneAgua?'Con agua':'Sin agua'} · Lote ${p.NroLote??feature.id}`)
                .on('click',()=>selectFeature(key,feature,layer)).addTo(symbols);
          }
        }
      });
      const state={meta,group:g,symbols,visible:true};
      layerState.set(key,state); g.addTo(map); syncSymbols(state);

      if(ctl){
        const id=`layer-${key}`;
        ctl.insertAdjacentHTML('beforeend',`<div class="form-check"><input class="form-check-input" type="checkbox" id="${id}" checked><label class="form-check-label" for="${id}">${esc(meta.title)}</label></div>`);
        $(id).addEventListener('change',e=>{
          const st=layerState.get(key); st.visible=e.target.checked;
          if(st.visible) st.group.addTo(map); else map.removeLayer(st.group);
          syncSymbols(st); renderLegend(); scheduleRefresh();
        });
      }
    });

    renderLegend();
    const extents=metas.map(x=>x.extent).filter(x=>Array.isArray(x)&&x.length===4);
    if(extents.length){
      const minX=Math.min(...extents.map(x=>x[0])),minY=Math.min(...extents.map(x=>x[1]));
      const maxX=Math.max(...extents.map(x=>x[2])),maxY=Math.max(...extents.map(x=>x[3]));
      map.fitBounds([[minY,minX],[maxY,maxX]],{padding:[20,20]});
    }
    await refreshVisibleLayers();
  }

  /* selección */
  const svcStates={1:'Normal',2:'Para corte',3:'Cortado',4:'Baja parcial',5:'Baja total'};
  function selectionName(key,feature){
    const p=feature.properties||{};
    if(key==='vias')    return p.Nombre||'Vía seleccionada';
    if(key==='lotes')   return `Lote ${p.NroLote??feature.id}`;
    if(key==='manzanas') return `UV ${p.UV??'-'} · MZA ${p.MZA??feature.id}`;
    return `Código ${p.CodFijo??feature.id}`;
  }
  function selectFeature(key,feature,layer){
    if(!waterVisible(key,feature)){
      const rs=$('resultStatus'); if(rs) rs.textContent='La entidad está oculta por el filtro de agua.'; return;
    }
    selectedFeature=feature; selectedLayer=key; selectedId=feature.id;
    if(selectedGraphic) map.removeLayer(selectedGraphic);
    if(selectionLabel)  map.removeLayer(selectionLabel);
    try{
      selectedGraphic=L.geoJSON(feature,{
        pane:'selectionPane',interactive:false,
        style:{color:'#facc15',weight:10,opacity:1,fillColor:'#facc15',fillOpacity:.28,dashArray:'12 6'},
        pointToLayer:(_,ll)=>L.circleMarker(ll,{pane:'selectionPane',radius:14,color:'#facc15',weight:5,fillColor:'#ef4444',fillOpacity:1})
      }).addTo(map);
      selectedGraphic.eachLayer(i=>i.bringToFront?.());
      const center=selectedGraphic.getBounds().getCenter();
      selectionLabel=L.marker(center,{interactive:false,icon:L.divIcon({className:'selection-label',html:`<span>✓ ${esc(selectionName(key,feature))}</span>`,iconAnchor:[0,34]})}).addTo(map);
    } catch(_){}
    showDetail(key,feature);
    document.querySelectorAll('.result-item').forEach(x=>x.classList.toggle('active',x.dataset.layer===key&&String(x.dataset.id)===String(feature.id)));
  }

  /* detalle */
  function showDetail(key,feature){
    const panel=$('detailPanel'),content=$('detailContent');
    if(!panel||!content) return;
    const version=++detailVersion, water=key==='codigosfijos'||key==='lotes';
    let html=`<div class="small text-secondary mb-2">${titleOf(key)} · ID ${esc(feature.id??'')}</div>`;
    if(water) html+='<section id="waterDetail"><h3 class="h6">Agua potable</h3><p class="small anim-pulse">Consultando datos…</p></section>';
    if(key!=='codigosfijos'){
      html+='<table class="table table-sm prop-table"><tbody>';
      for(const [k,v] of Object.entries(feature.properties||{}))
        html+=`<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`;
      html+='</tbody></table>';
    }
    content.innerHTML=html; panel.classList.remove('d-none');
    if(water) loadWaterDetail(key,feature.id,version);
  }
  async function loadWaterDetail(key,id,version){
    const alive=()=>version===detailVersion&&!$('detailPanel')?.classList.contains('d-none');
    try{
      const r=await fetch(`${api}/api/agua-potable/${key==='lotes'?'lotes':'codigos'}/${id}`,{credentials:'include'});
      if(r.status===401){location.href='/';return;}
      if(!r.ok) throw new Error('No se pudo consultar la ficha.');
      const ficha=await r.json(); if(!alive()) return;
      const section=$('waterDetail'); if(!section) return;
      let html=`<h3 class="h6">Agua potable</h3><p class="fw-semibold ${ficha.tieneAgua?'text-primary':'text-danger'}">${ficha.tieneAgua?'Con código fijo':'Sin código fijo'}</p>`;
      for(const item of (ficha.registros||[])){
        const rows=[['Código fijo',item.codigoFijo],['Código SIG',item.codigoSig],['Nombre',item.nombreRegistrado],['Lote',item.numeroLote],['UV',item.uv],['Manzana',item.manzana],['Lon',item.longitud],['Lat',item.latitud],['Estado',item.estadoVerificado?(svcStates[item.estadoServicio]||'Sin verificar'):'Sin verificar']];
        html+=`<div class="border rounded p-2 mb-2 anim-fade-in-up"><table class="table table-sm prop-table mb-0"><tbody>`;
        for(const [l,v] of rows) html+=`<tr><th>${esc(l)}</th><td>${esc(v??'—')}</td></tr>`;
        html+=`</tbody></table>`;
        if(key==='lotes') html+=`<button type="button" class="btn btn-sm btn-outline-primary mt-2" data-water-code="${item.idCodigo}">Ubicar código ${esc(item.codigoFijo??item.idCodigo)}</button>`;
        html+=`</div>`;
      }
      section.innerHTML=html;
      section.querySelectorAll('[data-water-code]').forEach(btn=>btn.addEventListener('click',()=>openSearchResult({layer:'codigosfijos',id:Number(btn.dataset.waterCode)})));
    } catch(e){
      if(alive()){const s=$('waterDetail');if(s)s.innerHTML=`<h3 class="h6">Agua potable</h3><p class="small text-danger">${esc(e.message)}</p>`;}
    }
  }

  /* búsqueda */
  async function doSearch(){
    const text=$('searchText')?.value.trim();
    const rs=$('resultStatus'),res=$('results'),rc=$('resultCount');
    if(!text){if(rs)rs.textContent='Escriba un criterio de búsqueda.';return;}
    if(rs)rs.textContent='Buscando…'; if(res)res.innerHTML='';
    const r=await fetch(`${api}/api/busqueda?texto=${encodeURIComponent(text)}&tamano=100`,{credentials:'include'});
    if(!r.ok){if(rs)rs.textContent='No se pudo ejecutar la búsqueda.';return;}
    const rows=await r.json();
    if(rc)rc.textContent=rows.length;
    if(!rows.length){if(rs)rs.textContent='Sin resultados.';return;}
    if(rs)rs.textContent=`${rows.length} resultado(s). Seleccione uno para acercar.`;
    rows.forEach((row,i)=>{
      const btn=document.createElement('button');
      btn.type='button';
      btn.className='list-group-item list-group-item-action result-item';
      btn.dataset.layer=row.layer; btn.dataset.id=row.id;
      btn.innerHTML=`<div class="fw-semibold">${esc(row.label)}</div><small class="text-secondary">${titleOf(row.layer)} · ID ${row.id}</small>`;
      btn.addEventListener('click',()=>openSearchResult(row));
      res?.appendChild(btn);
    });
  }
  async function openSearchResult(row){
    const r=await fetch(`${api}/api/capas/${row.layer}/${row.id}`,{credentials:'include'});
    if(!r.ok) return;
    const feature=await r.json();
    if(Array.isArray(feature.bbox)){
      const b=feature.bbox;
      if(b[0]===b[2]&&b[1]===b[3]) map.setView([b[1],b[0]],18);
      else map.fitBounds([[b[1],b[0]],[b[3],b[2]]],{padding:[40,40],maxZoom:19});
    }
    selectFeature(row.layer,feature,null);
  }
  function clearResults(){
    if($('results'))$('results').innerHTML='';
    if($('resultCount'))$('resultCount').textContent='0';
    if($('resultStatus'))$('resultStatus').textContent='Sin consulta activa.';
    if($('searchText'))$('searchText').value='';
    if(selectedGraphic){map.removeLayer(selectedGraphic);selectedGraphic=null;}
    if(selectionLabel) {map.removeLayer(selectionLabel); selectionLabel=null;}
    $('detailPanel')?.classList.add('d-none');
  }

  /* init */
  async function init(){
    const appEl=$('app');
    api=(appEl?.dataset?.api||'').replace(/\/$/,'');

    map=L.map('map',{zoomControl:true}).setView([-16.39,-60.965],14);
    map.createPane('selectionPane').style.zIndex=650;
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:22,maxNativeZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
    L.control.scale({imperial:false}).addTo(map);

    map.on('mousemove',e=>{const el=$('coords');if(el)el.textContent=`Lon: ${e.latlng.lng.toFixed(6)} · Lat: ${e.latlng.lat.toFixed(6)}`;});
    map.on('moveend',scheduleRefresh);
    map.on('zoomend',()=>{for(const st of layerState.values())syncSymbols(st);});

    $('showWithWater')?.addEventListener('change',applyWaterFilters);
    $('showWithoutWater')?.addEventListener('change',applyWaterFilters);
    $('searchBtn')?.addEventListener('click',doSearch);
    $('searchText')?.addEventListener('keydown',e=>{if(e.key==='Enter')doSearch();});
    $('clearBtn')?.addEventListener('click',clearResults);
    $('detailClose')?.addEventListener('click',()=>$('detailPanel')?.classList.add('d-none'));
    $('toggleSidebar')?.addEventListener('click',()=>$('sidebar')?.classList.toggle('open'));

    try { await loadMetadata(); }
    catch(e){ const rs=$('resultStatus'); if(rs)rs.textContent=e.message; }
  }

  return { init };
})();

// Compatibilidad con el alias anterior
window.mapInterop = { flyToBbox: () => {}, initializeMap: () => {}, updateLayer: () => {}, removeLayer: () => {} };
