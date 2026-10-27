const compressionUI = {busy: false, files: [], targets: new Map()};

function isCompressionInput(path) {
  const normalize = value => value.replaceAll('\\', '/').toLowerCase();
  return compressionUI.files.some(file => normalize(file.path) === normalize(path));
}

function compressionBytes(value) {
  if (!Number.isFinite(value) || value < 0) return '—';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let index = 0;
  while (value >= 1024 && index < units.length - 1) { value /= 1024; index++; }
  return `${value.toLocaleString(window.VideoFlowI18n.locale, {maximumFractionDigits: index ? 1 : 0})} ${units[index]}`;
}

function syncCompressionConcurrency() {
  $('#compressionConcurrency').textContent = state.settings?.max_concurrent === 0
    ? 'Sin límite de compresiones simultáneas. El rendimiento depende del equipo.'
    : `Hasta ${state.settings?.max_concurrent || 3} compresiones simultáneas. Cambia este valor en Configuración.`;
}

function renderCompressionFiles() {
  const container = $('#compressionFiles');
  container.replaceChildren();
  const reduction = Number($('#compressionReduction').value);
  const ratio = (100 - reduction) / 100;
  const total = compressionUI.files.reduce((sum, file) => sum + file.size, 0);
  $('#compressionCount').textContent = `${compressionUI.files.length} archivos`;
  $('#compressionHeroReduction').textContent = `−${reduction}%`;
  $('#compressionOriginalSize').textContent = total ? compressionBytes(total) : '—';
  $('#compressionTargetSize').textContent = total ? compressionBytes(total * ratio) : '—';
  $('#compressionSavedSize').textContent = total ? compressionBytes(total * (1 - ratio)) : '—';
  $('#compressionStart').disabled = compressionUI.busy || !compressionUI.files.length;
  if (!compressionUI.files.length) {
    const empty = document.createElement('div'); empty.className = 'separation-empty';
    empty.textContent = 'Selecciona uno o varios videos para calcular el tamaño aproximado.';
    container.append(empty);
  }
  for (const file of compressionUI.files) {
    const row = document.createElement('div'); row.className = 'conversion-file';
    const info = document.createElement('div'); info.className = 'conversion-file-info';
    const name = document.createElement('strong'); name.textContent = file.path.split(/[\\/]/).pop(); name.title = file.path;
    const sizes = document.createElement('small');
    sizes.textContent = `${compressionBytes(file.size)} → aproximadamente ${compressionBytes(file.size * ratio)}`;
    const destination = document.createElement('small');
    const label = document.createElement('span'); label.textContent = compressionUI.targets.has(file.path) ? 'Guardar en:' : 'Nombre automático';
    const path = document.createElement('span'); path.setAttribute('translate', 'no');
    path.textContent = compressionUI.targets.get(file.path)?.path || $('#compressionFolder').value;
    destination.append(label, document.createTextNode(' · '), path);
    info.append(name, sizes, destination);
    const actions = document.createElement('div'); actions.className = 'conversion-file-actions';
    const save = document.createElement('button'); save.type = 'button'; save.className = 'secondary-button';
    save.textContent = 'Guardar como…'; save.disabled = compressionUI.busy;
    save.setAttribute('aria-label', `Guardar como ${name.textContent}`);
    save.onclick = () => chooseCompressionTarget(file.path);
    const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'text-button';
    remove.textContent = 'Quitar'; remove.disabled = compressionUI.busy;
    remove.setAttribute('aria-label', `Quitar ${name.textContent}`);
    remove.onclick = () => {
      compressionUI.files = compressionUI.files.filter(item => item.path !== file.path);
      compressionUI.targets.delete(file.path);
      renderCompressionFiles();
    };
    actions.append(save, remove); row.append(info, actions); container.append(row);
  }
}

function setCompressionBusy(busy) {
  compressionUI.busy = busy;
  for (const id of ['compressionChoose', 'compressionReduction', 'compressionHeight', 'compressionBrowse']) $('#' + id).disabled = busy;
  renderCompressionFiles();
}

