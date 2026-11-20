let galleryRequest = 0;
let galleryOpening = false;
let galleryVideos = null;

function normalizeGalleryTitle(value) {
  return value.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
}

function renderGallery() {
  if (!galleryVideos) return;
  const platform = $('#galleryPlatform').value;
  const query = normalizeGalleryTitle($('#gallerySearch').value).trim().split(/\s+/).filter(Boolean);
  const order = $('#galleryOrder').value;
  const videos = galleryVideos.filter(video =>
    (!platform || video.platform === platform) &&
    (!query.length || query.every(term => video.searchTitle.includes(term)))
  );
  if (order === 'oldest') videos.reverse();
  if (order === 'title') {
    const collator = new Intl.Collator(window.VideoFlowI18n.locale, {sensitivity: 'base', numeric: true});
    videos.sort((a, b) => collator.compare(a.title, b.title));
  }
  if (order === 'longest' || order === 'shortest') {
    const direction = order === 'longest' ? -1 : 1;
    videos.sort((a, b) => Number(!a.duration_seconds) - Number(!b.duration_seconds) ||
      direction * ((a.duration_seconds || 0) - (b.duration_seconds || 0)));
  }
  const template = $('#galleryCard').content.firstElementChild;
  const cards = videos.map(video => {
    const card = template.cloneNode(true);
    const artwork = card.querySelector('.gallery-thumbnail');
    artwork.addEventListener('error', () => { artwork.hidden = true; }, {once: true});
    artwork.src = `/api/gallery/${video.id}/thumbnail`;
    const logo = card.querySelector('.gallery-platform');
    logo.src = `/static/icons/${video.platform}.png`;
    logo.alt = video.source;
    const title = card.querySelector('.gallery-title');
    title.textContent = title.title = video.title;
    const duration = card.querySelector('.duration-badge');
    duration.textContent = video.duration;
    duration.hidden = video.duration === '0:00';
    card.addEventListener('click', () => playGalleryVideo(video.id));
    return card;
  });
  const grid = $('#galleryGrid');
  grid.replaceChildren(...cards);
  grid.inert = galleryOpening;
  const empty = $('#galleryEmpty');
  empty.classList.toggle('hidden', videos.length > 0);
  if (!videos.length) {
    empty.querySelector('h3').textContent = query.length ? 'No se encontraron videos' : platform
      ? 'No hay videos de esta plataforma'
      : 'Todavía no hay videos guardados';
    empty.querySelector('p').textContent = query.length ? 'Cambia el texto de búsqueda o el filtro de plataforma.' : platform
      ? 'Prueba con otra plataforma o muestra todos los videos.'
      : 'Los videos que descargues aparecerán aquí.';
  }
}

async function loadGallery() {
  const request = ++galleryRequest;
  const status = $('#galleryStatus');
  status.textContent = 'Cargando galería…';
  try {
    const {videos} = await api('/api/gallery');
    if (request !== galleryRequest) return;
    galleryVideos = videos.map(video => ({...video, searchTitle: normalizeGalleryTitle(video.title)}));
    renderGallery();
    status.textContent = galleryOpening ? 'Preparando el video…' : '';
  } catch (error) {
    if (request === galleryRequest) status.textContent = error.message;
  }
}

async function playGalleryVideo(id) {
  if (galleryOpening) return;
  galleryOpening = true;
  const grid = $('#galleryGrid');
  const status = $('#galleryStatus');
  grid.inert = true;
  status.textContent = 'Preparando el video…';
  try {
    const media = await api(`/api/gallery/${id}/play`, {method: 'POST'});
    if (state.currentPage === 'gallery') {
      navigate('player');
      await window.openPlayerMedia(media);
    }
    status.textContent = '';
  } catch (error) {
    status.textContent = error.message;
  } finally {
    galleryOpening = false;
    grid.inert = false;
  }
}

$('#openGallery').addEventListener('click', () => navigate('gallery'));
$('#galleryPlatform').addEventListener('change', renderGallery);
$('#gallerySearch').addEventListener('input', renderGallery);
$('#galleryOrder').addEventListener('change', renderGallery);
window.addEventListener('videoflow:navigate', ({detail}) => {
  if (detail.page === 'gallery') loadGallery();
});
