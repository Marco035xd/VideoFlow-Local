async function initWallpapers() {
  const gallery = $('#wallpaperGallery');
  const add = $('#wallpaperAdd');
  const status = $('#wallpaperStatus');
  const opacity = $('#wallpaperOpacity');
  const opacityValue = $('#wallpaperOpacityValue');
  const endpoint = '/api/appearance/wallpapers';
  let pending = false;
  let activePhoto = null;
  let queuedOpacity = null;

  function previewOpacity(value) {
    opacityValue.textContent = `${value} %`;
    document.body.style.setProperty('--wallpaper-opacity', `${value}%`);
  }

  function render({active, photos}) {
    activePhoto = photos.find(photo => photo.id === active) || null;
    opacity.disabled = !activePhoto;
    opacity.value = String(queuedOpacity?.photo === active ? queuedOpacity.opacity : activePhoto?.opacity ?? 54);
    previewOpacity(opacity.value);
    document.body.classList.toggle('has-app-wallpaper', Boolean(active));
    if (active) document.body.style.setProperty('--app-wallpaper', `url("${endpoint}/${encodeURIComponent(active)}/photo")`);
    else document.body.style.removeProperty('--app-wallpaper');

    const cards = new Map([...gallery.querySelectorAll('[data-wallpaper]')].map(card => [card.dataset.wallpaper, card]));
    let previous = cards.get('');
    for (const photo of photos) {
      if (cards.has(photo.id)) {
        previous = cards.get(photo.id);
        continue;
      }
      const card = document.createElement('button');
      card.type = 'button';
      card.className = 'wallpaper-card';
      card.dataset.wallpaper = photo.id;
      const image = document.createElement('img');
      image.className = 'wallpaper-thumb';
      image.src = `${endpoint}/${encodeURIComponent(photo.id)}/thumbnail`;
      image.alt = '';
      image.loading = 'lazy';
      const name = document.createElement('span');
      name.className = 'wallpaper-name';
      name.textContent = photo.name;
      name.title = photo.name;
      name.setAttribute('translate', 'no');
      card.append(image, name);
      previous.after(card);
      previous = card;
      cards.set(photo.id, card);
    }
    for (const [id, card] of cards) card.setAttribute('aria-pressed', String(id === (active || '')));
  }

  async function update(options, savingOpacity = false) {
    if (pending) return;
    pending = true;
    gallery.setAttribute('aria-busy', 'true');
    add.disabled = true;
    if (!savingOpacity) opacity.disabled = true;
    status.textContent = '';
    status.classList.remove('is-error');
    try {
      const result = await api(endpoint, options);
      render(result);
      if (options?.method && !result.cancelled) status.textContent = 'Fondo aplicado y guardado.';
    } catch (error) {
      status.textContent = error.message;
      status.classList.add('is-error');
      if (savingOpacity && !queuedOpacity) {
        opacity.value = String(activePhoto.opacity);
        previewOpacity(opacity.value);
      }
    } finally {
      pending = false;
      add.disabled = false;
      opacity.disabled = !activePhoto;
      gallery.setAttribute('aria-busy', 'false');
      if (queuedOpacity) saveOpacity();
    }
  }

  function saveOpacity() {
    if (pending || !queuedOpacity) return;
    const changes = queuedOpacity;
    queuedOpacity = null;
    update({method:'PUT', body:JSON.stringify(changes)}, true);
  }

  opacity.addEventListener('input', () => previewOpacity(opacity.value));
  opacity.addEventListener('change', () => {
    if (!activePhoto) return;
    queuedOpacity = {photo:activePhoto.id, opacity:Number(opacity.value)};
    saveOpacity();
  });

  add.addEventListener('click', () => update({method:'POST', body:'{}'}));
  gallery.addEventListener('click', event => {
    const card = event.target.closest('[data-wallpaper]');
    if (!card || card.getAttribute('aria-pressed') === 'true') return;
    update({method:'PUT', body:JSON.stringify({active:card.dataset.wallpaper || null})});
  });
  await update();
}
