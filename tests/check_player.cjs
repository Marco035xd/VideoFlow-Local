/* Regression checks for replay, page visibility, interrupted play and file drops. */
const fs = require('fs'), vm = require('vm'), assert = require('assert');
class Node extends EventTarget {
  constructor() { super(); this.disabled = false; this.textContent = ''; this.value = '1'; this.dataset = {}; this.classList = {add(){},remove(){}}; this.style = {setProperty(){}}; this.attributes = {}; }
  setAttribute(name,value) { this.attributes[name] = value; }
  click() { this.dispatchEvent(new Event('click')); }
}
class Video extends Node {
  constructor() { super(); this.paused = true; this.ended = false; this.duration = 4; this.currentTime = 0; this.volume = 1; this.playCalls = 0; this.captures = []; }
  getAttribute(name) { return this[name]; }
  load() { this.ended = false; this.error = null; this.dispatchEvent(new Event('loadedmetadata')); }
  async play() { this.playCalls++; if (this.rejectPlay) throw this.rejectPlay; this.ended = false; this.paused = false; this.dispatchEvent(new Event('play')); }
  pause() { this.paused = true; this.dispatchEvent(new Event('pause')); }
  getBoundingClientRect() { return {left:0,width:800,bottom:500,height:500}; }
  setPointerCapture(id) { this.captures.push(id); }
  hasPointerCapture() { return this.captures.length > 0; }
  releasePointerCapture() { this.captures.pop(); }
}
const nodes = new Map(), node = id => {
  if (!nodes.has(id)) nodes.set(id, id === '#localPlayer' ? new Video() : new Node());
  return nodes.get(id);
};
const document = Object.assign(new EventTarget(), {hidden:false, querySelector:node, pictureInPictureEnabled:true});
const window = new EventTarget(), state = {currentPage:'player'}, revoked = [], blobs = [];
const context = vm.createContext({document,window,state,Event,performance,URL:{revokeObjectURL:url=>revoked.push(url),createObjectURL:file=>{blobs.push(file);return 'blob:test';}},api:async()=>({}),toast(){},console});
vm.runInContext(fs.readFileSync('static/player.js','utf8'), context);
const fire = (target, name, properties = {}) => {
  const event = new Event(name, {cancelable:true});
  Object.assign(event, properties); target.dispatchEvent(event); return event;
};
const flush = () => new Promise(resolve=>setImmediate(resolve));
(async()=>{
  const playback = vm.runInContext('initMainPlayer()',context), video = node('#localPlayer');
  await window.openPlayerMedia({name:'fixture.mp4',url:'/api/media/test',token:'test'});
  assert.equal(video.paused,false); assert.equal(node('#playerFloating').disabled,false);
  const seek=node('#playerSeek'), volume=node('#playerVolume');
  assert.equal(seek.disabled,false); assert.equal(seek.max,'4');
  fire(seek,'pointerdown'); seek.value='2.5'; fire(seek,'input');
  assert.equal(video.currentTime,2.5); assert.equal(video.paused,false);
  video.currentTime=2.6; fire(video,'timeupdate');
  assert.equal(seek.value,'2.5','Playback updates must not fight a thumb being dragged');
  fire(seek,'pointerup'); assert.equal(video.currentTime,2.5);
  volume.value='37'; fire(volume,'input'); assert.equal(video.volume,.37); assert.equal(video.muted,false);
  node('#playerMute').click(); assert.equal(video.muted,true); assert.equal(volume.value,'0');
  node('#playerMute').click(); assert.equal(video.muted,false); assert.equal(volume.value,'37');
  volume.value='0'; fire(volume,'input'); node('#playerMute').click(); assert.equal(video.volume,.37);
  video.pause(); seek.value='1'; fire(seek,'input'); fire(seek,'change'); assert.equal(video.currentTime,1); assert.equal(video.paused,true);
  const shell=node('#playerShell');
  shell.requestFullscreen=async()=>{document.fullscreenElement=shell;fire(document,'fullscreenchange');};
  document.exitFullscreen=async()=>{document.fullscreenElement=null;fire(document,'fullscreenchange');};
  playback.update(); node('#playerFullscreen').click(); await flush(); assert.equal(document.fullscreenElement,shell);
  node('#playerFullscreen').click(); await flush(); assert.equal(document.fullscreenElement,null);
  video.currentTime = 4; video.ended = true; video.pause(); fire(video,'ended');
  assert.equal(node('#playerPlay').textContent,'Volver a reproducir');
  node('#playerPlay').click(); await flush();
  assert.equal(video.currentTime,0); assert.equal(video.paused,false);
  video.currentTime=1.5; state.currentPage='home'; fire(window,'videoflow:navigate');
  assert.equal(video.paused,true); assert.equal(video.currentTime,1.5);
  state.currentPage='player'; fire(window,'videoflow:navigate'); await flush();
  assert.equal(video.paused,false); assert.equal(video.currentTime,1.5);
  node('#playerPlay').click();
  state.currentPage='home'; fire(window,'videoflow:navigate');
  state.currentPage='player'; fire(window,'videoflow:navigate'); await flush();
  assert.equal(video.paused,true,'User-paused video must stay paused');
  node('#playerRestart').click(); await flush(); assert.equal(video.currentTime,0); assert.equal(video.paused,false);
  document.hidden=true; fire(document,'visibilitychange'); assert.equal(video.paused,true);
  document.hidden=false; fire(document,'visibilitychange'); await flush(); assert.equal(video.paused,false);
  video.rejectPlay={name:'NotAllowedError'}; video.pause(); await playback.play();
  assert.match(node('#playerMessage').textContent,/Pulsa Reproducir/);
  video.rejectPlay=null;
  // A simple click must not capture the native replay control's pointer.
  fire(video,'pointerdown',{pointerId:1,button:0,clientX:200,clientY:200});
  assert.equal(video.captures.length,0); fire(video,'pointerup');
  fire(video,'pointerdown',{pointerId:2,button:0,clientX:200,clientY:200});
  fire(video,'pointermove',{pointerId:2,clientX:201,clientY:160});
  assert.equal(video.captures.length,1); fire(window,'videoflow:navigate'); assert.equal(video.captures.length,0);
  const target=node('#playerDropTarget');
  fire(target,'drop',{dataTransfer:{files:[{name:'movie.mp4',type:'video/mp4'}],types:['Files']}}); await flush();
  assert.equal(video.src,'blob:test'); assert.equal(video.paused,false); assert.equal(node('#playerName').textContent,'movie.mp4');
  await window.openPlayerMedia({url:'/api/media/next',token:'next',name:'next.mp4'});
  assert.deepEqual(revoked,['blob:test']);
  const old=video.src;
  fire(target,'drop',{dataTransfer:{files:[{name:'bad.txt',type:'text/plain'}],types:['Files']}});
  assert.equal(video.src,old); assert.match(node('#playerMessage').textContent,/video o audio/);
  fire(target,'drop',{dataTransfer:{files:[{name:'one.mp4'},{name:'two.mp4'}],types:['Files']}});
  assert.equal(video.src,old); assert.match(node('#playerMessage').textContent,/un solo/);
  target.dataset.nativeDrop='ready';
  const drop=fire(target,'drop',{dataTransfer:{files:[{name:'desktop.mp4',type:'video/mp4'}],types:['Files']}});
  assert.equal(video.src,old,'Desktop waits for the native file token');
  await window.openPlayerMedia({url:'/api/media/drop',token:'drop',name:'desktop.mp4'},drop.videoflowDropId);
  assert.equal(video.src,'/api/media/drop'); assert.equal(node('#playerFloating').disabled,false);
  await window.openPlayerMedia({url:'/api/media/stale',name:'stale.mp4'},'old-request');
  assert.equal(video.src,'/api/media/drop');
  console.log('PASS: seek dragging while playing/paused, independent volume/mute, fullscreen, replay, tab resume, gestures and file drops.');
})().catch(error=>{console.error(error);process.exitCode=1;});
