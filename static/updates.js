let ffmpegUpdateTimer=null,ffmpegUpdateNotified=false;
async function refreshFFmpegUpdates(check=false) {
  const data=await api('/api/updates/ffmpeg',check?{method:'POST',body:'{}'}:{}),update=data.update;
  const status=document.querySelector('#ffmpegUpdateStatus'),versions=document.querySelector('#ffmpegUpdateVersions');
  if(!status)return;
  status.textContent=update.status==='checking'?'Buscando actualizaciones de FFmpeg…':update.status==='error'?'No se pudo comprobar. Puedes volver a intentarlo.':update.status==='idle'?'Se comprobará al iniciar la aplicación.':update.available?'Hay una nueva versión de FFmpeg disponible.':'FFmpeg está actualizado.';
  versions.textContent=`Instalada: ${update.current||'no identificada'} · Última versión: ${update.latest||'por comprobar'}${update.checked_at?' · Revisado: '+new Date(update.checked_at).toLocaleTimeString('es-PE',{hour:'2-digit',minute:'2-digit'}):''}`;
  document.querySelector('#ffmpegCheck').disabled=update.status==='checking';
  document.querySelector('#ffmpegDownload').classList.toggle('hidden',!update.available);
  if(update.available&&!ffmpegUpdateNotified){ffmpegUpdateNotified=true;toast('Actualización de FFmpeg',`Versión ${update.latest} disponible. Revisa Configuración.`,'info',7000);}
  clearTimeout(ffmpegUpdateTimer);
  if(update.status==='checking')ffmpegUpdateTimer=setTimeout(()=>refreshFFmpegUpdates().catch(()=>{}),1000);
  return update;
}
function initFFmpegUpdates() {
  document.querySelector('#ffmpegCheck').onclick=()=>refreshFFmpegUpdates(true).catch(error=>toast('No se pudo comprobar',error.message,'error'));
  refreshFFmpegUpdates().then(update=>{if(update.status==='idle')return refreshFFmpegUpdates(true);}).catch(()=>{});
}