async function chooseCompressionTarget(path) {
  if (compressionUI.busy) return;
  setCompressionBusy(true);
  try {
    const result = await api('/api/compression-save-path', {method:'POST', body:JSON.stringify({
      path, initial:compressionUI.targets.get(path)?.folder || $('#compressionFolder').value,
    })});
    if (!result.cancelled) {
      if (isCompressionInput(result.path)) throw new Error('El destino coincide con un video seleccionado. Elige otro nombre para conservar los originales.');
      compressionUI.targets.set(path, result);
    }
  } catch(error) { toast('No se pudo elegir el archivo de salida', error.message, 'error'); }
  finally { setCompressionBusy(false); }
}

function initVideoCompression() {
  $('#compressionFolder').value = state.settings.compression_folder || state.settings.default_folder;
  $('#compressionFolder').title = $('#compressionFolder').value;
  $('#compressionReduction').onchange = renderCompressionFiles;
  $('#compressionChoose').onclick = async () => {
    if (compressionUI.busy) return;
    setCompressionBusy(true);
    try {
      const result = await api('/api/compression-files', {method:'POST', body:'{}'});
      if (!result.cancelled) {
        const files = new Map(compressionUI.files.map(file => [file.path, file]));
        for (const file of result.files) files.set(file.path, file);
        compressionUI.files = [...files.values()];
        for (const [source, target] of compressionUI.targets) {
          if (isCompressionInput(target.path)) compressionUI.targets.delete(source);
        }
      }
    } catch(error) { toast('No se pudieron seleccionar los videos', error.message, 'error'); }
    finally { setCompressionBusy(false); }
  };
  $('#compressionBrowse').onclick = async () => {
    if (compressionUI.busy) return;
    setCompressionBusy(true);
    const previous = $('#compressionFolder').value;
    try {
      const folder = await pickFolder('#compressionFolder');
      if (folder) {
        const result = await api('/api/settings', {method:'PUT', body:JSON.stringify({compression_folder:folder})});
        state.settings.compression_folder = result.settings.compression_folder;
        $('#compressionFolder').title = folder;
      }
    } catch(error) {
      $('#compressionFolder').value = previous;
      toast('No se pudo elegir la carpeta', error.message, 'error');
    } finally { setCompressionBusy(false); }
  };
  $('#compressionStart').onclick = async () => {
    if (compressionUI.busy || !compressionUI.files.length) return;
    const files = [...compressionUI.files], failed = [];
    const reduction = $('#compressionReduction').value, max_height = Number($('#compressionHeight').value);
    const folder = $('#compressionFolder').value;
    let queued = 0;
    setCompressionBusy(true);
    $('#compressionResults').replaceChildren();
    try {
      for (const file of files) {
        try {
          const target = compressionUI.targets.get(file.path);
          const data = await api('/api/video-compress', {method:'POST', body:JSON.stringify({
            path:file.path, reduction, max_height, folder,
            save_path:target?.path || '', overwrite:target?.overwrite === true,
          })});
          state.previousStatuses.set(data.download.id, data.download.status);
          compressionUI.targets.delete(file.path);
          queued++;
          resultLine('#compressionResults', file.path, 'Añadido a la cola');
        } catch(error) {
          failed.push(file);
          resultLine('#compressionResults', file.path, error.message);
        }
      }
      compressionUI.files = failed;
      await loadDownloads();
      toast('Lote de compresión', `${queued} añadidos a la cola; ${failed.length} pendientes de revisar.`, failed.length ? 'info' : 'success');
      if (!failed.length) navigate('downloads');
    } catch(error) { toast('No se pudo actualizar la cola', error.message, 'error'); }
    finally { setCompressionBusy(false); }
  };
  document.addEventListener('videoflow:language', () => { renderCompressionFiles(); syncCompressionConcurrency(); });
  renderCompressionFiles();
  syncCompressionConcurrency();
}
