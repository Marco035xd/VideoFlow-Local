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
  for(const job of collections) {
    const summary=job.status==='Completado'?'Lectura finalizada':job.status;
    const canCancel=job.status!=='Cancelado' && (job.status==='Leyendo' || job.added>0);
    const row=studioRow(job.title,`${summary} · ${job.added} añadidos · ${job.skipped} omitidos`,canCancel?'Cancelar colección':null,async()=>{await api(`/api/collections/${job.id}/cancel`,{method:'POST',body:'{}'});await refreshCollections();});
    if(job.error){
      const error=document.createElement('p');error.className='error-message';error.textContent=job.error;
      row.querySelector('div').append(error);
    }
    if(job.added){
      const view=document.createElement('button');view.type='button';view.className='secondary-button';view.textContent='Ver descargas';
      view.onclick=()=>navigate('downloads');row.append(view);
    }
    list.append(row);
  }
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
  initFFmpegUpdates();
  collectionFormats();
  $('#collectionMode').onchange=collectionFormats;$('#collectionFormat').onchange=collectionQuality;
  $('#collectionBrowse').onclick=()=>pickFolder('#collectionFolder');$('#browserBrowse').onclick=()=>pickFolder('#browserFolder');
  $('#collectionDownload').onclick=async()=>{
    const button=$('#collectionDownload'),feedback=$('#collectionFeedback');
    const url=$('#collectionUrl').value.trim();
    if(!url){feedback.textContent='Pega el enlace de una lista o un canal de YouTube.';$('#collectionUrl').focus();return;}
    button.disabled=true;feedback.classList.remove('error-message');feedback.textContent='Iniciando la lectura de la colección…';
    try {
      await api('/api/collections',{method:'POST',body:JSON.stringify({url,format:$('#collectionFormat').value,mode:$('#collectionMode').value,quality:$('#collectionQuality').value,folder:$('#collectionFolder').value,advanced:advancedOptions('collection')})});
      feedback.textContent='Colección iniciada. El estado de lectura aparece abajo; cada canción o video se descarga en Descargas.';
      toast('Colección iniciada','Los videos se añadirán conforme se lea la lista.');
      refreshCollections().catch(()=>{feedback.textContent='La colección se inició, pero no se pudo actualizar su estado. Vuelve a entrar en Listas y canales.';});
    }catch(e){feedback.classList.add('error-message');feedback.textContent=e.message;toast('No se pudo iniciar',e.message,'error');}finally{button.disabled=false;}
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
  initMainPlayer();
  setInterval(()=>{
    if(state.currentPage==='collections')refreshCollections().catch(()=>{});
    if(state.currentPage==='vault')refreshVault().catch(()=>{});
  },3000);
}
