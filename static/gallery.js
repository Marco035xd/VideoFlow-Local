let galleryRequest = 0;
let galleryOpening = false;

async function loadGallery() {
  const request = ++galleryRequest;
  const status = $('#galleryStatus');
  status.textContent = 'Cargando galería…';
  try {
    const {videos} = await api('/api/gallery');
    if (request !== galleryRequest) return;
    const cards = videos.map(video => {
      const card = $('#galleryCard').content.firstElementChild.cloneNode(true);
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
    $('#galleryEmpty').classList.toggle('hidden', videos.length > 0);
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
window.addEventListener('videoflow:navigate', ({detail}) => {
  if (detail.page === 'gallery') loadGallery();
});
