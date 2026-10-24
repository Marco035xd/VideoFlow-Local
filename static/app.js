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
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const pageTitles = {
  home: "Nueva descarga",
  convert: "Video a audio",
  "video-convert": "Convertir video",
  separate: "Voz e instrumentos",
  downloads: "Gestión de descargas",
  history: "Historial",
  appearance: "Apariencia",
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
  return Number(value || 0).toLocaleString("es-PE");
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function qualityLabel(format, quality, source = "") {
  if (["wav", "flac"].includes(format)) return "Sin pérdida";
  if (format === "m4a") return source === "Local" ? `${quality} kbps` : "Original";
  if (format === "mp3") return `${quality} kbps`;
  if (String(quality) === "0") return "Mejor disponible";
  if (source === "TikTok") return `${quality} px de alto`;
  if (String(quality) === "1440") return "2K (1440p)";
  if (String(quality) === "2160") return "4K (2160p)";
  return `${quality}p`;
}

const formatChoices = {
  video_audio: [["mp4", "MP4"], ["mkv", "MKV"], ["webm", "WEBM"], ["vob", "VOB"]],
  video_only: [["mp4", "MP4"], ["mkv", "MKV"], ["webm", "WEBM"]],
  audio: [["mp3", "MP3"], ["m4a", "M4A"], ["wav", "WAV"]],
};

const platformNames = { youtube: "YouTube", facebook: "Facebook", tiktok: "TikTok" };

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
  $$(".source-tab").forEach((button) => button.classList.toggle("active", button.dataset.source === source));
  const facebook = source === "facebook";
  const tiktok = source === "tiktok";
  $("#urlLabel").textContent = `Enlaces de ${facebook ? "Facebook" : tiktok ? "TikTok" : "YouTube"}`;
  $("#videoUrl").placeholder = facebook
    ? "https://www.facebook.com/.../videos/..."
    : tiktok ? "https://www.tiktok.com/@usuario/video/..." : "https://www.youtube.com/watch?v=...";
  $("#sourceMark").src = `/static/icons/${facebook ? "facebook" : tiktok ? "tiktok" : "youtube"}.png`;
  $("#videoUrl").placeholder += "\nPega hasta 10 enlaces, uno por línea";
  $("#sourceHelp").textContent = 'Un enlace: Analizar video. Varios enlaces: elige las opciones de abajo y pulsa «Añadir enlaces a la cola».';
  $("#facebookNotice").classList.toggle("hidden", !facebook);
  state.destinationFolder = folderForSource(source);
  state.savePath = "";
  state.overwrite = false;
  $("#folderPath").value = state.destinationFolder;
  $("#destinationLabel").textContent = `Destino de la descarga · ${platformNames[source]}`;
  $("#destinationHint").textContent = `Se guardará en la carpeta de ${platformNames[source]}. Usa «Guardar como» para cambiar nombre y ubicación.`;
}

