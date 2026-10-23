const platformDrafts = {};
let localFiles = [];
function syncBatchDestination() {
  $('#batchDestination').value = folderForSource();
  $('#batchConcurrency').textContent = `Hasta ${state.settings?.max_concurrent || 3} trabajos simultáneos. Puedes cambiar este límite en Configuración.`;
}
function resultLine(container, label, message) {
  const line = document.createElement('p');
  line.textContent = `${label}: ${message}`;
  $(container).append(line);
}
async function batchDownload() {
  const urls = [...new Set($('#videoUrl').value.trim().split(/\s+/).filter(Boolean))];
  if (!urls.length || urls.length > 10) return toast('Revisa los enlaces', 'Pega entre 1 y 10 enlaces, uno por línea.', 'error');
  const source = state.source;
  const folder = $('#batchDestination').value;
  const mode = $('#batchMode').value;
  const videoQuality = Number($('#batchVideoQuality').value);
  const audioQuality = $('#batchAudioQuality').value;
  const browser = $('#facebookBrowser').value;
  $('#batchStart').disabled = true;
  $('#videoUrl').readOnly = true;
  $$('.source-tab').forEach(b=>b.disabled=true);
  $('#pasteButton').disabled = true;
  $('#batchResults').replaceChildren();
  const failed = [];
  try {
    for (const url of urls) {
      try {
        const host = new URL(url).hostname.toLowerCase();
        const domains = {youtube: ['youtube.com','youtu.be'], facebook: ['facebook.com','fb.watch','fb.com'], tiktok: ['tiktok.com']};
        if (!domains[source].some(d => host === d || host.endsWith('.'+d))) throw new Error('El enlace no corresponde a la plataforma seleccionada.');
        resultLine('#batchResults', url, 'Analizando…');
        const {video} = await api('/api/analyze', {method:'POST',body:JSON.stringify({url,browser})});
        const heights = video.video_options.map(o=>Number(o.value)).filter(v=>v>0 && v<=videoQuality);
        if (mode !== 'audio' && !heights.length) throw new Error('No hay calidad disponible dentro del máximo elegido.');
        await api('/api/downloads',{method:'POST',body:JSON.stringify({url:video.url, original_url:url, title:video.title, video_id:video.id, thumbnail:video.thumbnail, duration:video.duration, folder, mode, format:mode==='audio'?'mp3':'mp4', quality:mode==='audio'?audioQuality:String(Math.max(...heights)),browser})});
        resultLine('#batchResults', video.title, 'Añadido a la cola');
      } catch(error) { failed.push(url); resultLine('#batchResults', url, error.message); }
    }
    platformDrafts[source] = failed.join('\n');
    if (state.source === source) $('#videoUrl').value = platformDrafts[source];
    await loadDownloads();
    toast('Lote procesado', `${urls.length-failed.length} añadidos; ${failed.length} pendientes de revisar.`, failed.length?'info':'success');
  } finally { $('#batchStart').disabled = false; $('#videoUrl').readOnly=false; $$('.source-tab').forEach(b=>b.disabled=false); $('#pasteButton').disabled=false; }
}
function initExtensions() {
  syncBatchDestination();
  $('#settingsRate').value = state.settings.rate_limit_kbps || 0;
  $('#settingsRetries').value = state.settings.retry_count ?? 5;
  $('#conversionFolder').value = state.settings.conversion_folder || state.settings.default_folder;
  $('#batchStart').onclick = batchDownload;
  $('#batchFolder').onclick = async () => {
    const source = state.source;
    await pickFolder('#batchDestination');
    if (state.source !== source) return syncBatchDestination();
    try {
      const folder = $('#batchDestination').value;
      await api('/api/settings',{method:'PUT',body:JSON.stringify({platform_folders:{[source]:folder}})});
      rememberFolder(source, folder);
    } catch(error) { toast('No se pudo guardar', error.message,'error'); }
  };
  $('#conversionBrowse').onclick = () => pickFolder('#conversionFolder');
  $('#conversionFormat').onchange = () => { $('#conversionQuality').disabled = ['wav','flac'].includes($('#conversionFormat').value); };
  $('#chooseVideos').onclick = async () => {
    try {
      const data = await api('/api/local-files',{method:'POST',body:'{}'});
      if (!data.paths.length) return;
      localFiles = [...new Set(data.paths)];
      $('#conversionFiles').replaceChildren();
      localFiles.forEach(p=>resultLine('#conversionFiles', p, 'Seleccionado'));
    } catch(error) { toast('No se pudo seleccionar',error.message,'error'); }
  };
  $('#convertStart').onclick = async () => {
    if (!localFiles.length || localFiles.length>10) return toast('Selecciona videos','Puedes convertir entre 1 y 10 archivos por lote.','error');
    const paths = [...localFiles];
    const format = $('#conversionFormat').value, quality = $('#conversionQuality').value, folder = $('#conversionFolder').value;
    $('#convertStart').disabled = true;
    $('#chooseVideos').disabled = true;
    $('#conversionResults').replaceChildren();
    const failed = [];
    try {
      for (const path of paths) {
        try {
          await api('/api/convert',{method:'POST',body:JSON.stringify({path,format,quality,folder})});
          resultLine('#conversionResults',path,'Añadido a la cola');
        } catch(error) { failed.push(path); resultLine('#conversionResults',path,error.message); }
      }
      localFiles=failed;
      $('#conversionFiles').replaceChildren();
      failed.forEach(p=>resultLine('#conversionFiles',p,'Pendiente'));
      await loadDownloads();
    } finally { $('#convertStart').disabled=false; $('#chooseVideos').disabled=false; }
  };
  $('#historySearch').oninput = filterHistory;
  $('#exportHistory').onclick = () => {
    const quote = value => '"'+String(value ?? '').replace(/^[=+@\-]/,"'$&").replaceAll('"','""')+'"';
    const rows = [['Título','Plataforma','Fecha','Enlace','Archivo'], ...state.history.map(h=>[h.title,h.source,h.downloaded_at,h.url,h.filepath])];
    const blob = new Blob(['\ufeff'+rows.map(r=>r.map(quote).join(';')).join('\r\n')],{type:'text/csv;charset=utf-8'});
    const url = URL.createObjectURL(blob), a=document.createElement('a'); a.href=url; a.download='VideoFlow-historial.csv'; a.click(); setTimeout(()=>URL.revokeObjectURL(url),5000);
  };
  $('#cancelAll').onclick = async () => {
    if (!await confirmAction('Cancelar pendientes','¿Quieres detener todos los trabajos pendientes y activos?')) return;
    try { for(const task of state.downloads.filter(t=>!['Completado','Cancelado','Error'].includes(t.status))) await api(`/api/downloads/${task.id}/cancel`,{method:'POST',body:'{}'}); await loadDownloads(); }
    catch(error) { toast('No se pudo cancelar',error.message,'error'); }
  };
  $('#cleanCompleted').onclick = async () => {
    try { for(const task of state.downloads.filter(t=>t.status==='Completado')) await api(`/api/downloads/${task.id}`,{method:'DELETE'}); await loadDownloads(); }
    catch(error) { toast('No se pudo limpiar',error.message,'error'); }
  };
}
function filterHistory() {
  const query = $('#historySearch').value.toLocaleLowerCase();
  $$('#historyBody tr').forEach(row=>{row.hidden=!row.textContent.toLocaleLowerCase().includes(query);});
}
