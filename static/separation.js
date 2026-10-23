const separationUI = { busy: false, models: {}, cards: new Map(), completed: new Set() };
const separationNames = {
  separate_2: ['Voz', 'Música'],
  separate_4: ['Voz', 'Batería', 'Bajo', 'Otros'],
  separate_6: ['Voz', 'Batería', 'Bajo', 'Otros', 'Guitarra', 'Piano'],
};
function separationMode() { return $('input[name="separationMode"]:checked').value; }
function updateSeparationOptions() {
  const mode = separationMode(), model = separationUI.models[mode];
  $('#separationStemTags').replaceChildren(...separationNames[mode].map(name => {
    const tag = document.createElement('span'); tag.textContent = name; return tag;
  }));
  $('#separationModelTitle').textContent = model?.ready ? 'Modelo disponible en este equipo' : 'Preparación inicial del modelo';
  $('#separationModelInfo').textContent = model?.ready
    ? 'Puedes separar sin Internet. El audio se procesa en tu computadora.'
    : `Al iniciar se descargarán aproximadamente ${model?.megabytes || (mode === 'separate_6' ? 136 : 166)} MB. El modelo se guarda para las siguientes separaciones. Tu audio no se sube a ningún servidor.`;
  $('#separationQuality').disabled = separationUI.busy || $('#separationFormat').value !== 'mp3';
  $('#separationStart').disabled = separationUI.busy || !$('#separationFile').value;
}
function separationBusy(value) {
  separationUI.busy = value;
  $$('#page-separate input, #page-separate select, #separationChoose, #separationBrowse, #separationStart').forEach(control => { control.disabled = value; });
  updateSeparationOptions();
}
async function refreshSeparationModels() {
  try { separationUI.models = (await api('/api/separation/models')).models; updateSeparationOptions(); }
  catch { /* Separating remains available; the worker reports download errors. */ }
}
function initSeparation() {
  $('#separationFolder').value = state.settings.separation_folder || state.settings.default_folder;
  $('#separationFolder').title = $('#separationFolder').value;
  $$('#page-separate input[name="separationMode"]').forEach(input => { input.onchange = updateSeparationOptions; });
  $('#separationFormat').onchange = updateSeparationOptions;
  $('#separationChoose').onclick = async () => {
    separationBusy(true);
    try {
      const data = await api('/api/separation/file', {method:'POST', body:'{}'});
      if (!data.cancelled) { $('#separationFile').value = data.path; $('#separationFile').title = data.path; }
    } catch(error) { toast('No se pudo seleccionar el archivo', error.message, 'error'); }
    finally { separationBusy(false); }
  };
  $('#separationBrowse').onclick = async () => {
    separationBusy(true);
    try {
      const folder = await pickFolder('#separationFolder');
      if (folder) await api('/api/settings', {method:'PUT', body:JSON.stringify({separation_folder:folder})});
    } catch(error) { toast('No se pudo guardar la carpeta', error.message, 'error'); }
    finally { separationBusy(false); }
  };
  $('#separationStart').onclick = async () => {
    if (separationUI.busy || !$('#separationFile').value) return;
    const payload = {path:$('#separationFile').value, mode:separationMode(), format:$('#separationFormat').value, quality:$('#separationQuality').value, folder:$('#separationFolder').value};
    separationBusy(true);
    try {
      await api('/api/separation', {method:'POST', body:JSON.stringify(payload)});
      await loadDownloads();
      toast('Separación añadida', 'Puedes seguir el progreso aquí o en Descargas.', 'success');
      $('#separationJobs').scrollIntoView({behavior:'smooth', block:'nearest'});
    } catch(error) { toast('No se pudo iniciar la separación', error.message, 'error'); }
    finally { separationBusy(false); }
  };
  $('#separationQueue').onclick = () => $('[data-page="downloads"]').click();
  refreshSeparationModels(); updateSeparationOptions();
}
function renderSeparationJobs() {
  const jobs = state.downloads.filter(job => job.mode.startsWith('separate_'));
  const container = $('#separationJobs');
  const ids = new Set(jobs.map(job=>job.id));
  for (const [id, card] of separationUI.cards) if (!ids.has(id)) { card.remove(); separationUI.cards.delete(id); }
  container.querySelector('.separation-empty')?.remove();
  if (!jobs.length) {
    const empty = document.createElement('div'); empty.className = 'separation-empty';
    empty.textContent = 'Aquí aparecerán tus separaciones de esta sesión. Las pistas anteriores están en Historial.';
    container.append(empty); return;
  }
  for (const job of jobs) {
    let card = separationUI.cards.get(job.id);
    if (!card) {
      card = document.createElement('article'); card.className = 'separation-job';
      card.innerHTML = `<div class="separation-heading"><strong class="separation-job-title"></strong><span class="status-chip"></span></div><p class="separation-phase" role="status"></p><div class="progress-track" role="progressbar" aria-label="Progreso de separación" aria-valuemin="0" aria-valuemax="100"><i></i></div><div class="separation-job-actions"></div><div class="separation-stems"></div>`;
      container.prepend(card); separationUI.cards.set(job.id, card);
    }
    card.querySelector('.separation-job-title').textContent = job.title;
    const chip = card.querySelector('.status-chip'); chip.textContent = job.status; chip.className = 'status-chip '+statusClass(job.status);
    card.querySelector('.separation-phase').textContent = job.error || job.phase || 'En cola';
    const percentage = Math.max(0, Math.min(100, Number(job.progress) || 0));
    card.querySelector('.progress-track i').style.width = percentage+'%';
    card.querySelector('.progress-track').setAttribute('aria-valuenow', String(Math.round(percentage)));
    if (card.dataset.status === job.status) continue; // Preserve audio playback while polling.
    card.dataset.status = job.status;
    const actions = card.querySelector('.separation-job-actions'); actions.replaceChildren();
    const button = document.createElement('button'); button.type = 'button'; button.className = 'secondary-button';
    if (!['Completado','Cancelado','Error'].includes(job.status)) {
      button.textContent = 'Cancelar separación'; button.onclick = () => downloadAction('cancel', job.id); actions.append(button);
    } else if (job.status === 'Completado') {
      button.textContent = 'Abrir carpeta de pistas'; button.onclick = () => openPath(job.final_path); actions.append(button);
      const stems = card.querySelector('.separation-stems'); stems.replaceChildren();
      (job.outputs || []).forEach((output, index) => {
        const track = document.createElement('div'); track.className = 'separation-track';
        const name = document.createElement('strong'); name.textContent = output.name;
        const audio = document.createElement('audio'); audio.controls = true; audio.preload = 'none';
        audio.src = `/api/separation/${encodeURIComponent(job.id)}/audio/${index}`;
        audio.setAttribute('aria-label', 'Escuchar '+output.name);
        audio.onplay = () => $$('#separationJobs audio').forEach(other => { if (other !== audio) other.pause(); });
        const show = document.createElement('button'); show.type = 'button'; show.className = 'text-button'; show.textContent = 'Mostrar archivo'; show.onclick = () => openPath(output.path);
        audio.onerror = () => { show.textContent = 'Abrir ubicación · vista previa no disponible'; };
        track.append(name, audio, show); stems.append(track);
      });
      if (!separationUI.completed.has(job.id)) { separationUI.completed.add(job.id); refreshSeparationModels(); }
    }
  }
}
