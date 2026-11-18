(() => {
  const {token, preferences} = JSON.parse(document.querySelector('#floatingBoot').textContent);
  const get = name => document.querySelector('#floating' + name);
  const shell = get('Shell');
  const isPip = shell.classList.contains('pip-shell');
  const playback = new LocalPlayback(get('Video'), {
    playButton: get('Play'), restartButton: get('Restart'), message: get('Message'), keepPlayingHidden: true,
  }).bindControls('floating', shell).bindSurfaceClick({draggable:isPip});
  const session = new PlayerSession(playback, 'floating', token);
  session.tick();

  const windowUrl = `/api/player/${token}/window`;
  const dialog = get('Options');
  const opacity = get('Opacity');
  let current = preferences;
  let themeKey;
  let background;
  let lastOpacity;
  let reading = false;
  let changing = false;

  function showOpacity() {
    get('OpacityValue').textContent = `${opacity.value} %`;
    playback.fillRange(opacity, Number(opacity.value) - 25, 75);
  }

  function render(preferences) {
    current = preferences;
    const key = JSON.stringify([current.theme, current.appearance, appearanceMedia.matches]);
    if (key !== themeKey) {
      applyAppearancePalette(current);
      themeKey = key;
    }
    if (current.background !== background) {
      const image = current.background ? `url("/api/player/background?v=${encodeURIComponent(current.background)}")` : 'none';
      shell.style.setProperty('--player-background', image);
      shell.classList.toggle('has-background', Boolean(current.background));
      get('Clear').disabled = !current.background;
      background = current.background;
    }
    if (current.opacity !== lastOpacity) {
      opacity.value = String(current.opacity);
      showOpacity();
      lastOpacity = current.opacity;
    }
  }

  async function syncPreferences() {
    if (changing || reading) return;
    reading = true;
    try {
      const response = await fetch(windowUrl);
      if (response.ok && !changing) render((await response.json()).preferences);
    } catch {
      // A transient read failure can wait for the next refresh.
    } finally { reading = false; }
  }

  async function change(action, data = {}) {
    if (changing) return;
    changing = true;
    opacity.disabled = true;
    get('OptionsMessage').textContent = '';
    try {
      const response = await fetch(windowUrl, {
        method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action, ...data}),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      render(result.preferences);
    } catch (error) {
      opacity.value = String(current.opacity);
      showOpacity();
      if (dialog.open) get('OptionsMessage').textContent = error.message;
      else playback.say(error.message);
    } finally {
      changing = false;
      opacity.disabled = false;
    }
  }

  get('Smaller').onclick = () => change('resize', {direction:-1});
  get('Larger').onclick = () => change('resize', {direction:1});
  get('Customize').onclick = () => dialog.showModal();
  get('Photo').onclick = () => change('pick_background');
  get('Clear').onclick = () => change('clear_background');
  opacity.oninput = showOpacity;
  opacity.onchange = () => change('opacity', {value:Number(opacity.value)});
  const close = async returnToMain => {
    await session.sending;
    if (!playback.remoteState) await session.command(playback.snapshot());
    await fetch(`/api/player/${token}/close`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({return_to_main:returnToMain}),
    });
  };
  get('Close').onclick = () => close(false);
  get('Return').onclick = () => close(true);

  let hideControls;
  if (isPip) {
    const hide = () => shell.classList.remove('pip-ui-visible');
    const reveal = () => {
      clearTimeout(hideControls);
      shell.classList.add('pip-ui-visible');
      hideControls = setTimeout(hide, 1800);
    };
    for (const name of ['pointermove', 'pointerdown', 'keydown']) shell.addEventListener(name, reveal);
    shell.addEventListener('pointerleave', () => { clearTimeout(hideControls); hide(); });
    reveal();
  }
  render(preferences);
  appearanceMedia.addEventListener('change', () => render(current));
  const syncTimer = setInterval(syncPreferences, 700);
  window.addEventListener('pagehide', () => {
    clearInterval(syncTimer);
    clearTimeout(hideControls);
    session.stop();
  });
})();
