/* A local, temporary Easter egg: no preferences or download state are changed. */
class KonamiCode {
  constructor(activate) {
    this.sequence = ['arrowup','arrowup','arrowdown','arrowdown','arrowleft','arrowright','arrowleft','arrowright','b','a'];
    this.keys = []; this.last = 0; this.activate = activate;
  }
  handle(event, now = performance.now()) {
    const target = event.target;
    if (event.isComposing || event.ctrlKey || event.altKey || event.metaKey || event.repeat ||
        target?.isContentEditable || target?.closest?.('input, textarea, select, [contenteditable]:not([contenteditable="false"])')) {
      this.keys = []; return;
    }
    if (now - this.last > 4000) this.keys = [];
    this.last = now;
    this.keys.push(event.key.toLowerCase());
    if (this.keys.length > this.sequence.length) this.keys.shift();
    if (this.keys.length === this.sequence.length && this.keys.every((key, index) => key === this.sequence[index])) {
      this.keys = []; this.activate();
    }
  }
}

function initArcade() {
  const dialog = document.querySelector('#arcadeDialog');
  if (!dialog) return;
  const get = name => document.querySelector('#arcade' + name);
  const canvas = get('Canvas'), context = canvas.getContext('2d');
  if (!context) return;
  const width = canvas.width, height = canvas.height;
  let running = false, frame = 0, previous = null, remaining = 30, score = 0;
  let notes = [], spawn = 0, ship = width / 2, keys = new Set(), pointerDirection = 0;
  let restoreVideo = null, restoreSource = null;
  const stars = Array.from({length:40}, (_,i) => ({x:(i * 137 + 31) % width,y:(i * 73 + 17) % (height - 45)}));
  let accent = '#80a8ff';
  const update = () => { get('Score').textContent = String(score); get('Time').textContent = Math.ceil(remaining) + ' s'; };
  const render = () => {
    context.fillStyle = '#070c19'; context.fillRect(0,0,width,height);
    context.fillStyle = '#7789ae'; for (const star of stars) context.fillRect(star.x,star.y,2,2);
    context.strokeStyle = '#1b2b47'; context.beginPath(); context.moveTo(0,height-36);context.lineTo(width,height-36);context.stroke();
    for (const note of notes) {
      context.fillStyle = note.color; context.fillRect(note.x-2,note.y-12,4,18); context.fillRect(note.x+1,note.y-12,11,4);
      context.beginPath(); context.ellipse(note.x-6,note.y+6,8,6,0,0,Math.PI*2); context.fill();
    }
    context.fillStyle = accent;
    context.fillRect(ship-23,height-31,46,20); context.fillRect(ship-14,height-39,28,8);
    context.fillStyle = '#070c19'; context.beginPath();context.moveTo(ship-4,height-28);context.lineTo(ship+7,height-21);context.lineTo(ship-4,height-14);context.fill();
    if (!running) {
      context.fillStyle = '#070c19d9'; context.fillRect(85,95,width-170,100);
      context.fillStyle = '#f2f6ff'; context.textAlign = 'center'; context.font = 'bold 22px Consolas, monospace';
      context.fillText(remaining > 0 ? 'ATRAPA EL RITMO' : '¡RONDA COMPLETADA!',width/2,133);
      context.font = '14px Consolas, monospace'; context.fillStyle = '#b4c5e9';
      context.fillText(remaining > 0 ? 'Pulsa Jugar para comenzar' : `${score} notas · ¿Una ronda más?`,width/2,164);
    }
  };
  const finish = () => {
    running = false; keys.clear(); pointerDirection = 0; frame = 0;
    get('Start').textContent = 'Jugar otra vez';
    get('Status').textContent = `¡Conseguiste ${score} notas! Tus descargas siguen trabajando.`;
    update(); render();
  };
  const tick = timestamp => {
    if (!running || !dialog.open) return;
    const delta = previous === null ? 0 : Math.min(.05,(timestamp - previous)/1000);
    previous = timestamp;
    if (!document.hidden) {
      remaining = Math.max(0,remaining - delta);
      const direction = pointerDirection || (Number(keys.has('arrowright') || keys.has('d')) - Number(keys.has('arrowleft') || keys.has('a')));
      ship = Math.max(25,Math.min(width-25,ship + direction * 350 * delta));
      spawn -= delta;
      if (spawn <= 0) { notes.push({x:25+Math.random()*(width-50),y:-15,color:score%2?'#69e0d2':accent});spawn=.55; }
      notes = notes.filter(note => {
        note.y += (100 + Math.min(score*3,90)) * delta;
        if (note.y >= height-47 && note.y <= height-23 && Math.abs(note.x-ship)<31) { score++; return false; }
        return note.y < height+20;
      });
    }
    update(); render();
    if (remaining <= 0) return finish();
    frame = requestAnimationFrame(tick);
  };
  const start = () => {
    cancelAnimationFrame(frame); running = true; remaining = 30; score = 0; notes = []; spawn = 0; previous = null; keys.clear();
    get('Start').textContent = 'Reiniciar ronda'; get('Status').textContent = '¡Atrapa tantas notas como puedas!';
    canvas.focus(); update(); frame = requestAnimationFrame(tick);
  };
  const open = () => {
    if (dialog.open) return;
    accent = getComputedStyle(document.documentElement).getPropertyValue('--primary').trim() || '#80a8ff';
    const video = document.querySelector('#localPlayer');
    restoreVideo = video && !video.paused && !video.ended ? video : null;
    restoreSource = restoreVideo?.currentSrc;
    restoreVideo?.pause();
    remaining = 30; score = 0; notes = []; ship = width/2; running = false;
    get('Start').textContent = 'Jugar'; get('Status').textContent = 'Un pequeño secreto para acompañar tus descargas.';
    dialog.showModal(); update(); render(); get('Start').focus();
  };
  get('Start').addEventListener('click', start);
  get('Close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    running = false; cancelAnimationFrame(frame); frame = 0; keys.clear(); pointerDirection = 0;
    if (restoreVideo && restoreVideo.currentSrc === restoreSource && !document.hidden && state.currentPage === 'player') restoreVideo.play().catch(()=>{});
    restoreVideo = null; restoreSource = null;
  });
  dialog.addEventListener('keydown', event => {
    const key = event.key.toLowerCase();
    if (['arrowleft','arrowright','a','d'].includes(key)) { event.preventDefault(); keys.add(key); }
  });
  dialog.addEventListener('keyup', event => keys.delete(event.key.toLowerCase()));
  window.addEventListener('blur', () => { keys.clear(); pointerDirection = 0; previous = null; });
  document.addEventListener('visibilitychange', () => { keys.clear(); pointerDirection = 0; previous = null; });
  canvas.addEventListener('pointermove', event => {
    if (!running) return;
    const rect = canvas.getBoundingClientRect();
    ship = Math.max(25,Math.min(width-25,(event.clientX-rect.left)/rect.width*width));
  });
  for (const [name,direction] of [['Left',-1],['Right',1]]) {
    const button = get(name);
    button.addEventListener('pointerdown', event => { pointerDirection = direction; button.setPointerCapture(event.pointerId); });
    for (const event of ['pointerup','pointercancel','lostpointercapture']) button.addEventListener(event, () => { pointerDirection = 0; });
  }
  const konami = new KonamiCode(open);
  document.addEventListener('keydown', event => { if (!dialog.open) konami.handle(event); },true);
}
document.addEventListener('DOMContentLoaded',initArcade);
