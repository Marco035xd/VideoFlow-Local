// Session choices are opt-in and reset when the app is reopened.
let youtubeCookieToken = '';

function youtubeSessionChoice() {
  const choice = $('#youtubeBrowser').value;
  if (choice !== 'cookies') return choice;
  if (!youtubeCookieToken) throw new Error('Selecciona primero un archivo cookies.txt de YouTube.');
  return youtubeCookieToken;
}

function browserForSource(source = state.source) {
  const key = source.toLowerCase();
  if (key === 'youtube') return youtubeSessionChoice();
  return key === 'facebook' ? $('#facebookBrowser').value : '';
}

function analysisFeedback(message = '', error = false) {
  const status = $('#analysisStatus');
  status.textContent = message;
  status.classList.toggle('hidden', !message);
  status.classList.toggle('error-message', error);
}

function setYouTubeSessionBusy(busy) {
  $('#youtubeBrowser').disabled = busy;
  $('#youtubeCookieChoose').disabled = busy;
}

function invalidateYouTubeAnalysis() {
  if (state.video?.source === 'YouTube') {
    state.video = null;
    $('#videoResult').classList.add('hidden');
  }
  if (state.source === 'youtube') analysisFeedback('Sesión actualizada. Vuelve a analizar el video para usarla.');
}

function initYouTubeSession() {
  $('#youtubeBrowser').addEventListener('change', () => {
    const file = $('#youtubeBrowser').value === 'cookies';
    $('#youtubeCookieChoose').classList.toggle('hidden', !file);
    $('#youtubeCookieName').classList.toggle('hidden', !file || !youtubeCookieToken);
    $('#youtubeCookieHelp').classList.toggle('hidden', !file);
    invalidateYouTubeAnalysis();
  });
  $('#youtubeCookieChoose').onclick = async () => {
    setYouTubeSessionBusy(true);
    try {
      const data = await api('/api/youtube/session-file', {method: 'POST', body: '{}'});
      if (data.cancelled) return;
      youtubeCookieToken = data.token;
      $('#youtubeCookieName').textContent = data.name;
      $('#youtubeCookieName').classList.remove('hidden');
      invalidateYouTubeAnalysis();
    } catch (error) {
      analysisFeedback(error.message, true);
      toast('No se pudo cargar la sesión', error.message, 'error');
    } finally { setYouTubeSessionBusy(false); }
  };
  $('#collectionSessionSettings').onclick = () => {
    navigate('home');
    selectSource('youtube');
    $('#youtubeNotice').scrollIntoView({behavior: 'smooth', block: 'center'});
    $('#youtubeBrowser').focus({preventScroll: true});
  };
}
