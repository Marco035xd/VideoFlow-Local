const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const element = () => ({
  value:'', disabled:false, textContent:'', children:[],
  replaceChildren() { this.children = []; },
  append(...items) { this.children.push(...items); },
  setAttribute() {},
});
const fields = new Map();
const field = key => {
  if (!fields.has(key)) fields.set(key, element());
  return fields.get(key);
};
const tabs = [
  ['youtube', 'YouTube', 'youtube.com youtu.be'],
  ['tiktok', 'TikTok', 'tiktok.com'],
  ['reddit', 'Reddit', 'reddit.com redd.it redditmedia.com'],
  ['instagram', 'Instagram', 'instagram.com instagr.am'],
].map(([source, platform, domains]) => ({ dataset:{source, platform, domains} }));
const downloads = [];
const analyze = [];
const context = vm.createContext({
  URL, JSON, console,
  document:{
    querySelector:field,
    querySelectorAll:selector => selector === '.source-tab' ? tabs : [],
    createElement:element,
    createTextNode:value => value,
    addEventListener() {},
  },
  async fixtureApi(path, options) {
    const data = JSON.parse(options.body);
    if (path === '/api/analyze') {
      analyze.push(data);
      const heights = data.url.includes('redd.it') ? ['0'] : data.url.includes('instagram.com') ? ['480','960'] : ['360','720'];
      return {video:{url:data.url, title:'Fixture', id:'v', video_options:heights.map(value => ({value}))}};
    }
    downloads.push(data);
    return {ok:true};
  },
});
for (const path of ['static/app.js','static/extensions.js']) vm.runInContext(fs.readFileSync(path, 'utf8'), context);
vm.runInContext(`
  api = fixtureApi;
  toast = () => {};
  loadDownloads = async () => {};
  globalThis.browserForSource = source => source === 'instagram' ? 'firefox' : '';
  globalThis.setDownloadSessionBusy = () => {};
  globalThis.advancedOptions = () => ({});
`, context);

async function batch(source, links, maximum, folder) {
  vm.runInContext(`state.source = "${source}"`, context);
  field('#videoUrl').value = links.join('\n');
  field('#batchDestination').value = folder;
  field('#batchMode').value = 'video_audio';
  field('#batchFormat').value = 'mp4';
  field('#batchVideoQuality').value = maximum;
  await vm.runInContext('batchDownload()', context);
  assert.equal(field('#batchStart').disabled, false);
}

(async () => {
  const youtube = 'https://youtu.be/a';
  const tiktok = 'https://www.tiktok.com/@u/video/1';
  await batch('youtube', [youtube, youtube, 'https://youtube.com/watch?v=b', tiktok], '720', 'C:/Downloads');
  assert.equal(downloads.length, 2);
  assert(downloads.every(item => item.quality === '720' && item.folder === 'C:/Downloads'));
  assert.equal(field('#videoUrl').value, tiktok);

  const reddit = 'https://redd.it/sample';
  const misleading = 'https://reddit.com.example.org/r/video';
  await batch('reddit', [reddit, misleading, 'ftp://redd.it/sample'], '0', 'C:/Reddit');
  assert.deepEqual([downloads[2].url, downloads[2].quality, downloads[2].folder], [reddit, '0', 'C:/Reddit']);
  assert(!analyze.some(item => item.url === misleading || item.url.startsWith('ftp:')));
  assert.equal(field('#videoUrl').value, misleading + '\nftp://redd.it/sample');

  const reel = 'https://www.instagram.com/reel/sample/';
  await batch('instagram', [reel], '1080', 'C:/Instagram');
  assert.deepEqual([downloads[3].url, downloads[3].quality, downloads[3].browser], [reel, '960', 'firefox']);
  assert.equal(field('#videoUrl').value, '');
  console.log('OK: lotes por plataforma, deduplicación, destinos, resolución original y sesión elegida.');
})().catch(error => { console.error(error); process.exitCode = 1; });
