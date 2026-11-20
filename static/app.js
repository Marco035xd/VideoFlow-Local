const state = {
  settings: null,
  video: null,
  downloads: [],
  history: [],
  previousStatuses: new Map(),
  currentPage: "home",
  confirmResolver: null,
  source: "youtube",
  destinationFolder: "",
  savePath: "",
  overwrite: false,
  removedDownloadsBusy: false,
  removedDownloadsRequest: 0,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const pageTitles = {
  home: "Nueva descarga",
  convert: "Video a audio",
  "video-convert": "Convertir video",
  compress: "Comprimir video",
  separate: "Voz e instrumentos",
  downloads: "Gestión de descargas",
  gallery: "Galería de descargas",
  history: "Historial",
  appearance: "Apariencia",
  profile: "Perfil",
  collections: "Listas y canales", player: "Reproductor", browser: "Navegador privado", vault: "Carpeta privada",
  settings: "Configuración",
};

async function api(path, options = {}) {
  const config = {
    headers: { "Content-Type": "application/json" },
    ...options,
  };
  const response = await fetch(path, config);
  let data;
  try {
    data = await response.json();
  } catch {
    data = { ok: false, error: "Respuesta no válida del servidor." };
  }
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `Error HTTP ${response.status}`);
  }
  return data;
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString(window.VideoFlowI18n.locale);
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(window.VideoFlowI18n.locale, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function qualityLabel(format, quality, source = "", mode = "") {
  if (mode === 'video_compress') return `Reducción objetivo: ${quality}%`;
  if (["wav", "flac"].includes(format)) return "Sin pérdida";
  if (format === "flac") return "Sin pérdida";
  if (String(quality) === "4320") return "8K (4320p)";
  if (format === "m4a") return source === "Local" ? `${quality} kbps` : "Original";
  if (format === "mp3") return `${quality} kbps`;
  if (format === "ogg") return `Vorbis · ${quality} kbps`;
  if (String(quality) === "0") return "Mejor disponible";
  if (["TikTok", "Reddit", "Instagram", "X", "Twitch"].includes(source)) return `${quality} px de alto`;
  if (String(quality) === "1440") return "2K (1440p)";
  if (String(quality) === "2160") return "4K (2160p)";
  return `${quality}p`;
}

const formatChoices = {
  video_audio: [["mp4", "MP4"], ["mkv", "MKV"], ["webm", "WEBM"], ["mov", "MOV"], ["avi", "AVI"], ["vob", "VOB"]],
  video_only: [["mp4", "MP4"], ["mkv", "MKV"], ["webm", "WEBM"], ["mov", "MOV"], ["avi", "AVI"]],
  audio: [["mp3", "MP3"], ["m4a", "M4A"], ["wav", "WAV"], ["flac", "FLAC"], ["ogg", "OGG · Vorbis"]],
};

const platformTabs = $$(".source-tab");
const platformNames = Object.fromEntries(platformTabs.map(tab => [tab.dataset.source, tab.dataset.platform]));
const platformExamples = Object.fromEntries(platformTabs.map(tab => [tab.dataset.source, tab.dataset.exampleUrl]));

function sourceForLink(link) {
  try {
    const url = new URL(link);
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) return null;
    const host = url.hostname.toLowerCase().replace(/\.+$/, "");
    const tab = platformTabs.find(button => button.dataset.domains.split(" ").some(
      domain => host === domain || host.endsWith("." + domain)
    ));
    if (tab?.dataset.source === "twitch") {
      const isClip = host === "clips.twitch.tv" ? url.pathname.length > 1
        : /^(?:(?:www|go|m)\.)?twitch\.tv$/.test(host) && /^\/(?:[^/]+\/)?clip\/[^/]+/.test(url.pathname);
      if (!isClip) return null;
    }
    return tab?.dataset.source ?? null;
  } catch {
    return null;
  }
}

function folderForSource(source = state.source) {
  return state.settings?.platform_folders?.[source.toLowerCase()] || state.settings?.default_folder || "";
}

function syncFolderSettings() {
  for (const source of Object.keys(platformNames)) {
    $(`#settingsFolder-${source}`).value = folderForSource(source);
  }
}

function rememberFolder(source, folder) {
  const sourceKey = source.toLowerCase();
  state.settings.platform_folders = { ...state.settings.platform_folders, [sourceKey]: folder };
  $(`#settingsFolder-${sourceKey}`).value = folder;
  syncBatchDestination();
}

function selectSource(source) {
  state.source = source;
  syncBatchDestination();
  for (const button of platformTabs) {
    const selected = button.dataset.source === source;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-pressed", String(selected));
  }
  $("#urlLabel").textContent = `Enlaces de ${platformNames[source]}`;
  $("#videoUrl").placeholder = platformExamples[source] + "\nPega varios enlaces, uno por línea";
  $("#sourceMark").src = `/static/icons/${source}.png`;
  $("#sourceHelp").textContent = source === 'twitch'
    ? 'Pega un enlace a un clip de Twitch. Puedes añadir varios clips a la cola.'
    : 'Un enlace: Analizar video. Varios enlaces: elige las opciones de abajo y pulsa «Añadir enlaces a la cola».';
  for (const panel of $$("[data-site-session]")) panel.classList.toggle("hidden", panel.dataset.siteSession !== source);
  $('#youtubeNotice').classList.toggle('hidden', source !== 'youtube');
  analysisFeedback();
  state.destinationFolder = folderForSource(source);
  state.savePath = "";
  state.overwrite = false;
  $("#folderPath").value = state.destinationFolder;
  $("#destinationLabel").textContent = `Destino de la descarga · ${platformNames[source]}`;
  $("#destinationHint").textContent = `Se guardará en la carpeta de ${platformNames[source]}. Usa «Guardar como» para cambiar nombre y ubicación.`;
}

