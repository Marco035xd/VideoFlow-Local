let playerToken = null;
let vaultConfigured = true;
let studioBound = false;
let vaultBusy = false;
let vaultRefreshing = false;

function advancedOptions(prefix='download') {
  return {fps:$('#'+prefix+'Fps').value, dynamic_range:$('#'+prefix+'Range').value,
    subtitles:$('#'+prefix+'Subs').value, language:$('#'+prefix+'Language').value,
    start:$('#'+prefix+'Start').value, end:$('#'+prefix+'End').value,
    automatic:$('#'+prefix+'Automatic').checked, incognito:$('#'+prefix+'Incognito').checked};
}

function studioRow(title, subtitle, action, callback) {
  const row = document.createElement('div'); row.className='studio-row';
  const info=document.createElement('div'), heading=document.createElement('strong'), detail=document.createElement('small');
  heading.textContent=title; detail.textContent=subtitle; info.append(heading,detail); row.append(info);
  if(action) {
    const button=document.createElement('button'); button.type='button';button.className='secondary-button';button.textContent=action;
    button.onclick=async()=>{button.disabled=true;try{await callback();}catch(e){toast('No se pudo completar',e.message,'error');}finally{button.disabled=false;}};
    row.append(button);
  }
  return row;
}

function collectionFormats() {
  const mode=$('#collectionMode').value;
  $('#collectionFormat').replaceChildren(...formatChoices[mode].filter(([value])=>value!=='vob').map(([value,label])=>new Option(label,value)));
  collectionQuality();
}
function collectionQuality() {
  const audio=$('#collectionMode').value==='audio', mp3=$('#collectionFormat').value==='mp3';
  const options=audio?(mp3?[[320,'320 kbps'],[192,'192 kbps'],[128,'128 kbps']]:[[0,'Mejor disponible']]):[[0,'Mejor disponible'],[4320,'8K · hasta 4320p'],[2160,'4K · hasta 2160p'],[1440,'2K · hasta 1440p'],[1080,'Hasta 1080p'],[720,'Hasta 720p'],[480,'Hasta 480p']];
  $('#collectionQuality').replaceChildren(...options.map(([v,l])=>new Option(l,v)));
}
async function refreshCollections() {
  const {collections}=await api('/api/collections');
  const list=$('#collectionJobs'); list.replaceChildren();
  for(const job of collections) list.append(studioRow(job.title,`${job.status} · ${job.added} añadidos · ${job.skipped} omitidos${job.error?' · '+job.error:''}`,job.status!=='Cancelado'?'Cancelar colección':null,async()=>{await api(`/api/collections/${job.id}/cancel`,{method:'POST',body:'{}'});await refreshCollections();}));
}
async function refreshBrowser() {
  const data=await api('/api/browser');
  $('#browserStatus').textContent=`${data.blocked} solicitudes bloqueadas · ${data.detected.length} direcciones`;
  const list=$('#browserDetected');list.replaceChildren();
  for(const item of [...data.detected].reverse()) list.append(studioRow(item.kind,item.url,'Descargar',async()=>{
    const format=$('#browserFormat').value;
    await api('/api/browser/download',{method:'POST',body:JSON.stringify({url:item.url,format,mode:format==='mp3'?'audio':'video_audio',folder:$('#browserFolder').value})});
    toast('Descarga añadida','Puedes seguir el progreso en Descargas.');await loadDownloads();
  }));
}
function displayVaultFiles(files) {
  $('#vaultUnlocked').classList.remove('hidden');$('#vaultForm').classList.add('hidden');
  $('#vaultStatus').textContent='Carpeta privada desbloqueada';
  const list=$('#vaultFiles');list.replaceChildren();
  for(const file of files) list.append(studioRow(file.name,`${(file.size/1024/1024).toFixed(1)} MB · cifrado`,'Exportar',async()=>{
    vaultBusy=true;
    try {const result=await api('/api/vault/export',{method:'POST',body:JSON.stringify({id:file.id})});
      if(!result.cancelled) toast('Archivo exportado','La copia exportada se abre sin PIN.');
    } finally {vaultBusy=false;}
  }));
  if(!files.length) list.textContent='Todavía no hay archivos privados.';
}
async function refreshVault() {
  if(vaultBusy || vaultRefreshing)return;
  vaultRefreshing=true;
  try {
  const status=await api('/api/vault');vaultConfigured=status.configured;
  $('#vaultConfirmLabel').classList.toggle('hidden',vaultConfigured);
  if(!status.unlocked) {
    $('#vaultUnlocked').classList.add('hidden');$('#vaultForm').classList.remove('hidden');$('#vaultFiles').replaceChildren();
    $('#vaultStatus').textContent=vaultConfigured?'Carpeta privada bloqueada':'Crea un PIN para comenzar a proteger tus archivos.';
  }
  } finally {vaultRefreshing=false;}
}
function initStudio() {
  $('#settingsBackground').checked=state.settings.background_mode!==false;
  $('#settingsAwake').checked=state.settings.keep_awake!==false;
  $('#collectionFolder').value=folderForSource('youtube');$('#browserFolder').value=state.settings.default_folder;
  if(studioBound)return;studioBound=true;
  collectionFormats();
  $('#collectionMode').onchange=collectionFormats;$('#collectionFormat').onchange=collectionQuality;
  $('#collectionBrowse').onclick=()=>pickFolder('#collectionFolder');$('#browserBrowse').onclick=()=>pickFolder('#browserFolder');
  $('#collectionStart').onclick=async()=>{
    const button=$('#collectionStart');button.disabled=true;
    try {
      await api('/api/collections',{method:'POST',body:JSON.stringify({url:$('#collectionUrl').value,format:$('#collectionFormat').value,mode:$('#collectionMode').value,quality:$('#collectionQuality').value,folder:$('#collectionFolder').value,advanced:advancedOptions('collection')})});
      $('#collectionUrl').value='';await refreshCollections();toast('Colección iniciada','Los videos se añadirán conforme se lea la lista.');
    }catch(e){toast('No se pudo iniciar',e.message,'error');}finally{button.disabled=false;}
  };
  $('#browserOpen').onclick=async()=>{try{await api('/api/browser',{method:'POST',body:JSON.stringify({url:$('#browserUrl').value})});}catch(e){toast('No se pudo abrir el navegador',e.message,'error');}};
  $('#browserRefresh').onclick=()=>refreshBrowser().catch(e=>toast('Error',e.message,'error'));
  $('#browserClear').onclick=async()=>{try{await api('/api/browser',{method:'DELETE'});await refreshBrowser();}catch(e){toast('Error',e.message,'error');}};
  $('#vaultForm').onsubmit=async event=>{
    event.preventDefault();const pin=$('#vaultPin').value;
    if(!vaultConfigured&&pin!==$('#vaultConfirm').value)return toast('Revisa el PIN','Los dos PIN deben coincidir.','error');
    const button=event.currentTarget.querySelector('button');button.disabled=true;
    try{const data=await api('/api/vault/unlock',{method:'POST',body:JSON.stringify({pin})});vaultConfigured=true;displayVaultFiles(data.files);}
    catch(e){toast('No se pudo desbloquear',e.message,'error');}
    finally{$('#vaultPin').value='';$('#vaultConfirm').value='';button.disabled=false;}
  };
  $('#vaultLock').onclick=async()=>{try{await api('/api/vault/lock',{method:'POST',body:'{}'});await refreshVault();}catch(e){toast('Error',e.message,'error');}};
  $('#vaultImport').onclick=async()=>{
    vaultBusy=true;
    $('#vaultImport').disabled=true;
    try{const data=await api('/api/vault/import',{method:'POST',body:'{}'});displayVaultFiles(data.files);toast('Copias cifradas',`${data.added} archivos protegidos.${data.errors.length?' '+data.errors.join(' · '):''}`,data.errors.length?'error':'success');}
    catch(e){toast('No se pudo proteger',e.message,'error');}finally{$('#vaultImport').disabled=false;vaultBusy=false;}
  };
  const video=$('#localPlayer');video.tabIndex=0;
  $('#playerOpen').onclick=async()=>{
    try{const data=await api('/api/player',{method:'POST',body:'{}'});if(data.cancelled)return;
      playerToken=data.token;video.src=data.url;$('#playerName').textContent=data.name;$('#playerMessage').textContent='';
      $('#playerFloating').disabled=false;$('#playerPip').disabled=!document.pictureInPictureEnabled;
      await video.play().catch(()=>{});
    }catch(e){toast('No se pudo abrir',e.message,'error');}
  };
  video.onerror=()=>{$('#playerMessage').textContent='El formato interno no es compatible con este reproductor. Conviértelo a MP4 H.264 desde Convertir video.';};
  $('#playerFloating').onclick=async()=>{try{await api(`/api/player/${playerToken}/floating`,{method:'POST',body:'{}'});video.pause();}catch(e){toast('No se pudo abrir la ventana',e.message,'error');}};
  $('#playerPip').onclick=async()=>{try{if(document.pictureInPictureElement)await document.exitPictureInPicture();else await video.requestPictureInPicture();}catch(e){toast('PiP no disponible','Usa el botón Ventana flotante.','info');}};
  $('#playerSpeed').onchange=()=>{video.playbackRate=Number($('#playerSpeed').value);};
  $('#playerBrightness').oninput=()=>{video.style.filter=`brightness(${$('#playerBrightness').value}%)`;};
  let gesture=null;
  video.addEventListener('pointerdown',event=>{
    const rect=video.getBoundingClientRect();if(event.clientY>rect.bottom-55)return;
    gesture={y:event.clientY,brightness:Number($('#playerBrightness').value),volume:video.volume,left:event.clientX<rect.left+rect.width/2,height:rect.height};video.setPointerCapture(event.pointerId);
  });
  video.addEventListener('pointermove',event=>{if(!gesture)return;const delta=(gesture.y-event.clientY)/gesture.height;
    if(gesture.left){$('#playerBrightness').value=Math.max(50,Math.min(150,gesture.brightness+delta*100));$('#playerBrightness').oninput();}
    else video.volume=Math.max(0,Math.min(1,gesture.volume+delta));
  });
  video.addEventListener('pointerup',()=>gesture=null);video.addEventListener('pointercancel',()=>gesture=null);
  video.addEventListener('keydown',event=>{if(![' ','ArrowRight','ArrowLeft','ArrowUp','ArrowDown'].includes(event.key))return;event.preventDefault();
    if(event.key===' ')video.paused?video.play().catch(()=>{}):video.pause();
    if(event.key==='ArrowRight'&&Number.isFinite(video.duration))video.currentTime=Math.min(video.duration,video.currentTime+10);
    if(event.key==='ArrowLeft')video.currentTime=Math.max(0,video.currentTime-10);
    if(event.key==='ArrowUp')video.volume=Math.min(1,video.volume+.05);
    if(event.key==='ArrowDown')video.volume=Math.max(0,video.volume-.05);
  });
  setInterval(()=>{
    if(state.currentPage==='collections')refreshCollections().catch(()=>{});
    if(state.currentPage==='vault')refreshVault().catch(()=>{});
  },3000);
}