function toast(title, message, type = "info", timeout = 4300) {
  const item = document.createElement("div");
  item.className = `toast ${type}`;
  const icon = type === "success" ? "✓" : type === "error" ? "!" : "i";
  item.innerHTML = `
    <div class="toast-icon">${icon}</div>
    <div><strong>${escapeHtml(title)}</strong><p>${escapeHtml(message)}</p></div>
    <button class="toast-close" type="button" aria-label="Cerrar">×</button>
  `;
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
  if (page === "history") loadHistory();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function loadSettings() {
  const data = await api("/api/settings");
  state.settings = data.settings;
  initAppearance();
  state.destinationFolder = folderForSource();
  $("#folderPath").value = state.destinationFolder;
  syncFolderSettings();
  $("#settingsFormat").value = state.settings.default_format;
  $("#settingsVideoQuality").value = state.settings.default_video_quality;
  $("#settingsAudioQuality").value = state.settings.default_audio_quality;
  $("#settingsConcurrent").value = state.settings.max_concurrent;
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
  if (mode === "audio" && format !== "mp3") {
    options = [{ value: "0", label: "Calidad original", estimated_size: state.video.source_audio_size || 0, estimated_size_human: "—" }];
  }
  if (format === "vob") options = options.filter((item) => Number(item.value) <= 480);
  const select = $("#qualitySelect");
  select.innerHTML = options
    .map((item) => `<option value="${item.value}" data-size="${item.estimated_size || 0}">${escapeHtml(item.label)} · ${escapeHtml(item.estimated_size_human || "—")}</option>`)
    .join("");

  const preferred = mode === "audio" && format !== "mp3" ? "0" : mode === "audio"
    ? state.settings.default_audio_quality
    : format === "vob"
      ? String(Math.min(480, Number(state.settings.default_video_quality)))
      : state.settings.default_video_quality;
  if ([...select.options].some((option) => option.value === preferred)) select.value = preferred;
  else if (select.options.length) select.selectedIndex = Math.max(0, select.options.length - 1);

  $("#finalExtension").textContent = `.${format}`;
  $("#vobNotice").classList.toggle("hidden", format !== "vob");
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
  const choices = state.video?.source === "TikTok"
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
  $("#modeSelect").value = ["mp3", "m4a", "wav"].includes(preferredFormat)
    ? "audio" : previous.mode === "video_only" ? "video_only" : "video_audio";
  state.destinationFolder = previous.folder || folderForSource(video.source);
  state.savePath = "";
  state.overwrite = false;
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
  $("#videoResult").classList.remove("hidden");
  $("#videoResult").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function analyzeVideo() {
  const url = $("#videoUrl").value.trim();
  if (url.split(/\s+/).length > 1) { toast("Varios enlaces", "Elige las opciones de Descargar varios enlaces y pulsa Añadir enlaces a la cola."); return; }
  if (!url) {
    toast("Falta el enlace", "Pega una URL de YouTube, Facebook o TikTok para continuar.", "error");
    $("#videoUrl").focus();
    return;
  }
  const button = $("#analyzeButton");
  button.classList.add("loading");
  button.disabled = true;
  try {
    const data = await api("/api/analyze", {
      method: "POST",
      body: JSON.stringify({ url, browser: $("#facebookBrowser").value }),
    });
    showVideo(data.video);
    toast("Video analizado", "Ya puedes elegir el formato, la calidad y dónde guardarlo.", "success");
  } catch (error) {
    toast("No se pudo analizar", error.message, "error", 6500);
  } finally {
    button.classList.remove("loading");
    button.disabled = false;
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
        browser: state.video.source === "Facebook" ? $("#facebookBrowser").value : "",
        quality,
        folder,
        save_path: state.savePath,
        overwrite: state.overwrite,
        estimated_size: estimatedSize,
      }),
    });
    rememberFolder(data.download.source, data.download.folder);
    toast("Añadido a la cola", `${state.video.title} comenzará según el límite configurado.`, "success");
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
      ? `${task.speed_human} · ${task.eta_human} restantes`
      : task.status === "Completado"
        ? `${task.final_size_human} · Guardado correctamente`
        : task.status === "Procesando"
          ? task.phase || "FFmpeg está preparando el archivo final"
          : task.status;
    return `
      <article class="download-card">
        <img class="download-thumb" src="${escapeHtml(task.thumbnail || "/static/logo.svg")}" alt="">
        <div class="download-info">
          <div class="download-title-row">
            <h4 title="${escapeHtml(task.title)}">${escapeHtml(task.title)}</h4>
            <span class="status-chip ${statusClass(task.status)}">${escapeHtml(task.status)}</span>
          </div>
          <div class="download-submeta">
            <span>${escapeHtml(task.source || "YouTube")}</span>
            <span>${escapeHtml(task.format.toUpperCase())}</span>
            <span>${escapeHtml(task.mode.startsWith('separate_') ? 'Separación de audio' : task.mode === 'video_convert' ? 'Video convertido' : task.mode === "video_only" ? "Solo video" : task.mode === "audio" ? "Solo audio" : "Video + audio")}</span>
            <span>${escapeHtml(task.mode === 'video_convert' ? ({'18':'Calidad muy alta','20':'Calidad alta','23':'Calidad equilibrada'}[task.quality] || 'Calidad alta') : qualityLabel(task.format, task.quality, task.source))}</span>
            ${task.mode === 'video_convert' ? '' : `<span>${escapeHtml(task.downloaded_human)} / ${escapeHtml(total)}</span>`}
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

  $("#slotsAvailable").textContent = Math.max(0, 10 - unfinished.length);
  $("#statQueued").textContent = queued;
  $("#statActive").textContent = active;
  $("#statCompleted").textContent = completed;
  $("#generalProgressText").textContent = `${Math.round(average)}%`;
  $("#generalProgressBar").style.width = `${average}%`;
  $("#downloadCountBadge").textContent = unfinished.length;
  $("#downloadCountBadge").classList.toggle("hidden", unfinished.length === 0);
}

function handleDownloadNotifications(downloads) {
  for (const task of downloads) {
    const previous = state.previousStatuses.get(task.id);
    if (previous && previous !== task.status) {
      if (task.status === "Completado") {
        const label = task.mode.startsWith('separate_') ? 'Separación completada' : task.mode === 'video_convert' ? 'Video convertido' : 'Descarga completada';
        toast(label, task.title, "success");
        browserNotification(label, task.title);
        loadHistory();
      } else if (task.status === "Error") {
        const label = task.mode.startsWith('separate_') ? 'Error en la separación' : task.mode === 'video_convert' ? 'Error al convertir video' : 'Error en la descarga';
        toast(label, task.error || task.title, "error", 6500);
        browserNotification(label, task.title);
      }
    }
    state.previousStatuses.set(task.id, task.status);
  }
}

function browserNotification(title, body) {
  if (!state.settings?.notifications || !("Notification" in window)) return;
  if (Notification.permission === "granted") new Notification(title, { body });
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

async function downloadAction(action, id) {
  try {
    if (action === "cancel") {
      const accepted = await confirmAction("Cancelar descarga", "Se detendrá el trabajo y se eliminarán los archivos temporales.");
      if (!accepted) return;
    }
    await api(`/api/downloads/${id}/${action}`, { method: "POST", body: "{}" });
    await loadDownloads();
  } catch (error) {
    toast("No se pudo completar la acción", error.message, "error");
  }
}

async function deleteDownload(id) {
  try {
    await api(`/api/downloads/${id}`, { method: "DELETE" });
    await loadDownloads();
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
      body: JSON.stringify({ url: item.url, browser: $("#facebookBrowser").value }),
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
          <div><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.source || "YouTube")} · ${escapeHtml(item.duration_human)}</small><button class="secondary-button history-redownload" type="button" data-redownload-id="${item.id}" ${/^https?:\/\//i.test(item.url || "") ? "" : 'disabled title="Este registro no tiene un enlace guardado"'}>↻ Volver a descargar</button></div>
        </div>
      </td>
      <td>${escapeHtml(formatDate(item.downloaded_at))}</td>
      <td><span class="format-tag">${escapeHtml(item.format)}</span></td>
      <td>${escapeHtml(item.mode === 'video_convert' ? ({'18':'Calidad muy alta','20':'Calidad alta','23':'Calidad equilibrada'}[item.quality] || 'Calidad alta') : qualityLabel(item.format, item.quality, item.source))}</td>
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
    rate_limit_kbps: Number($("#settingsRate").value),
    retry_count: Number($("#settingsRetries").value),
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
    toast("Configuración guardada", "Los cambios se aplicaron correctamente.", "success");
  } catch (error) {
    toast("No se pudo guardar", error.message, "error");
  }
}

function bindEvents() {
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
    if (["pause", "resume", "cancel"].includes(action)) downloadAction(action, id);
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
    await Promise.all([loadSystem(), loadDownloads(), loadHistory()]);
  } catch (error) {
    toast("Error de inicio", error.message, "error", 7000);
  }
  window.setInterval(loadDownloads, 1000);
}

document.addEventListener("DOMContentLoaded", init);
