/* Shared playback controls for the main player and its floating window. */
class LocalPlayback {
  constructor(video, {playButton, restartButton, message, speed, visible = () => true, keepPlayingHidden = false} = {}) {
    this.video = video;
    this.playButton = playButton;
    this.restartButton = restartButton;
    this.message = message;
    this.speed = speed;
    this.visible = visible;
    this.keepPlayingHidden = keepPlayingHidden;
    this.resumeOnReturn = false;
    this.operation = 0;
    this.blobUrl = null;
    playButton?.addEventListener('click', () => this.toggle());
    restartButton?.addEventListener('click', () => this.play(true));
    for (const name of ['play', 'pause', 'ended', 'loadedmetadata', 'emptied', 'durationchange', 'timeupdate', 'volumechange']) {
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
      if(this.remoteState){
        const view=this.remoteState;
        if(event.key===' ')this.toggle();
        if(event.key==='ArrowRight'||event.key==='ArrowLeft')this.session.command({position:Math.max(0,Math.min(view.duration,view.position+(event.key==='ArrowRight'?10:-10)))});
        if(event.key==='ArrowUp'||event.key==='ArrowDown')this.session.command({volume:Math.max(0,Math.min(1,view.volume+(event.key==='ArrowUp' ? .05 : -.05))),muted:false});
        return;
      }
      if (event.key === ' ') this.toggle();
      if (event.key === 'ArrowRight' && Number.isFinite(video.duration)) video.currentTime = Math.min(video.duration, video.currentTime + 10);
      if (event.key === 'ArrowLeft') video.currentTime = Math.max(0, video.currentTime - 10);
      if (event.key === 'ArrowUp') video.volume = Math.min(1, video.volume + .05);
      if (event.key === 'ArrowDown') video.volume = Math.max(0, video.volume - .05);
      if (event.key === 'ArrowUp' || event.key === 'ArrowDown') video.muted = video.volume === 0;
      this.session?.command(this.snapshot());
    });
    speed?.addEventListener('change', () => { video.playbackRate = Number(speed.value); this.session?.command({rate:video.playbackRate}); });
    document.addEventListener('visibilitychange', () => this.visibilityChanged());
    this.update();
  }

  say(text) { if (this.message) this.message.textContent = text; }
  hasSource() { return Boolean(this.video.getAttribute('src')); }
  snapshot() {
    if (this.remoteState) return {...this.remoteState};
    return {position:this.video.currentTime || 0, duration:Number.isFinite(this.video.duration)?this.video.duration:0,
      playing:!this.video.paused && !this.video.ended, volume:this.video.volume, muted:Boolean(this.video.muted),
      rate:this.video.playbackRate || 1, brightness:this.brightness || 100};
  }
  time(value) {
    const total = Math.max(0, Math.floor(Number.isFinite(value) ? value : 0));
    const seconds = String(total % 60).padStart(2, '0');
    const minutes = Math.floor(total / 60);
    return minutes >= 60 ? `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, '0')}:${seconds}` : `${minutes}:${seconds}`;
  }

  bindControls(prefix, shell) {
    const get = name => document.querySelector(`#${prefix}${name}`);
    this.controls = {seek:get('Seek'), elapsed:get('Elapsed'), duration:get('Duration'),
      volume:get('Volume'), volumeValue:get('VolumeValue'), mute:get('Mute'), fullscreen:get('Fullscreen'), shell};
    this.scrubbing = false;
    this.lastVolume = this.video.volume || 1;
    const {seek, volume, mute, fullscreen} = this.controls;
    const seekToThumb = () => {
      const duration=this.remoteState?.duration || this.video.duration;
      if (!Number.isFinite(duration) || duration <= 0) return;
      try { this.video.currentTime = Math.max(0, Math.min(duration, Number(seek.value))); }
      catch { this.say('Espera a que el archivo termine de abrirse para cambiar la posición.'); }
      this.controls.elapsed.textContent = this.time(Number(seek.value));
      this.fillRange(seek, Number(seek.value), duration);
      this.session?.command({position:Number(seek.value)});
    };
    seek.addEventListener('pointerdown', () => { this.scrubbing = true; });
    seek.addEventListener('input', seekToThumb);
    const finishSeek = () => { seekToThumb(); this.scrubbing = false; this.update(); };
    seek.addEventListener('change', finishSeek);
    seek.addEventListener('pointerup', finishSeek);
    seek.addEventListener('pointercancel', () => { this.scrubbing = false; this.update(); });
    seek.addEventListener('blur', () => { this.scrubbing = false; this.update(); });
    volume.addEventListener('input', () => {
      this.video.volume = Math.max(0, Math.min(1, Number(volume.value) / 100));
      this.video.muted = this.video.volume === 0;
      if (this.video.volume > 0) this.lastVolume = this.video.volume;
      this.session?.command({volume:this.video.volume, muted:this.video.muted});
      this.update();
    });
    mute.addEventListener('click', () => {
      if(this.remoteState){
        const view=this.remoteState,unmute=view.muted||view.volume===0;
        this.session.command({muted:!unmute,volume:unmute?(view.volume||this.lastVolume):view.volume});return;
      }
      if (this.video.muted || this.video.volume === 0) {
        this.video.volume = this.video.volume || this.lastVolume;
        this.video.muted = false;
      } else {
        this.lastVolume = this.video.volume;
        this.video.muted = true;
      }
      this.session?.command({volume:this.video.volume, muted:this.video.muted});
      this.update();
    });
    fullscreen.addEventListener('click', async () => {
      try {
        if (document.fullscreenElement === shell) await document.exitFullscreen();
        else await shell.requestFullscreen();
      } catch { this.say('No se pudo abrir la pantalla completa. Puedes usar Ventana flotante.'); }
    });
    document.addEventListener('fullscreenchange', () => this.update());
    this.update();
    return this;
  }

  fillRange(range, value, maximum) {
    range.style.setProperty('--range-fill', `${maximum > 0 ? Math.max(0, Math.min(100, value / maximum * 100)) : 0}%`);
  }

  update() {
    const view = this.remoteState;
    if (this.playButton) {
      this.playButton.disabled = !this.hasSource();
      const ended = view ? view.duration>0 && view.position>=view.duration : this.video.ended;
      const playing = view ? view.playing : !this.video.paused;
      this.playButton.textContent = ended ? 'Volver a reproducir' : playing ? 'Pausar' : 'Reproducir';
    }
    if (this.restartButton) this.restartButton.disabled = !this.hasSource();
    if (this.controls) {
      const {seek, elapsed, duration, volume, volumeValue, mute, fullscreen, shell} = this.controls;
      const length = view ? view.duration : Number.isFinite(this.video.duration) ? this.video.duration : 0;
      seek.disabled = !this.hasSource() || length <= 0;
      seek.max = String(length);
      duration.textContent = this.time(length);
      if (!this.scrubbing) {
        const position = view ? view.position : this.video.currentTime || 0;
        seek.value = String(position);
        elapsed.textContent = this.time(position);
        this.fillRange(seek, position, length);
      }
      const level = (view ? view.muted : this.video.muted) ? 0 : Math.round((view ? view.volume : this.video.volume) * 100);
      volume.value = String(level); volumeValue.textContent = `${level} %`;
      this.fillRange(volume, level, 100);
      mute.textContent = level ? 'Silenciar' : 'Activar sonido';
      mute.setAttribute('aria-label', mute.textContent);
      mute.setAttribute('aria-pressed', String(!level));
      fullscreen.disabled = !this.hasSource() || !shell.requestFullscreen;
      fullscreen.textContent = document.fullscreenElement === shell ? 'Salir de pantalla completa' : 'Pantalla completa';
    }
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
    if (this.remoteState) return this.session.command({playing:true, ...(fromStart || this.remoteState.position>=this.remoteState.duration?{position:0}:{})});
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
      this.session?.command(this.snapshot());
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
    if (this.remoteState) return this.session.command({playing:!this.remoteState.playing,
      ...(this.remoteState.position>=this.remoteState.duration?{position:0}:{})});
    if (this.video.paused || this.video.ended) return this.play();
    ++this.operation;
    this.video.pause();
    this.session?.command(this.snapshot());
  }

  visibilityChanged() {
    if (this.keepPlayingHidden || this.remoteState || document.pictureInPictureElement === this.video) return;
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

class PlayerSession {
  constructor(playback, role, token) {
    this.playback=playback;this.role=role;this.token=token;this.revision=-1;this.owner=null;
    this.stopped=false;this.busy=false;this.applying=false;this.lastReport=0;
    playback.session=this;
    this.timer=setInterval(()=>this.tick(),250);
    playback.video.addEventListener('loadedmetadata',()=>this.tick());
  }
  async request(data) {
    const response=await fetch(`/api/player/${this.token}/state`,data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{});
    if(!response.ok)throw new Error('No se pudo sincronizar el reproductor.');
    return (await response.json()).state;
  }
  command(changes) {
    if(this.stopped)return Promise.resolve();
    this.pending={...this.pending,...changes};
    if(this.sending)return this.sending;
    this.sending=(async()=>{
      while(this.pending&&!this.stopped){const changes=this.pending;this.pending=null;await this.receive(await this.request({changes}));}
    })().catch(error=>this.playback.say(error.message)).finally(()=>{this.sending=null;});
    return this.sending;
  }
  async receive(state) {
    if(this.stopped||!state||state.revision<this.revision)return;
    const changed=state.revision!==this.revision||state.owner!==this.owner;
    this.revision=state.revision;this.owner=state.owner;
    const playback=this.playback,video=playback.video;
    if(state.owner!==this.role){
      playback.remoteState=state;playback.resumeOnReturn=false;video.pause();
    }else{
      const wasRemote=Boolean(playback.remoteState);playback.remoteState=null;
      if((changed||wasRemote||this.waitingMetadata)&&!this.applying){
        if(video.readyState<1){this.waitingMetadata=true;this.revision=-1;return;}
        this.waitingMetadata=false;this.applying=true;
        try{
          if(Math.abs(video.currentTime-state.position)>.25)video.currentTime=state.position;
          video.volume=state.volume;video.muted=state.muted;video.playbackRate=state.rate;
          playback.brightness=state.brightness;video.style.filter=`brightness(${state.brightness}%)`;
          if(playback.speed)playback.speed.value=String(state.rate);
          if(state.playing&&(this.role==='floating'||(playback.visible()&&!document.hidden)))await video.play().catch(()=>playback.say('Pulsa Reproducir para continuar con el video.'));
          else video.pause();
        }finally{this.applying=false;}
      }
    }
    const notice=document.querySelector('#playerRemoteNotice');
    if(this.role==='main'&&notice)notice.classList.toggle('hidden',state.owner==='main');
    document.querySelector('#playerShell')?.classList.toggle('media-remote',this.role==='main'&&state.owner!=='main');
    playback.update();
  }
  async tick() {
    if(this.stopped||this.busy||this.sending)return;
    this.busy=true;
    try{
      await this.receive(await this.request());
      if(this.owner===this.role&&!this.applying&&!this.waitingMetadata&&performance.now()-this.lastReport>750){
        this.lastReport=performance.now();
        await this.receive(await this.request({role:this.role,revision:this.revision,report:this.playback.snapshot()}));
      }
    }catch{}finally{this.busy=false;}
  }
  stop(){this.stopped=true;clearInterval(this.timer);if(this.playback.session===this)this.playback.session=null;}
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
  playback.bindControls('player', document.querySelector('#playerShell'));
  let token = null;
  let selection = 0;
  video.tabIndex = 0;
  window.openPlayerMedia = async (data, requestId = null) => {
    if (requestId !== null && target.dataset.dropId !== requestId) return;
    if(token&&token!==data.token&&playback.remoteState)await api(`/api/player/${token}/close`,{method:'POST',body:'{}'});
    token = data.token || null;
    playback.session?.stop();playback.remoteState=null;
    document.querySelector('#playerName').textContent = data.name;
    document.querySelector('#playerFloating').disabled = !token;
    document.querySelector('#playerPip').disabled = !token && !document.pictureInPictureEnabled;
    target.classList.remove('is-dragging');
    await playback.open(data.url, data.blobUrl || null);
    if(token){const session=new PlayerSession(playback,'main',token);await session.command(playback.snapshot());}
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
  const openPopout = async mode => {
    if (!token) return;
    try {
      await playback.session?.sending;
      const palette=Object.fromEntries(['--surface-solid','--text','--muted','--line','--line-strong','--primary','--on-primary'].map(key=>[key,getComputedStyle(document.documentElement).getPropertyValue(key).trim()]));
      const data=await api(`/api/player/${token}/floating`, {method:'POST',body:JSON.stringify({mode,state:playback.snapshot(),palette})});
      playback.resumeOnReturn = false;
      video.pause();
      await playback.session?.receive(data.state);
    } catch (error) { toast('No se pudo abrir la ventana', error.message, 'error'); }
  };
  document.querySelector('#playerFloating').onclick=()=>openPopout('floating');
  document.querySelector('#playerReturn')?.addEventListener('click',async()=>{
    try{await api(`/api/player/${token}/close`,{method:'POST',body:JSON.stringify({return_to_main:true})});await playback.session?.tick();}
    catch(error){toast('No se pudo volver',error.message,'error');}
  });
  document.querySelector('#playerPip').onclick = async () => {
    if(window.pywebview&&token)return openPopout('pip');
    try {
      if (document.pictureInPictureElement) await document.exitPictureInPicture();
      else await video.requestPictureInPicture();
    } catch { toast('PiP no disponible', 'Usa el botón Ventana flotante.', 'info'); }
  };
  const brightness = document.querySelector('#playerBrightness');
  brightness.oninput = () => { playback.brightness=Number(brightness.value);video.style.filter = `brightness(${brightness.value}%)`;playback.session?.command({brightness:playback.brightness}); };
  let gesture = null;
  let suppressClickUntil = 0;
  video.controls = false;
  video.addEventListener('click', () => { if (performance.now() >= suppressClickUntil) playback.toggle(); });
  video.addEventListener('pointerdown', event => {
    const rect = video.getBoundingClientRect();
    if (event.button !== 0) return;
    // Only the video surface receives gestures; controls are separate siblings.
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
    else { video.volume = Math.max(0, Math.min(1, gesture.volume + delta)); video.muted = video.volume === 0;playback.session?.command({volume:video.volume,muted:video.muted}); }
  });
  const endGesture = () => {
    if (gesture?.active) suppressClickUntil = performance.now() + 250;
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
