const fs = require('fs'), vm = require('vm'), assert = require('assert');
const nodes = new Map(), variables = new Map(), requests = [];
const node = key => {
  if (!nodes.has(key)) nodes.set(key, {textContent:'', classList:{toggle(){},add(){},remove(){}}, setAttribute(){}});
  return nodes.get(key);
};
const context = vm.createContext({
  window: {matchMedia:()=>({matches:false}), setTimeout}, clearTimeout,
  document:{documentElement:{dataset:{},style:{setProperty:(key,value)=>variables.set(key,value)}}},
  $:node, $$:()=>[], state:{settings:{}},
  api:async (path,options)=>new Promise(resolve=>requests.push({payload:JSON.parse(options.body),resolve})),
});
vm.runInContext(fs.readFileSync('static/appearance.js','utf8'),context);
const contrast=(a,b)=>vm.runInContext(`appearanceContrast(${JSON.stringify(a)},${JSON.stringify(b)})`,context);
for (const preset of ['videoflow','graphite','ocean','forest','plum','sand']) {
  for (const mode of ['light','dark','system']) {
    for (const accent of ['default','blue','green','yellow','pink','orange','purple','white','custom']) {
      vm.runInContext(`applyAppearance({theme:'${mode}',appearance:{...appearanceDefaults,preset:'${preset}',accent:'${accent}'}})`,context);
      assert(contrast(variables.get('--primary'),variables.get('--surface-solid'))>=4.5);
      for (const key of ['--primary','--primary-2']) assert(contrast(variables.get(key),variables.get('--on-primary'))>=4.5);
      for (const key of ['--hero-start','--hero-mid','--hero-end']) assert(contrast(variables.get(key),variables.get('--hero-text'))>=4.5);
    }
  }
}
vm.runInContext("applyAppearance({theme:'dark',appearance:{...appearanceDefaults,custom_colors:true,background:'#ffffff',foreground:'#181818'}})",context);
assert.equal(variables.get('--bg'),'#ffffff');
assert.equal(context.document.documentElement.dataset.theme,'light');
assert(contrast(variables.get('--text'),variables.get('--surface-solid'))>=4.5);

(async()=>{
  const first=vm.runInContext("appearanceState.draft={theme:'dark',appearance:{...appearanceDefaults}};appearanceState.version=1;persistAppearance()",context);
  vm.runInContext("appearanceState.draft={theme:'light',appearance:{...appearanceDefaults,preset:'forest'}};appearanceState.version=2;persistAppearance()",context);
  assert.equal(requests.length,1,'Saves must be serialized');
  requests[0].resolve({settings:requests[0].payload}); await first;
  assert.equal(requests.length,2);
  assert.equal(requests[1].payload.appearance.preset,'forest');
  requests[1].resolve({settings:requests[1].payload});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(context.state.settings.theme,'light');
  assert.equal(context.state.settings.appearance.preset,'forest');
  console.log('OK: 162 preset/mode/accent combinations keep readable controls and banners; custom colors adapt; rapid saves preserve the latest selection.');
})().catch(error=>{console.error(error);process.exitCode=1;});
