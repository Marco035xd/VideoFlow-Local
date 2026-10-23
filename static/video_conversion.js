const videoConvertUI = {busy: false, target: null};

function setVideoConvertBusy(busy) {
  videoConvertUI.busy = busy;
  for (const id of ['videoConvertChoose', 'videoConvertFormat', 'videoConvertQuality', 'videoConvertBrowse', 'videoConvertSaveAs', 'videoConvertStart']) {
    $('#' + id).disabled = busy;
  }
}

function videoConvertResetTarget() {
  videoConvertUI.target = null;
  $('#videoConvertSavedPath').textContent = '';
  $('#videoConvertSavedPath').classList.add('hidden');
}

function updateVideoConvertFormat() {
  videoConvertResetTarget();
  const fmt = $('#videoConvertFormat').value;
  const notice = $('#videoConvertNotice');
  const title = notice.querySelector('strong');
  const detail = notice.querySelector('p');
  if (fmt === 'mp4' || fmt === 'mov') {
    title.textContent = fmt === 'mp4' ? 'MP4 compatible para edición' : 'MOV con H.264 y AAC';
    detail.textContent = 'Se genera un archivo nuevo con H.264, color YUV 4:2:0, audio AAC y fotogramas constantes. MP4 a MP4 cambia el contenido interno, no solo el nombre.';
  } else {
    title.textContent = fmt === 'webm' ? 'WEBM para reproducción web' : 'MKV con H.264 y AAC';
    detail.textContent = fmt === 'webm' ? 'Usa VP9 y Opus. Para intentar resolver la importación en VEGAS Pro, selecciona MP4.' : 'El contenedor MKV puede no ser aceptado por algunas versiones de VEGAS Pro. Para edición, selecciona MP4.';
  }
}

function initVideoConversion() {
  $('#videoConvertFolder').value = state.settings.video_conversion_folder || state.settings.default_folder;
  $('#videoConvertFolder').title = $('#videoConvertFolder').value;
  $('#videoConvertFormat').onchange = updateVideoConvertFormat;
  $('#videoConvertChoose').onclick = async () => {
    setVideoConvertBusy(true);
    try {
      const result = await api('/api/video-file', {method:'POST', body:'{}'});
      if (!result.cancelled) {
        $('#videoConvertInput').value = result.path;
        $('#videoConvertInput').title = result.path;
        videoConvertResetTarget();
      }
    } catch (error) { toast('No se pudo seleccionar el video', error.message, 'error'); }
    finally { setVideoConvertBusy(false); }
  };
  $('#videoConvertBrowse').onclick = async () => {
    setVideoConvertBusy(true);
    try {
      const folder = await pickFolder('#videoConvertFolder');
      if (folder) {
        videoConvertResetTarget();
        await api('/api/settings', {method:'PUT', body:JSON.stringify({video_conversion_folder:folder})});
      }
    } catch (error) { toast('No se pudo elegir la carpeta', error.message, 'error'); }
    finally { setVideoConvertBusy(false); }
  };
  $('#videoConvertSaveAs').onclick = async () => {
    if (!$('#videoConvertInput').value) return toast('Selecciona un video', 'Primero elige el video de origen.', 'error');
    setVideoConvertBusy(true);
    try {
      const result = await api('/api/video-save-path', {method:'POST', body:JSON.stringify({path:$('#videoConvertInput').value, format:$('#videoConvertFormat').value, initial:$('#videoConvertFolder').value})});
      if (!result.cancelled) {
        videoConvertUI.target = result;
        $('#videoConvertFolder').value = result.folder;
        $('#videoConvertFolder').title = result.folder;
        $('#videoConvertSavedPath').textContent = `Archivo final: ${result.path}`;
        $('#videoConvertSavedPath').classList.remove('hidden');
      }
    } catch (error) { toast('No se pudo elegir el archivo de salida', error.message, 'error'); }
    finally { setVideoConvertBusy(false); }
  };
  $('#videoConvertStart').onclick = async () => {
    const path = $('#videoConvertInput').value;
    if (!path) return toast('Selecciona un video', 'Elige el archivo que quieres convertir.', 'error');
    setVideoConvertBusy(true);
    try {
      await api('/api/video-convert', {method:'POST', body:JSON.stringify({path, format:$('#videoConvertFormat').value, quality:$('#videoConvertQuality').value, folder:$('#videoConvertFolder').value, save_path:videoConvertUI.target?.path || '', overwrite:videoConvertUI.target?.overwrite === true})});
      videoConvertResetTarget();
      await loadDownloads();
      toast('Conversión añadida', 'Revisa el progreso en Descargas. El video original se conserva.', 'success');
      navigate('downloads');
    } catch (error) { toast('No se pudo iniciar la conversión', error.message, 'error'); }
    finally { setVideoConvertBusy(false); }
  };
  updateVideoConvertFormat();
}
