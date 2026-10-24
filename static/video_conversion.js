const videoConvertUI = {busy: false, files: [], targets: new Map()};

function syncVideoConvertConcurrency() {
  $('#videoConvertConcurrency').textContent = state.settings?.max_concurrent === 0 ? "Sin límite de conversiones simultáneas. El rendimiento depende del equipo." : `Hasta ${state.settings?.max_concurrent || 3} conversiones simultáneas. Cambia este valor en Configuración.`;
}

function renderVideoConvertFiles() {
  const container = $('#videoConvertFiles');
  container.replaceChildren();
  $('#videoConvertCount').textContent = `${videoConvertUI.files.length} archivos`;
  $('#videoConvertStart').disabled = videoConvertUI.busy || videoConvertUI.files.length === 0;
  if (!videoConvertUI.files.length) {
    const empty = document.createElement('div');
    empty.className = 'separation-empty';
    empty.textContent = 'Ningún video seleccionado. Elige varios archivos en una sola ventana.';
    container.append(empty);
    return;
  }
  for (const path of videoConvertUI.files) {
    const row = document.createElement('div'); row.className = 'conversion-file';
    const info = document.createElement('div'); info.className = 'conversion-file-info';
    const name = document.createElement('strong'); name.textContent = path.split(/[\\/]/).pop(); name.title = path;
    const destination = document.createElement('small');
    destination.textContent = videoConvertUI.targets.has(path)
      ? `Guardar en: ${videoConvertUI.targets.get(path).path}`
      : `Nombre automático · ${$('#videoConvertFolder').value}`;
    info.append(name, destination);
    const actions = document.createElement('div'); actions.className = 'conversion-file-actions';
    const save = document.createElement('button'); save.type = 'button'; save.className = 'secondary-button'; save.textContent = 'Guardar como…'; save.disabled = videoConvertUI.busy;
    save.setAttribute('aria-label', `Guardar como ${name.textContent}`);
    save.onclick = () => chooseVideoConvertTarget(path);
    const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'text-button'; remove.textContent = 'Quitar'; remove.disabled = videoConvertUI.busy;
    remove.setAttribute('aria-label', `Quitar ${name.textContent}`);
    remove.onclick = () => {
      videoConvertUI.files = videoConvertUI.files.filter(file => file !== path);
      videoConvertUI.targets.delete(path);
      renderVideoConvertFiles();
    };
    actions.append(save, remove); row.append(info, actions); container.append(row);
  }
}

function setVideoConvertBusy(busy) {
  videoConvertUI.busy = busy;
  for (const id of ['videoConvertChoose', 'videoConvertFormat', 'videoConvertQuality', 'videoConvertBrowse']) {
    $('#' + id).disabled = busy;
  }
  renderVideoConvertFiles();
}

async function chooseVideoConvertTarget(path) {
  setVideoConvertBusy(true);
  try {
    const result = await api('/api/video-save-path', {method:'POST', body:JSON.stringify({
      path, format:$('#videoConvertFormat').value,
      initial:videoConvertUI.targets.get(path)?.folder || $('#videoConvertFolder').value,
    })});
    if (!result.cancelled) videoConvertUI.targets.set(path, result);
  } catch (error) { toast('No se pudo elegir el archivo de salida', error.message, 'error'); }
  finally { setVideoConvertBusy(false); }
}

function updateVideoConvertFormat() {
  videoConvertUI.targets.clear();
  renderVideoConvertFiles();
  const fmt = $('#videoConvertFormat').value;
  const notice = $('#videoConvertNotice');
  const title = notice.querySelector('strong');
  const detail = notice.querySelector('p');
  if (fmt === 'mp4' || fmt === 'mov') {
    title.textContent = fmt === 'mp4' ? 'MP4 compatible para edición' : 'MOV con H.264 y AAC';
    detail.textContent = 'Se genera un archivo nuevo con H.264, color YUV 4:2:0, audio AAC y fotogramas constantes. MP4 a MP4 cambia el contenido interno, no solo el nombre.';
  } else if (fmt === 'avi') {
    title.textContent = 'AVI con MPEG-4 y MP3';
    detail.textContent = 'Conversión a MPEG-4, audio MP3 a 320 kbps y fotogramas constantes.';
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
        const added = [...new Set([...videoConvertUI.files, ...(result.paths || [result.path]).filter(Boolean)])];
        videoConvertUI.files = added;
      }
    } catch (error) { toast('No se pudieron seleccionar los videos', error.message, 'error'); }
    finally { setVideoConvertBusy(false); }
  };
  $('#videoConvertBrowse').onclick = async () => {
    setVideoConvertBusy(true);
    try {
      const folder = await pickFolder('#videoConvertFolder');
      if (folder) await api('/api/settings', {method:'PUT', body:JSON.stringify({video_conversion_folder:folder})});
    } catch (error) { toast('No se pudo elegir la carpeta', error.message, 'error'); }
    finally { setVideoConvertBusy(false); }
  };
  $('#videoConvertStart').onclick = async () => {
    const files = [...videoConvertUI.files];
    if (!files.length) return toast('Selecciona videos', 'Elige uno o varios videos para convertir.', 'error');
    const format = $('#videoConvertFormat').value;
    const quality = $('#videoConvertQuality').value;
    const folder = $('#videoConvertFolder').value;
    const failed = [];
    let queued = 0;
    setVideoConvertBusy(true);
    $('#videoConvertResults').replaceChildren();
    try {
      for (const path of files) {
        try {
          const target = videoConvertUI.targets.get(path);
          await api('/api/video-convert', {method:'POST', body:JSON.stringify({
            path, format, quality, folder,
            save_path:target?.path || '', overwrite:target?.overwrite === true,
          })});
          videoConvertUI.targets.delete(path);
          queued += 1;
          resultLine('#videoConvertResults', path, 'Añadido a la cola');
        } catch (error) {
          failed.push(path);
          resultLine('#videoConvertResults', path, error.message);
        }
      }
      videoConvertUI.files = failed;
      await loadDownloads();
      toast('Lote de conversión', `${queued} añadidos a la cola; ${failed.length} pendientes de revisar.`, failed.length ? 'info' : 'success');
      if (!failed.length) navigate('downloads');
    } catch (error) { toast('No se pudo actualizar la cola', error.message, 'error'); }
    finally { setVideoConvertBusy(false); }
  };
  syncVideoConvertConcurrency();
  updateVideoConvertFormat();
}
