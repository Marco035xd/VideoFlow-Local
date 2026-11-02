function audioTrackOptionLabel(track) {
  const t = window.VideoFlowI18n.t;
  let language = track.language || '';
  try {
    if (language) language = new Intl.DisplayNames([window.VideoFlowI18n.locale], {type:'language'}).of(language.replace(/-desc$/, ''));
  } catch { /* Keep the language code when Windows cannot name it. */ }
  const name = track.name || language || t('Pista de audio');
  const details = [name];
  if (track.language && track.name) details.push(track.language);
  if (track.original) details.push(t('Original'));
  if (track.descriptive) details.push(t('Audiodescripción'));
  if (track.default) details.push(t('Predeterminada'));
  return details.join(' · ');
}

function selectedAudioTrack() {
  if (!state.video || $('#modeSelect').value === 'video_only') return null;
  return (state.video.audio_tracks || []).find(track => track.id === $('#audioTrackSelect').value) || null;
}

function renderAudioTracks(preferred) {
  const select = $('#audioTrackSelect');
  const selected = preferred ?? select.value;
  const tracks = state.video?.audio_tracks || [];
  const automatic = document.createElement('option');
  automatic.value = '';
  automatic.textContent = window.VideoFlowI18n.t('Automático · recomendado');
  select.replaceChildren(automatic);
  for (const track of tracks) {
    const option = document.createElement('option');
    option.value = track.id;
    option.textContent = audioTrackOptionLabel(track);
    select.append(option);
  }
  select.value = tracks.some(track => track.id === selected) ? selected : '';
  syncAudioTrackMode();
}

function syncAudioTrackMode() {
  const silent = $('#modeSelect').value === 'video_only';
  const tracks = state.video?.audio_tracks || [];
  $('#audioTrackSelect').disabled = silent || !tracks.length;
  const status = $('#audioTrackStatus');
  if (silent) status.textContent = 'Solo video no incluye ninguna pista de audio.';
  else if (!tracks.length) status.textContent = 'El sitio no ha informado pistas de audio seleccionables para este video. Se usará el audio disponible automáticamente.';
  else if (tracks.length === 1) status.textContent = 'Se detectó una pista de audio. Puedes elegirla o usar la selección automática.';
  else status.textContent = `Hay ${tracks.length} pistas de audio disponibles. Elige cuál incluir en la descarga.`;
  $('#audioTrackDetail').textContent = selectedAudioTrack() ? audioTrackOptionLabel(selectedAudioTrack()) : '';
}

function audioTrackRequest() {
  const track = selectedAudioTrack();
  return track ? {audio_track:track.id, audio_track_label:track.label, audio_track_language:track.language} : {};
}

function initAudioTracks() {
  $('#audioTrackSelect').addEventListener('change', () => { syncAudioTrackMode(); updateEstimate(); });
  document.addEventListener('videoflow:language', () => { if (state.video) renderAudioTracks(); });
}
