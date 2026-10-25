/* Shared playback controls for the main player and its floating window. */
class LocalPlayback {
  constructor(video, {playButton, restartButton, message, speed, visible = () => true} = {}) {
    this.video = video;
    this.playButton = playButton;
    this.restartButton = restartButton;
    this.message = message;
    this.speed = speed;
    this.visible = visible;
    this.resumeOnReturn = false;
    this.operation = 0;
    this.blobUrl = null;
    playButton?.addEventListener('click', () => this.toggle());
    restartButton?.addEventListener('click', () => this.play(true));
    for (const name of ['play', 'pause', 'ended', 'loadedmetadata', 'emptied']) {
      video.addEventListener(name, () => this.update());
    }
    video.addEventListener('loadedmetadata', () => {
      video.playbackRate = Number(speed?.value || 1);
    });
    video.addEventListener('ended', () => {
      this.resumeOnReturn = false;
      this.say('Video terminado. Puedes volver a reproducirlo.');
    });
    video.addEventListener('playing', () => this.say(''));
    video.addEventListener('error', () => this.say(
      'No se pudo reproducir este archivo. Si el códec no es compatible, conviértelo a MP4 H.264 en Convertir video.'
    ));
    video.addEventListener('keydown', event => {
      if (![' ', 'ArrowRight', 'ArrowLeft', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
      event.preventDefault();
      if (event.key === ' ') this.toggle();
      if (event.key === 'ArrowRight' && Number.isFinite(video.duration)) video.currentTime = Math.min(video.duration, video.currentTime + 10);
      if (event.key === 'ArrowLeft') video.currentTime = Math.max(0, video.currentTime - 10);
      if (event.key === 'ArrowUp') video.volume = Math.min(1, video.volume + .05);
      if (event.key === 'ArrowDown') video.volume = Math.max(0, video.volume - .05);
    });
    speed?.addEventListener('change', () => { video.playbackRate = Number(speed.value); });
    document.addEventListener('visibilitychange', () => this.visibilityChanged());
    this.update();
  }

  say(text) { if (this.message) this.message.textContent = text; }
  hasSource() { return Boolean(this.video.getAttribute('src')); }
  update() {
    if (this.playButton) {
      this.playButton.disabled = !this.hasSource();
      this.playButton.textContent = this.video.ended ? 'Volver a reproducir' : this.video.paused ? 'Reproducir' : 'Pausar';
    }
    if (this.restartButton) this.restartButton.disabled = !this.hasSource();
  }

  async open(url, blobUrl = null) {
    ++this.operation;
    this.resumeOnReturn = false;
    this.video.pause();
    const previousBlob = this.blobUrl;
    this.blobUrl = blobUrl;
    this.video.src = url;
    this.video.load();
    if (previousBlob) URL.revokeObjectURL(previousBlob);
    this.say('');
    this.update();
    if (this.visible() && !document.hidden) await this.play();
  }

  async play(fromStart = false) {
    if (!this.hasSource()) return;
    const operation = ++this.operation;
    const video = this.video;
    try {
      // WebView2 can leave an ended media element at its final frame.
      if (fromStart || video.ended || (Number.isFinite(video.duration) && video.currentTime >= video.duration)) video.currentTime = 0;
      if (video.error) {
        const position = fromStart ? 0 : video.currentTime;
        video.load();
        video.addEventListener('loadedmetadata', () => {
          if (operation === this.operation && Number.isFinite(video.duration)) video.currentTime = Math.min(position, Math.max(0, video.duration - .01));
        }, {once: true});
      }
      await video.play();
      if (operation === this.operation) this.say('');
    } catch (error) {
      if (operation !== this.operation || error.name === 'AbortError') return;
      this.say(error.name === 'NotAllowedError'
        ? 'Pulsa Reproducir para continuar con el video.'
        : 'No se pudo iniciar el video. Pulsa Reiniciar o vuelve a abrir el archivo.');
    }
    this.update();
  }

  toggle() {
    this.resumeOnReturn = false;
    if (this.video.paused || this.video.ended) return this.play();
    ++this.operation;
    this.video.pause();
  }

  visibilityChanged() {
    if (!this.visible() || document.hidden) {
      if (!this.video.paused && !this.video.ended) this.resumeOnReturn = true;
      ++this.operation;
      this.video.pause();
    } else if (this.resumeOnReturn) {
      this.resumeOnReturn = false;
      this.play();
    }
    this.update();
  }
}

function initMainPlayer() {
  const video = document.querySelector('#localPlayer');
  const target = document.querySelector('#playerDropTarget');
  const zone = document.querySelector('#playerDropZone');
  const playback = new LocalPlayback(video, {
    playButton: document.querySelector('#playerPlay'), restartButton: document.querySelector('#playerRestart'),
    message: document.querySelector('#playerMessage'), speed: document.querySelector('#playerSpeed'),
    visible: () => state.currentPage === 'player',
  });
  let token = null;
  let selection = 0;
  video.tabIndex = 0;
  window.openPlayerMedia = async (data, requestId = null) => {
    if (requestId !== null && target.dataset.dropId !== requestId) return;
    token = data.token || null;
    document.querySelector('#playerName').textContent = data.name;
    document.querySelector('#playerFloating').disabled = !token;
    document.querySelector('#playerPip').disabled = !document.pictureInPictureEnabled;
    target.classList.remove('is-dragging');
    await playback.open(data.url, data.blobUrl || null);
  };
  window.playerDropError = (message, requestId) => {
    if (target.dataset.dropId === requestId) playback.say(message);
  };
  document.querySelector('#playerOpen').onclick = async () => {
    const current = ++selection;
    target.dataset.dropId = String(current);
    try {
      const data = await api('/api/player', {method: 'POST', body: '{}'});
      if (!data.cancelled && current === selection) await window.openPlayerMedia(data, String(current));
    } catch (error) { toast('No se pudo abrir', error.message, 'error'); }
  };
  zone.onclick = () => document.querySelector('#playerOpen').click();
  zone.onkeydown = event => {
    if (!['Enter', ' '].includes(event.key)) return;
    event.preventDefault();
    zone.click();
  };
  const fileDrag = event => [...(event.dataTransfer?.types || [])].includes('Files');
  let depth = 0;
  target.addEventListener('dragenter', event => {
    if (!fileDrag(event)) return;
    event.preventDefault(); ++depth; target.classList.add('is-dragging');
  });
  target.addEventListener('dragover', event => {
    if (!fileDrag(event)) return;
    event.preventDefault(); event.dataTransfer.dropEffect = 'copy';
  });
  target.addEventListener('dragleave', () => {
    depth = Math.max(0, depth - 1);
    if (!depth) target.classList.remove('is-dragging');
  });
  target.addEventListener('drop', event => {
    event.preventDefault(); depth = 0; target.classList.remove('is-dragging');
    const files = [...(event.dataTransfer?.files || [])];
    if (!files.length) return;
    const requestId = String(++selection);
    event.videoflowDropId = requestId;
    target.dataset.dropId = requestId;
    if (files.length !== 1) return playback.say('Arrastra un solo video o audio para reproducirlo.');
    const file = files[0];
    if (!/^(video|audio)\//.test(file.type) && !/\.(mp4|mkv|mov|webm|avi|wmv|flv|mpeg|mpg|vob|m4v|ts|mp3|m4a|wav|flac|ogg|opus|aac)$/i.test(file.name)) {
      return playback.say('Elige un archivo de video o audio.');
    }
    // Desktop resolves the actual dropped file through pywebview's native event.
    if (target.dataset.nativeDrop === 'ready') return playback.say('Abriendo archivo…');
    const blobUrl = URL.createObjectURL(file);
    window.openPlayerMedia({url: blobUrl, blobUrl, name: file.name}, requestId);
  }, {capture: true});
  // Prevent a dropped file outside the panel from replacing the application page.
  for (const name of ['dragover', 'drop']) document.addEventListener(name, event => {
    if (fileDrag(event)) event.preventDefault();
  });
  window.addEventListener('videoflow:navigate', () => { depth = 0; target.classList.remove('is-dragging'); playback.visibilityChanged(); });
  document.querySelector('#playerFloating').onclick = async () => {
    if (!token) return;
    try {
      await api(`/api/player/${token}/floating`, {method: 'POST', body: '{}'});
      playback.resumeOnReturn = false;
      video.pause();
    } catch (error) { toast('No se pudo abrir la ventana', error.message, 'error'); }
  };
  document.querySelector('#playerPip').onclick = async () => {
    try {
      if (document.pictureInPictureElement) await document.exitPictureInPicture();
      else await video.requestPictureInPicture();
    } catch { toast('PiP no disponible', 'Usa el botón Ventana flotante.', 'info'); }
  };
  const brightness = document.querySelector('#playerBrightness');
  brightness.oninput = () => { video.style.filter = `brightness(${brightness.value}%)`; };
  let gesture = null;
  video.addEventListener('pointerdown', event => {
    const rect = video.getBoundingClientRect();
    if (event.button !== 0 || event.clientY > rect.bottom - 64) return;
    // Capture only after a deliberate vertical gesture, leaving ordinary clicks
    // and WebView2's native play/replay controls untouched.
    gesture = {id: event.pointerId, x: event.clientX, y: event.clientY, active: false,
      brightness: Number(brightness.value), volume: video.volume,
      left: event.clientX < rect.left + rect.width / 2, height: rect.height};
  });
  video.addEventListener('pointermove', event => {
    if (!gesture || event.pointerId !== gesture.id) return;
    const moved = gesture.y - event.clientY;
    if (!gesture.active) {
      if (Math.abs(moved) < 10 || Math.abs(moved) < Math.abs(event.clientX - gesture.x)) return;
      gesture.active = true; video.setPointerCapture(event.pointerId);
    }
    const delta = moved / gesture.height;
    if (gesture.left) { brightness.value = Math.max(50, Math.min(150, gesture.brightness + delta * 100)); brightness.oninput(); }
    else video.volume = Math.max(0, Math.min(1, gesture.volume + delta));
  });
  const endGesture = () => {
    if (gesture && video.hasPointerCapture(gesture.id)) video.releasePointerCapture(gesture.id);
    gesture = null;
  };
  video.addEventListener('pointerup', endGesture);
  video.addEventListener('pointercancel', endGesture);
  video.addEventListener('lostpointercapture', () => { gesture = null; });
  window.addEventListener('videoflow:navigate', endGesture);
  window.addEventListener('blur', endGesture);
  return playback;
}
