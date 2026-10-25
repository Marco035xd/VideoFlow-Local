/* Local UI catalogs. Never translate identifiers, input values or user files. */
(() => {
  'use strict';
  const supported = ['es', 'en', 'pt'];
  const normalize = value => supported.includes(value) ? value : 'es';
  let language = normalize(document.documentElement.lang), catalog = {}, patterns = [];
  const texts = new WeakMap(), attributes = new WeakMap();
  const protectedContent = 'script,style,code,[translate="no"],#videoTitle,#videoUploader,.history-video strong,.path-button,.conversion-file-info strong,.separation-job-title,.studio-row strong,#browserDetected small';
  const attributeNames = ['placeholder', 'title', 'aria-label', 'alt'];
  const escape = text => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const normalizeText = text => text.replace(/\s+/g, ' ').trim();
  function t(text, depth = 0) {
    const source = normalizeText(String(text ?? ''));
    if (language === 'es' || !source) return String(text ?? '');
    const index = language === 'en' ? 0 : 1;
    if (catalog[source]) return catalog[source][index];
    if (depth < 3) {
      for (const {expression, translations, tokens} of patterns) {
        const match = source.match(expression);
        if (match && !match.slice(1).some(value => value.includes(' · '))) {
          return translations[index].replace(/\{(\d+)\}/g, (_, key) => {
            const value = match[tokens.indexOf(key) + 1];
            return tokens.translateTerms ? t(value, depth + 1) : value;
          });
        }
      }
      if (source.includes(' · ')) return source.split(' · ').map(part => t(part, depth + 1)).join(' · ');
    }
    return String(text ?? '');
  }
  const protectedNode = element => !element || element.closest(protectedContent);
  function localizeText(node) {
    if (protectedNode(node.parentElement)) return;
    const previous = texts.get(node);
    const source = previous && node.data === previous.output ? previous.source : node.data;
    if (!source.trim()) return;
    const [, start, content, end] = source.match(/^(\s*)([\s\S]*?)(\s*)$/);
    const output = start + t(content) + end;
    texts.set(node, {source, output});
    if (node.data !== output) node.data = output;
  }
  function localizeAttributes(element) {
    if (protectedNode(element)) return;
    let saved = attributes.get(element);
    if (!saved) attributes.set(element, saved = new Map());
    for (const name of attributeNames) {
      if (!element.hasAttribute(name)) continue;
      const value = element.getAttribute(name), previous = saved.get(name);
      const source = previous && value === previous.output ? previous.source : value;
      const output = t(source);
      saved.set(name, {source, output});
      if (value !== output) element.setAttribute(name, output);
    }
  }
  function localize(root) {
    if (root.nodeType === Node.TEXT_NODE) return localizeText(root);
    if (root.nodeType !== Node.ELEMENT_NODE || protectedNode(root)) return;
    localizeAttributes(root);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode(node) { return protectedNode(node.nodeType === Node.TEXT_NODE ? node.parentElement : node) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; },
    });
    let node;
    while ((node = walker.nextNode())) {
      if (node.nodeType === Node.TEXT_NODE) localizeText(node);
      else localizeAttributes(node);
    }
  }
  const observer = new MutationObserver(changes => {
    observer.disconnect();
    try {
      const roots = new Set();
      for (const change of changes) {
        if (change.type === 'childList') for (const node of change.addedNodes) roots.add(node);
        else roots.add(change.target);
      }
      for (const root of roots) if (root.isConnected) localize(root);
    } finally { observe(); }
  });
  function observe() {
    observer.observe(document.documentElement, {subtree:true, childList:true, characterData:true, attributes:true, attributeFilter:attributeNames});
  }
  function apply() {
    observer.disconnect();
    try {
      document.documentElement.lang = language;
      localize(document.documentElement);
      const selector = document.querySelector('#settingsLanguage');
      if (selector) selector.value = language;
    } finally { observe(); }
  }
  let channel;
  try { channel = new BroadcastChannel('videoflow-interface-language'); } catch { /* Language still works without cross-window support. */ }
  const ready = fetch('/static/locales/messages.json').then(response => {
    if (!response.ok) throw new Error('No se pudieron cargar los idiomas.');
    return response.json();
  }).then(messages => {
    catalog = messages;
    patterns = Object.entries(catalog).filter(([key]) => /\{\d+\}/.test(key)).map(([key, translations]) => {
      const tokens = [];
      tokens.translateTerms = ['Modo {0}. Cambiar a {1}', 'Guardando {0}', 'Instalada: {0}', 'Última versión: {0}'].includes(key);
      const expression = key.split(/(\{\d+\})/).map(part => {
        const token = part.match(/^\{(\d+)\}$/);
        if (!token) return escape(part);
        tokens.push(token[1]); return '(.+?)';
      }).join('');
      return {expression:new RegExp('^' + expression + '$'), translations, tokens};
    });
    apply();
  });
  async function setLanguage(value, broadcast = true) {
    await ready;
    language = normalize(value);
    apply();
    document.dispatchEvent(new CustomEvent('videoflow:language', {detail:{language}}));
    if (broadcast) channel?.postMessage({language});
  }
  if (channel) channel.onmessage = event => {
    if (supported.includes(event.data?.language)) setLanguage(event.data.language, false).catch(console.error);
  };
  window.VideoFlowI18n = {t, ready, setLanguage, get language() {return language;},
    get locale() {return {es:'es-PE', en:'en-US', pt:'pt-BR'}[language];}};
  ready.catch(error => console.error(error));
  window.addEventListener('pagehide', () => { observer.disconnect(); channel?.close(); });
})();
