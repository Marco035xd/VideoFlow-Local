let ffmpegUpdateTimer;
let notifiedFFmpegVersion;

function renderFFmpegUpdate(update) {
  const installing = ['downloading', 'validating'].includes(update.install_status);
  const busy = installing || update.status === 'checking';
  const pending = update.pending_version;
  const status = $('#ffmpegUpdateStatus');
  const statusText = {
    idle: 'Se comprobará al iniciar la aplicación.',
    checking: 'Buscando actualizaciones de FFmpeg…',
    error: 'No se pudo comprobar. Puedes volver a intentarlo.',
    ready: update.available ? 'Hay una nueva versión de FFmpeg disponible.' : 'FFmpeg está actualizado.',
  };
  if (pending) {
    status.textContent = `FFmpeg ${pending} está listo. Cierra VideoFlow por completo y vuelve a abrirlo.`;
  } else if (update.install_status === 'downloading') {
    status.textContent = 'Descargando FFmpeg…';
  } else if (update.install_status === 'validating') {
    status.textContent = 'Verificando FFmpeg y FFprobe…';
  } else if (update.install_status === 'error' && !busy) {
    status.textContent = 'No se pudo actualizar FFmpeg.';
  } else {
    status.textContent = statusText[update.status];
  }

  const checkedAt = update.checked_at ? new Date(update.checked_at).toLocaleTimeString(window.VideoFlowI18n.locale,
    {hour: '2-digit', minute: '2-digit'}) : '';
  $('#ffmpegUpdateVersions').textContent = `Instalada: ${update.current || 'no identificada'} · Última versión: ${update.latest || 'por comprobar'}${checkedAt ? ` · Revisado: ${checkedAt}` : ''}`;
  const error = $('#ffmpegUpdateError');
  error.textContent = update.install_error || '';
  error.classList.toggle('hidden', !update.install_error || busy);
  const progress = $('#ffmpegUpdateProgress');
  progress.classList.toggle('hidden', !installing);
  if (update.install_status === 'downloading' && update.total) {
    progress.value = Math.min(100, update.downloaded * 100 / update.total);
  } else {
    progress.removeAttribute('value');
  }
  $('#ffmpegCheck').disabled = busy || Boolean(pending);
  $('#ffmpegInstall').disabled = busy;
  $('#ffmpegInstall').classList.toggle('hidden', !update.install_supported || !update.available || Boolean(pending));
  $('#ffmpegDownload').classList.toggle('hidden', !update.available || busy || Boolean(pending));

  if (update.available && !pending && !installing && update.latest !== notifiedFFmpegVersion) {
    notifiedFFmpegVersion = update.latest;
    toast('Actualización de FFmpeg', `Versión ${update.latest} disponible. Revisa Configuración.`, 'info', 7000);
  }
  clearTimeout(ffmpegUpdateTimer);
  if (busy) ffmpegUpdateTimer = setTimeout(pollFFmpegUpdate, 1000);
}

async function refreshFFmpegUpdates(check = false) {
  const data = await api('/api/updates/ffmpeg', check ? {method: 'POST', body: '{}'} : {});
  renderFFmpegUpdate(data.update);
  return data.update;
}

function pollFFmpegUpdate() {
  refreshFFmpegUpdates().catch(() => { ffmpegUpdateTimer = setTimeout(pollFFmpegUpdate, 2000); });
}

function initFFmpegUpdates() {
  document.addEventListener('videoflow:language', () => refreshFFmpegUpdates().catch(() => {}));
  $('#ffmpegCheck').onclick = () => refreshFFmpegUpdates(true).catch(error => toast('No se pudo comprobar', error.message, 'error'));
  $('#ffmpegInstall').onclick = async () => {
    const button = $('#ffmpegInstall');
    button.disabled = true;
    try {
      const {update} = await api('/api/updates/ffmpeg/install', {method: 'POST', body: '{}'});
      renderFFmpegUpdate(update);
    } catch (error) {
      button.disabled = false;
      toast('No se pudo actualizar FFmpeg.', error.message, 'error');
    }
  };
  refreshFFmpegUpdates().then(update => {
    if (update.status === 'idle') return refreshFFmpegUpdates(true);
  }).catch(() => {});
}