function toast(title, message, type = "info", timeout = 4300, userContent = false, audible = true) {
  if (type === "error" && audible) window.VideoFlowSounds?.play("error");
  const item = document.createElement("div");
  item.className = `toast ${type}`;
  const icon = type === "success" ? "✓" : type === "error" ? "!" : "i";
  item.innerHTML = `
    <div class="toast-icon">${icon}</div>
    <div><strong>${escapeHtml(title)}</strong><p>${escapeHtml(message)}</p></div>
    <button class="toast-close" type="button" aria-label="Cerrar">×</button>
  `;
  if (userContent) item.querySelector('p').setAttribute('translate', 'no');
  item.querySelector(".toast-close").addEventListener("click", () => item.remove());
  $("#toastStack").appendChild(item);
  window.setTimeout(() => item.remove(), timeout);
}

function confirmAction(title, message) {
  $("#confirmTitle").textContent = title;
  $("#confirmMessage").textContent = message;
  $("#confirmModal").classList.remove("hidden");
  return new Promise((resolve) => {
    state.confirmResolver = resolve;
  });
}

function closeConfirm(result) {
  $("#confirmModal").classList.add("hidden");
  if (state.confirmResolver) state.confirmResolver(result);
  state.confirmResolver = null;
}

function navigate(page) {
  state.currentPage = page;
  $$(".page").forEach((node) => node.classList.remove("active-page"));
  $$(".nav-item").forEach((node) => node.classList.toggle("active", node.dataset.page === page));
  $(`#page-${page}`).classList.add("active-page");
  $("#pageTitle").textContent = pageTitles[page];
  window.dispatchEvent(new CustomEvent('videoflow:navigate', {detail: {page}}));
  if (page === "history") loadHistory();
  if (page === "collections") refreshCollections().catch(e=>toast('Error',e.message,'error'));
  if (page === "browser") refreshBrowser().catch(e=>toast('Error',e.message,'error'));
  if (page === "vault") refreshVault().catch(e=>toast('Error',e.message,'error'));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function loadSettings() {
  const data = await api("/api/settings");
  state.settings = data.settings;
  await window.VideoFlowI18n.setLanguage(state.settings.language, false);
  $('#settingsLanguage').value = state.settings.language;
  initAppearance();
  initStudio();
  state.destinationFolder = folderForSource();
  $("#folderPath").value = state.destinationFolder;
  syncFolderSettings();
  $("#settingsFormat").value = state.settings.default_format;
  $("#settingsVideoQuality").value = state.settings.default_video_quality;
  $("#settingsAudioQuality").value = state.settings.default_audio_quality;
  $("#settingsConcurrent").value = state.settings.max_concurrent;
  $('#settingsRemovedRetention').value = state.settings.removed_retention_days;
  syncRemovedRetention();
  $("#concurrentValue").textContent = state.settings.max_concurrent;
  $("#settingsNotifications").checked = Boolean(state.settings.notifications);
  if (!state.settings.welcome_seen) {
    $("#welcomeScreen").classList.remove("hidden");
    $("#welcomeScreen").setAttribute("aria-hidden", "false");
  }
}

async function loadSystem() {
  try {
    const data = await api("/api/system");
    const ready = data.ffmpeg && data.ffprobe;
    const card = $("#systemCard");
    card.querySelector(".status-dot").className = `status-dot ${ready ? "" : "bad"}`;
    card.querySelector("strong").textContent = ready ? "Sistema listo" : "Falta FFmpeg";
    card.querySelector("p").textContent = ready
      ? `yt-dlp ${data.yt_dlp} · ${data.deno ? "Deno disponible" : "Deno no detectado"}`
      : "Ejecuta INSTALAR.bat para habilitar conversiones.";
    if (!ready) toast("Dependencia pendiente", "FFmpeg no está disponible. Ejecuta INSTALAR.bat.", "error", 7000);
  } catch (error) {
    $("#connectionStatus").innerHTML = "<i></i> Sin conexión";
    toast("No se pudo conectar", error.message, "error");
  }
}

function getCurrentQualityOption() {
  const select = $("#qualitySelect");
  return select.options[select.selectedIndex];
}

function rebuildQualityOptions() {
  if (!state.video) return;
  const format = $("#formatSelect").value;
  const mode = $("#modeSelect").value;
  let options = mode === "audio" ? state.video.audio_options : state.video.video_options;
  if (mode === "audio" && !['mp3', 'ogg'].includes(format)) {
    options = [{ value: "0", label: "Calidad original", estimated_size: state.video.source_audio_size || 0, estimated_size_human: "—" }];
  }
  if (format === "vob") options = options.filter((item) => Number(item.value) <= 480);
  const select = $("#qualitySelect");
  select.innerHTML = options
    .map((item) => `<option value="${item.value}" data-size="${item.estimated_size || 0}">${escapeHtml(item.label)} · ${escapeHtml(item.estimated_size_human || "—")}</option>`)
    .join("");

  const preferred = mode === "audio" && !['mp3', 'ogg'].includes(format) ? "0" : mode === "audio"
    ? state.settings.default_audio_quality
    : format === "vob"
      ? String(Math.min(480, Number(state.settings.default_video_quality)))
      : state.settings.default_video_quality;
  if ([...select.options].some((option) => option.value === preferred)) select.value = preferred;
  else if (select.options.length) select.selectedIndex = Math.max(0, select.options.length - 1);

  $("#finalExtension").textContent = `.${format}`;
  $("#vobNotice").classList.toggle("hidden", format !== "vob");
  syncAudioTrackMode();
  if (state.savePath && !state.savePath.toLowerCase().endsWith(`.${format}`)) {
    state.savePath = "";
    state.overwrite = false;
    $("#folderPath").value = state.destinationFolder;
    $("#destinationHint").textContent = "Cambió el formato. Elige «Guardar como» otra vez para fijar nombre y ubicación.";
  }
  updateEstimate();
}

function rebuildFormatOptions() {
  const mode = $("#modeSelect").value;
  const select = $("#formatSelect");
  const previous = select.value;
  const source = state.video?.source;
  const hasVobQuality = state.video?.video_options.some(({value}) => Number(value) <= 480);
  const hideVob = source === "TikTok" || (["Reddit", "Instagram", "X", "Twitch"].includes(source) && !hasVobQuality);
  const choices = hideVob
    ? formatChoices[mode].filter(([value]) => value !== "vob")
    : formatChoices[mode];
  select.innerHTML = choices
    .map(([value, label]) => `<option value="${value}">${label}</option>`).join("");
  if (choices.some(([value]) => value === previous)) select.value = previous;
  else if (choices.some(([value]) => value === state.settings.default_format)) select.value = state.settings.default_format;
  rebuildQualityOptions();
}

function updateEstimate() {
  const option = getCurrentQualityOption();
  const track = selectedAudioTrack();
  if (track && Number(track.estimated_size) > 0 && $('#modeSelect').value === 'audio'
      && !['mp3', 'ogg', 'wav', 'flac'].includes($('#formatSelect').value)) {
    $('#estimatedSize').textContent = compressionBytes(Number(track.estimated_size));
    return;
  }
  $("#estimatedSize").textContent = option
    ? option.textContent.split("·").slice(-1)[0].trim()
    : "—";
}

function showVideo(video, previous = {}) {
  state.video = video;
  selectSource(video.source.toLowerCase());
  $("#videoThumbnail").src = video.thumbnail || "/static/logo.svg";
  $("#videoTitle").textContent = video.title;
  $("#videoUploader").textContent = video.view_count
    ? `${video.source} · ${video.uploader} · ${formatNumber(video.view_count)} visualizaciones`
    : `${video.source} · ${video.uploader}`;
  $("#videoDuration").textContent = video.duration_human;
  const preferredFormat = previous.format || state.settings.default_format;
  $("#modeSelect").value = formatChoices.audio.some(([value]) => value === preferredFormat)
    ? "audio" : previous.mode === "video_only" ? "video_only" : "video_audio";
  state.destinationFolder = previous.folder || folderForSource(video.source);
  state.savePath = "";
  state.overwrite = false;
  renderAudioTracks(previous.audio_track || '');
  $("#folderPath").value = state.destinationFolder;
  $("#destinationHint").textContent = previous.folder
    ? "Carpeta recuperada del historial. Se usará un nombre automático para esta nueva descarga."
    : `Se guardará en la carpeta de ${video.source}. Usa «Guardar como» para cambiar nombre y ubicación.`;
  rebuildFormatOptions();
  if ([...$("#formatSelect").options].some((option) => option.value === preferredFormat)) {
    $("#formatSelect").value = preferredFormat;
    rebuildQualityOptions();
  }
  if (previous.quality !== undefined && [...$("#qualitySelect").options].some((option) => option.value === String(previous.quality))) {
    $("#qualitySelect").value = String(previous.quality);
    updateEstimate();
  }
  if (previous.audio_track && !selectedAudioTrack()) {
    $('#audioTrackStatus').textContent = 'La pista guardada en el historial ya no aparece disponible. Revisa las pistas antes de descargar.';
  }
  $("#videoResult").classList.remove("hidden");
  $("#videoResult").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function analyzeVideo() {
  const url = $("#videoUrl").value.trim();
  if (url.split(/\s+/).length > 1) { toast("Varios enlaces", "Elige las opciones de Descargar varios enlaces y pulsa Añadir enlaces a la cola."); return; }
  if (!url) {
    toast("Falta el enlace", "Pega un enlace de video para continuar.", "error");
    $("#videoUrl").focus();
    return;
  }
  const source = sourceForLink(url);
  if (source && source !== state.source) {
    platformDrafts[source] = url;
    selectSource(source);
  }
  const button = $("#analyzeButton");
  button.classList.add("loading");
  button.disabled = true;
  setDownloadSessionBusy(true);
  $('#batchStart').disabled = true;
  $('#videoUrl').readOnly = true;
  $('#pasteButton').disabled = true;
  $$('.source-tab').forEach(tab => tab.disabled = true);
  analysisFeedback('Analizando video…');
  state.video = null;
  $('#videoResult').classList.add('hidden');
  try {
    const data = await api("/api/analyze", {
      method: "POST",
      body: JSON.stringify({ url, browser: browserForSource() }),
    });
    showVideo(data.video);
    toast("Video analizado", "Ya puedes elegir el formato, la calidad y dónde guardarlo.", "success");
  } catch (error) {
    analysisFeedback(error.message, true);
    toast("No se pudo analizar", error.message, "error", 6500);
  } finally {
    button.classList.remove("loading");
    button.disabled = false;
    setDownloadSessionBusy(false);
    $('#batchStart').disabled = false;
    $('#videoUrl').readOnly = false;
    $('#pasteButton').disabled = false;
    $$('.source-tab').forEach(tab => tab.disabled = false);
  }
}

async function pickFolder(targetInput) {
  const input = $(targetInput);
  try {
    const data = await api("/api/select-folder", {
      method: "POST",
      body: JSON.stringify({ initial: input.value || folderForSource() }),
    });
    if (!data.cancelled && data.path) {
      input.value = data.path;
      input.title = data.path;
      return data.path;
    }
  } catch (error) {
    toast("No se pudo abrir la carpeta", error.message, "error");
  }
}

async function pickSavePath() {
  if (!state.video) return;
  const video = state.video;
  const button = $("#browseFolderButton");
  button.disabled = true;
  try {
    const data = await api("/api/save-path", {
      method: "POST",
      body: JSON.stringify({
        initial: state.destinationFolder || folderForSource(video.source),
        source: video.source,
        title: video.title,
        format: $("#formatSelect").value,
      }),
    });
    if (data.cancelled) return;
    rememberFolder(data.source || video.source, data.folder);
    if (state.video !== video) return;
    state.savePath = data.path;
    state.destinationFolder = data.folder;
    state.overwrite = Boolean(data.overwrite);
    $("#folderPath").value = data.path;
    $("#destinationHint").textContent = state.overwrite
      ? "El archivo existente se reemplazará al terminar la descarga."
      : "El archivo se guardará exactamente con este nombre y en esta ubicación.";
  } catch (error) {
    toast("No se pudo elegir el archivo", error.message, "error");
  } finally {
    button.disabled = false;
  }
}

async function addToQueue() {
  if (!state.video) return;
  const format = $("#formatSelect").value;
  const mode = $("#modeSelect").value;
  const quality = $("#qualitySelect").value;
  const folder = state.destinationFolder;
  const option = getCurrentQualityOption();
  const estimatedSize = Number(option?.dataset.size || 0);
  if (!folder) {
    toast("Falta la carpeta", "Selecciona una ruta de destino.", "error");
    return;
  }
  const button = $("#addQueueButton");
  button.disabled = true;
  try {
    const data = await api("/api/downloads", {
      method: "POST",
      body: JSON.stringify({
        url: state.video.url,
        original_url: state.video.original_url || state.video.url,
        video_id: state.video.id,
        title: state.video.title,
        thumbnail: state.video.thumbnail,
        duration: state.video.duration,
        format,
        mode,
        browser: state.video.browser || '',
        quality,
        folder,
        save_path: state.savePath,
        overwrite: state.overwrite,
        estimated_size: estimatedSize,
        advanced: {...advancedOptions(), ...audioTrackRequest()},
      }),
    });
    rememberFolder(data.download.source, data.download.folder);
    toast("Añadido a la cola", `${state.video.title} ${window.VideoFlowI18n.t('comenzará según el límite configurado.')}`, "success", 4300, true);
    $("#videoResult").classList.add("hidden");
    $("#videoUrl").value = "";
    state.video = null;
    await loadDownloads();
    navigate("downloads");
  } catch (error) {
    toast("No se pudo agregar", error.message, "error");
  } finally {
    button.disabled = false;
  }
}

function statusClass(status) {
  const value = status.toLowerCase();
  if (value === "completado") return "completed";
  if (value === "error") return "error";
  if (value === "cancelado") return "cancelled";
  if (value === "pausado") return "paused";
  if (value === "pendiente") return "pending";
  if (value === "procesando") return "processing";
  return "";
}

function actionButtons(task) {
  const buttons = [];
  if (task.status === "Descargando") {
    buttons.push(`<button class="action-button" data-action="pause" data-id="${task.id}" title="Pausar">Ⅱ</button>`);
    buttons.push(`<button class="action-button danger" data-action="cancel" data-id="${task.id}" title="Cancelar">×</button>`);
  } else if (task.status === "Procesando") {
    buttons.push(`<button class="action-button danger" data-action="cancel" data-id="${task.id}" title="Cancelar">×</button>`);
  } else if (task.status === "Pausado") {
    buttons.push(`<button class="action-button" data-action="resume" data-id="${task.id}" title="Reanudar">▶</button>`);
    buttons.push(`<button class="action-button danger" data-action="cancel" data-id="${task.id}" title="Cancelar">×</button>`);
  } else if (task.status === "Pendiente") {
    buttons.push(`<button class="action-button danger" data-action="cancel" data-id="${task.id}" title="Cancelar">×</button>`);
  } else if (task.status === "Completado") {
    buttons.push(`<button class="action-button" data-action="open" data-path="${escapeHtml(task.final_path)}" title="Mostrar archivo">⌂</button>`);
    buttons.push(`<button class="action-button danger" data-action="delete" data-id="${task.id}" title="Quitar de la lista">⌫</button>`);
  } else {
    if (task.can_retry) buttons.push(`<button class="action-button retry-button" data-action="retry" data-id="${task.id}" title="Reintentar descarga" aria-label="Reintentar descarga">↻</button>`);
    buttons.push(`<button class="action-button danger" data-action="delete" data-id="${task.id}" title="Quitar de la lista">⌫</button>`);
  }
  return buttons.join("");
}

function renderDownloads() {
  renderSeparationJobs();
  const list = $("#downloadList");
  const empty = $("#emptyDownloads");
  empty.classList.toggle("hidden", state.downloads.length > 0);
  list.classList.toggle("hidden", state.downloads.length === 0);

  list.innerHTML = state.downloads.map((task) => {
    const total = task.total_human !== "—" ? task.total_human : task.estimated_size_human;
    const detail = task.status === "Descargando"
      ? task.phase || `${task.speed_human} · ${task.eta_human} restantes`
      : task.status === "Completado"
        ? `${task.final_size_human} · ${task.phase || "Guardado correctamente"}${task.incognito ? " · Incógnito" : ""}`
        : task.status === "Procesando"
          ? task.phase || "FFmpeg está preparando el archivo final"
          : task.status;
    return `
      <article class="download-card">
        <img class="download-thumb" src="${escapeHtml(task.thumbnail || "/static/logo.svg")}" alt="">
        <div class="download-info">
          <div class="download-title-row">
            <h4 translate="no" title="${escapeHtml(task.title)}">${escapeHtml(task.title)}</h4>
            <span class="status-chip ${statusClass(task.status)}">${escapeHtml(task.status)}</span>
          </div>
          <div class="download-submeta">
            <span>${escapeHtml(task.source || "YouTube")}</span>
            <span>${escapeHtml(task.format.toUpperCase())}</span>
            <span>${escapeHtml(task.mode.startsWith('separate_') ? 'Separación de audio' : task.mode === 'video_compress' ? 'Video comprimido' : task.mode === 'video_convert' ? 'Video convertido' : task.mode === "video_only" ? "Solo video" : task.mode === "audio" ? "Solo audio" : "Video + audio")}</span>
            ${task.audio_track_label ? `<span><span>Audio:</span> <span translate="no">${escapeHtml(task.audio_track_label)}</span></span>` : ''}
            <span>${escapeHtml(task.mode === 'video_convert' ? ({'18':'Calidad muy alta','20':'Calidad alta','23':'Calidad equilibrada'}[task.quality] || 'Calidad alta') : qualityLabel(task.format, task.quality, task.source, task.mode))}</span>
            ${['video_convert', 'video_compress'].includes(task.mode) ? '' : `<span>${escapeHtml(task.downloaded_human)} / ${escapeHtml(total)}</span>`}
            <span>${escapeHtml(detail)}</span>
          </div>
          <div class="progress-row">
            <div class="progress-track"><i style="width:${Math.max(0, Math.min(100, task.progress))}%"></i></div>
            <span class="progress-percent">${Math.round(task.progress)}%</span>
          </div>
          ${task.error ? `<div class="error-message">${escapeHtml(task.error)}</div>` : ""}
        </div>
        <div class="download-actions">${actionButtons(task)}</div>
      </article>
    `;
  }).join("");

  const unfinished = state.downloads.filter((item) => !["Completado", "Error", "Cancelado"].includes(item.status));
  const queued = state.downloads.filter((item) => item.status === "Pendiente").length;
  const active = state.downloads.filter((item) => ["Descargando", "Procesando", "Pausado"].includes(item.status)).length;
  const completed = state.downloads.filter((item) => item.status === "Completado").length;
  const relevant = state.downloads.filter((item) => !["Error", "Cancelado"].includes(item.status));
  const average = relevant.length ? relevant.reduce((sum, item) => sum + Number(item.progress || 0), 0) / relevant.length : 0;

  $("#slotsAvailable").textContent = "∞";
  $("#statQueued").textContent = queued;
  $("#statActive").textContent = active;
  $("#statCompleted").textContent = completed;
  $("#generalProgressText").textContent = `${Math.round(average)}%`;
  $("#generalProgressBar").style.width = `${average}%`;
  $("#downloadCountBadge").textContent = unfinished.length;
  $("#downloadCountBadge").classList.toggle("hidden", unfinished.length === 0);
}

function handleDownloadNotifications(downloads) {
  let galleryChanged = false;
  for (const task of downloads) {
    const previous = state.previousStatuses.get(task.id);
    if (task.status === 'Completado' && previous !== task.status && !task.incognito &&
        platformNames[task.source.toLowerCase()] && ['video_audio', 'video_only'].includes(task.mode)) {
      galleryChanged = true;
    }
    if (previous && previous !== task.status) {
      if (task.status === "Completado") {
        const label = task.mode.startsWith('separate_') ? 'Separación completada' : task.mode === 'video_compress' ? 'Video comprimido' : task.mode === 'video_convert' ? 'Video convertido' : 'Descarga completada';
        toast(label, task.title, "success", 4300, true);
        browserNotification(label, task.title);
        loadHistory();
      } else if (task.status === "Error") {
        const label = task.mode.startsWith('separate_') ? 'Error en la separación' : task.mode === 'video_compress' ? 'Error al comprimir video' : task.mode === 'video_convert' ? 'Error al convertir video' : 'Error en la descarga';
        toast(label, task.error || task.title, "error", 6500, !task.error, false);
        browserNotification(label, task.title);
      }
    }
    state.previousStatuses.set(task.id, task.status);
  }
  if (galleryChanged && state.currentPage === 'gallery') loadGallery();
}

function browserNotification(title, body) {
  if (!state.settings?.notifications || !("Notification" in window)) return;
  if (Notification.permission === "granted") new Notification(window.VideoFlowI18n.t(title), { body });
}

async function loadDownloads() {
  try {
    const data = await api("/api/downloads");
    handleDownloadNotifications(data.downloads);
    state.downloads = data.downloads;
    renderDownloads();
  } catch (error) {
    console.error(error);
  }
}

function syncRemovedRetention() {
  $('#removedRetentionHint').textContent = `Los registros que quites de la lista se guardan aquí durante ${state.settings.removed_retention_days} días. Puedes restaurarlos a Descargas. Los archivos y el historial permanecen intactos.`;
}

function setRemovedDownloadsBusy(busy) {
  state.removedDownloadsBusy = busy;
  if (busy) {
    state.removedDownloadsRequest++;
    $('#removedDownloadList').querySelectorAll('button').forEach(control => { control.disabled = true; });
  }
  $('#restoreAllRemovedDownloads').disabled = true;
  $('#clearRemovedDownloads').disabled = true;
  $('#refreshRemovedDownloads').disabled = busy;
}

async function loadRemovedDownloads() {
  if (state.removedDownloadsBusy) return;
  const requestId = ++state.removedDownloadsRequest;
  const status = $('#removedDownloadsStatus'), list = $('#removedDownloadList');
  try {
    const data = await api('/api/removed-downloads');
    if (state.removedDownloadsBusy || requestId !== state.removedDownloadsRequest) return;
    state.settings.removed_retention_days = data.retention_days;
    syncRemovedRetention();
    $('#restoreAllRemovedDownloads').disabled = data.downloads.length === 0;
    $('#clearRemovedDownloads').disabled = data.downloads.length === 0;
    list.replaceChildren();
    status.textContent = data.downloads.length ? '' : 'No hay descargas retiradas temporalmente.';
    for (const task of data.downloads) {
      const card = document.createElement('article'); card.className = 'removed-download-card';
      const info = document.createElement('div');
      const title = document.createElement('strong'); title.setAttribute('translate','no'); title.textContent = task.title;
      const detail = document.createElement('p'); detail.className = 'field-hint';
      detail.textContent = `${task.source} · ${task.format.toUpperCase()} · ${task.status}`;
      const expiry = document.createElement('p'); expiry.className = 'field-hint';
      expiry.textContent = `Disponible hasta: ${new Date(task.expires_at*1000).toLocaleDateString(window.VideoFlowI18n.locale)}`;
      const path = document.createElement('small'); path.setAttribute('translate','no');path.textContent = task.final_path || task.folder;
      info.append(title,detail,expiry,path);
      const actions = document.createElement('div');actions.className = 'removed-download-actions';
      const restore = document.createElement('button');restore.type='button';restore.className='secondary-button';restore.textContent='Restaurar a Descargas';
      restore.onclick=async()=>{
        restore.disabled=true;
        try {
          const data=await api(`/api/removed-downloads/${task.id}/restore`,{method:'POST',body:'{}'});
          state.previousStatuses.set(data.download.id,data.download.status);
          await loadDownloads();await loadRemovedDownloads();
          toast('Registro restaurado','La descarga volvió a la lista sin descargar el archivo de nuevo.','success');
        } catch(error){restore.disabled=false;toast('No se pudo restaurar',error.message,'error');}
      };
      actions.append(restore);
      if(task.final_path){
        const show=document.createElement('button');show.type='button';show.className='secondary-button';show.textContent='Mostrar archivo';show.onclick=()=>openPath(task.final_path);actions.append(show);
      }
      const forget=document.createElement('button');forget.type='button';forget.className='text-button';forget.textContent='Quitar registro temporal';
      forget.onclick=async()=>{
        if(!await confirmAction('Quitar registro temporal','Se quitará este registro temporal. El archivo y el historial se conservarán.'))return;
        forget.disabled=true;
        try {await api(`/api/removed-downloads/${task.id}`,{method:'DELETE'});await loadRemovedDownloads();}
        catch(error){forget.disabled=false;toast('No se pudo eliminar',error.message,'error');}
      };
      actions.append(forget);card.append(info,actions);list.append(card);
    }
  } catch(error){
    if (!state.removedDownloadsBusy && requestId === state.removedDownloadsRequest) {
      status.textContent=error.message;
      $('#restoreAllRemovedDownloads').disabled=true;
      $('#clearRemovedDownloads').disabled=true;
    }
  }
}

async function restoreAllRemovedDownloads() {
  const button = $('#restoreAllRemovedDownloads');
  if (state.removedDownloadsBusy || button.disabled) return;
  setRemovedDownloadsBusy(true);
  button.textContent = 'Restaurando…';
  button.setAttribute('aria-busy', 'true');
  $('#removedDownloadsStatus').textContent = 'Restaurando las descargas retiradas…';
  try {
    const data = await api('/api/removed-downloads/restore-all', {method:'POST', body:'{}'});
    for (const task of data.restored) state.previousStatuses.set(task.id, task.status);
    await loadDownloads();
    if (data.skipped_count) {
      toast('Restauración completada', `Se restauraron ${data.restored_count} descargas sin volver a descargarlas. No se pudieron restaurar ${data.skipped_count} registros.`, 'info');
    } else if (data.restored_count) {
      toast('Descargas restauradas', `Se restauraron ${data.restored_count} descargas sin volver a descargar los archivos.`, 'success');
    } else {
      toast('Retiradas temporalmente', 'No hay descargas retiradas para restaurar.', 'info');
    }
  } catch(error) {
    toast('No se pudo restaurar', error.message, 'error');
  } finally {
    setRemovedDownloadsBusy(false);
    button.textContent = 'Restaurar todas';
    button.removeAttribute('aria-busy');
    await loadRemovedDownloads();
  }
}

async function clearRemovedDownloads() {
  const button = $('#clearRemovedDownloads');
  if (state.removedDownloadsBusy || button.disabled) return;
  setRemovedDownloadsBusy(true);
  try {
    const accepted = await confirmAction('Vaciar retiradas temporalmente', 'Se quitarán todos los registros de Retiradas temporalmente y no podrán restaurarse desde este apartado. Los archivos descargados y el historial se conservarán. ¿Deseas continuar?');
    if (!accepted) return;
    button.textContent = 'Vaciando…';
    button.setAttribute('aria-busy', 'true');
    $('#removedDownloadsStatus').textContent = 'Vaciando los registros temporales…';
    const data = await api('/api/removed-downloads', {method:'DELETE', body:JSON.stringify({confirmed:true})});
    toast('Retiradas vaciadas', `Se quitaron ${data.cleared_count} registros temporales. Los archivos y el historial se conservaron.`, 'success');
  } catch(error) {
    toast('No se pudo vaciar', error.message, 'error');
  } finally {
    setRemovedDownloadsBusy(false);
    button.textContent = 'Vaciar retiradas';
    button.removeAttribute('aria-busy');
    await loadRemovedDownloads();
  }
}

async function downloadAction(action, id) {
  try {
    if (action === "cancel") {
      const accepted = await confirmAction("Cancelar descarga", "Se detendrá el trabajo y se eliminarán los archivos temporales.");
      if (!accepted) return;
    }
    await api(`/api/downloads/${id}/${action}`, { method: "POST", body: "{}" });
    if (action === 'retry') toast('Descarga en cola', 'Se volverá a conectar con el formato y la pista de audio elegidos.');
    await loadDownloads();
  } catch (error) {
    toast("No se pudo completar la acción", error.message, "error");
  }
}

async function deleteDownload(id) {
  try {
    await api(`/api/downloads/${id}`, { method: "DELETE" });
    await loadDownloads();
    await loadRemovedDownloads();
    toast('Descarga retirada',`Puedes recuperarla en Retiradas temporalmente durante ${state.settings.removed_retention_days} días.`,'success');
  } catch (error) {
    toast("No se pudo eliminar", error.message, "error");
  }
}

async function openPath(path) {
  try {
    await api("/api/open-path", { method: "POST", body: JSON.stringify({ path }) });
  } catch (error) {
    toast("No se pudo abrir la ruta", error.message, "error");
  }
}

async function loadHistory() {
  try {
    const data = await api("/api/history");
    state.history = data.history;
    renderHistory();
    if (typeof filterHistory === "function") filterHistory();
  } catch (error) {
    toast("No se pudo cargar el historial", error.message, "error");
  }
}

function historyUrlCell(url = "") {
  if (!/^https?:\/\//i.test(url)) return '<span class="history-url-missing">Enlace no registrado</span>';
  const escaped = escapeHtml(url);
  return `<div class="history-url"><a href="${escaped}" target="_blank" rel="noopener noreferrer" title="${escaped}">${escaped}</a><button class="text-button" type="button" data-copy-url="${escaped}" aria-label="Copiar enlace del video">Copiar</button></div>`;
}

async function copyHistoryUrl(url) {
  try {
    await navigator.clipboard.writeText(url);
    toast("Enlace copiado", "La URL del video está en el portapapeles.", "success");
  } catch {
    toast("No se pudo copiar", "Puedes abrir el enlace y copiarlo desde la barra del navegador.", "error");
  }
}

async function redownloadFromHistory(id, button) {
  const item = state.history.find((entry) => String(entry.id) === String(id));
  if (!item || !/^https?:\/\//i.test(item.url || "")) return;
  button.disabled = true;
  button.textContent = "Analizando…";
  try {
    const data = await api("/api/analyze", {
      method: "POST",
      body: JSON.stringify({ url: item.url, browser: browserForSource(item.source || 'YouTube') }),
    });
    navigate("home");
    $("#videoUrl").value = item.url;
    showVideo(data.video, item);
    toast("Listo para volver a descargar", "Se recuperó el destino anterior. Revisa las opciones y agrega el video a la cola.", "success");
  } catch (error) {
    toast("No se pudo recuperar el video", error.message, "error");
  } finally {
    button.disabled = false;
    button.textContent = "↻ Volver a descargar";
  }
}

function renderHistory() {
  const body = $("#historyBody");
  const empty = $("#emptyHistory");
  const table = $(".table-wrap");
  empty.classList.toggle("hidden", state.history.length > 0);
  table.classList.toggle("hidden", state.history.length === 0);
  body.innerHTML = state.history.map((item) => `
    <tr>
      <td>
        <div class="history-video">
          <img src="${escapeHtml(item.thumbnail || "/static/logo.svg")}" alt="">
          <div><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.source || "YouTube")} · ${escapeHtml(item.duration_human)}</small>${item.audio_track_label ? `<small><span>Audio:</span> <span translate="no">${escapeHtml(item.audio_track_label)}</span></small>` : ''}<button class="secondary-button history-redownload" type="button" data-redownload-id="${item.id}" ${/^https?:\/\//i.test(item.url || "") ? "" : 'disabled title="Este registro no tiene un enlace guardado"'}>↻ Volver a descargar</button></div>
        </div>
      </td>
      <td>${escapeHtml(formatDate(item.downloaded_at))}</td>
      <td><span class="format-tag">${escapeHtml(item.format)}</span></td>
      <td>${escapeHtml(item.mode === 'video_convert' ? ({'18':'Calidad muy alta','20':'Calidad alta','23':'Calidad equilibrada'}[item.quality] || 'Calidad alta') : qualityLabel(item.format, item.quality, item.source, item.mode))}</td>
      <td>${escapeHtml(item.size_human)}</td>
      <td>${historyUrlCell(item.url)}</td>
      <td><button class="path-button" data-open-path="${escapeHtml(item.filepath)}" title="${escapeHtml(item.filepath)}">${escapeHtml(item.filepath)}</button></td>
    </tr>
  `).join("");
}

async function saveSettings() {
  const payload = {
    platform_folders: Object.fromEntries(Object.keys(platformNames).map((source) => [source, $(`#settingsFolder-${source}`).value])),
    default_format: $("#settingsFormat").value,
    default_video_quality: $("#settingsVideoQuality").value,
    default_audio_quality: $("#settingsAudioQuality").value,
    max_concurrent: Number($("#settingsConcurrent").value),
    removed_retention_days: Number($('#settingsRemovedRetention').value),
    background_mode: $("#settingsBackground").checked, keep_awake: $("#settingsAwake").checked,
    rate_limit_kbps: Number($("#settingsRate").value),
    retry_count: Number($("#settingsRetries").value),
    youtube_connection: $('#settingsYouTubeConnection').value,
    notifications: $("#settingsNotifications").checked,
  };
  try {
    if (payload.notifications && "Notification" in window && Notification.permission === "default") {
      await Notification.requestPermission();
    }
    const data = await api("/api/settings", { method: "PUT", body: JSON.stringify(payload) });
    state.settings = data.settings;
    state.destinationFolder = folderForSource();
    state.savePath = "";
    state.overwrite = false;
    $("#folderPath").value = state.destinationFolder;
    syncFolderSettings();
    syncBatchDestination();
    syncVideoConvertConcurrency();
    syncCompressionConcurrency();
    syncRemovedRetention();
    if ($('#removedDownloads').open) await loadRemovedDownloads();
    toast("Configuración guardada", "Los cambios se aplicaron correctamente.", "success");
  } catch (error) {
    toast("No se pudo guardar", error.message, "error");
  }
}

async function saveInterfaceLanguage() {
  const selector = $('#settingsLanguage'), previous = state.settings.language;
  selector.disabled = true;
  $('#languageStatus').textContent = 'Guardando idioma…';
  try {
    const data = await api('/api/settings', {method:'PUT', body:JSON.stringify({language:selector.value})});
    state.settings.language = data.settings.language;
    await window.VideoFlowI18n.setLanguage(data.settings.language);
    $('#languageStatus').textContent = 'Idioma guardado. Se usará también la próxima vez que abras la aplicación.';
    renderHistory();
  } catch (error) {
    selector.value = previous;
    $('#languageStatus').textContent = 'No se pudo guardar el idioma. Vuelve a intentarlo.';
    toast('No se pudo guardar', error.message, 'error');
  } finally { selector.disabled = false; }
}

function bindEvents() {
  $('#removedDownloads').addEventListener('toggle',()=>{if($('#removedDownloads').open)loadRemovedDownloads();});
  $('#restoreAllRemovedDownloads').addEventListener('click',restoreAllRemovedDownloads);
  $('#clearRemovedDownloads').addEventListener('click',clearRemovedDownloads);
  $('#refreshRemovedDownloads').addEventListener('click',loadRemovedDownloads);
  $('#settingsLanguage').addEventListener('change', saveInterfaceLanguage);
  document.addEventListener('videoflow:language', event => { if (state.settings) state.settings.language = event.detail.language; });
  $$(".nav-item").forEach((button) => button.addEventListener("click", () => navigate(button.dataset.page)));
  $$(".source-tab").forEach((button) => button.addEventListener("click", () => {
    platformDrafts[state.source] = $("#videoUrl").value;
    selectSource(button.dataset.source);
    state.video = null;
    $("#videoUrl").value = platformDrafts[state.source] || "";
    syncBatchDestination();
    $("#videoResult").classList.add("hidden");
  }));
  $("#newDownloadButton").addEventListener("click", () => navigate("home"));
  $("#analyzeButton").addEventListener("click", analyzeVideo);
  $("#videoUrl").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && event.ctrlKey) { event.preventDefault(); analyzeVideo(); }
  });
  $("#pasteButton").addEventListener("click", async () => {
    try {
      $("#videoUrl").value = await navigator.clipboard.readText();
      $("#videoUrl").focus();
    } catch {
      toast("Portapapeles bloqueado", "Pega el enlace manualmente con Ctrl + V.", "error");
    }
  });
  $("#modeSelect").addEventListener("change", rebuildFormatOptions);
  $("#formatSelect").addEventListener("change", rebuildQualityOptions);
  $("#qualitySelect").addEventListener("change", updateEstimate);
  $("#browseFolderButton").addEventListener("click", pickSavePath);
  $$("[data-settings-source]").forEach((button) => button.addEventListener("click", () => pickFolder(`#settingsFolder-${button.dataset.settingsSource}`)));
  $("#addQueueButton").addEventListener("click", addToQueue);
  $("#clearVideoButton").addEventListener("click", () => {
    state.video = null;
    $("#videoResult").classList.add("hidden");
  });
  $("#startButton").addEventListener("click", async () => {
    $("#welcomeScreen").classList.add("hidden");
    $("#welcomeScreen").setAttribute("aria-hidden", "true");
    state.settings.welcome_seen = true;
    await api("/api/settings", { method: "PUT", body: JSON.stringify({ welcome_seen: true }) });
  });
  $("#themeToggle").addEventListener("click", cycleAppearanceMode);
  $("#openAppearance").addEventListener("click", () => navigate("appearance"));
  $("#settingsConcurrent").addEventListener("input", (event) => {
    $("#concurrentValue").textContent = event.target.value;
  });
  $("#saveSettingsButton").addEventListener("click", saveSettings);
  $("#clearHistoryButton").addEventListener("click", async () => {
    const accepted = await confirmAction("Limpiar historial", "Se borrarán los registros y enlaces del historial. Los archivos descargados permanecerán en tu computadora.");
    if (!accepted) return;
    try {
      await api("/api/history", { method: "DELETE" });
      await loadHistory();
      toast("Historial limpio", "Los archivos guardados permanecen intactos.", "success");
    } catch (error) {
      toast("No se pudo limpiar", error.message, "error");
    }
  });
  $("#confirmCancel").addEventListener("click", () => closeConfirm(false));
  $("#confirmAccept").addEventListener("click", () => closeConfirm(true));
  $("#confirmModal").addEventListener("click", (event) => {
    if (event.target.id === "confirmModal") closeConfirm(false);
  });

  $("#downloadList").addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const { action, id, path } = button.dataset;
    if (["pause", "resume", "cancel", "retry"].includes(action)) {
      button.disabled = true;
      downloadAction(action, id).finally(() => { if (button.isConnected) button.disabled = false; });
    }
    if (action === "delete") deleteDownload(id);
    if (action === "open") openPath(path);
  });

  $("#historyBody").addEventListener("click", (event) => {
    const button = event.target.closest("[data-open-path]");
    if (button) openPath(button.dataset.openPath);
    const copyButton = event.target.closest("[data-copy-url]");
    if (copyButton) copyHistoryUrl(copyButton.dataset.copyUrl);
    const repeatButton = event.target.closest("[data-redownload-id]");
    if (repeatButton) redownloadFromHistory(repeatButton.dataset.redownloadId, repeatButton);
  });
}

async function init() {
  bindEvents();
  try {
    await loadSettings();
    initExtensions();
    initSeparation();
    initVideoConversion();
    initVideoCompression();
    initAudioTracks();
    initYouTubeSession();
    await Promise.all([loadSystem(), loadDownloads(), loadHistory(), initWallpapers()]);
  } catch (error) {
    toast("Error de inicio", error.message, "error", 7000);
  }
  window.setInterval(loadDownloads, 1000);
}

document.addEventListener("DOMContentLoaded", init);
