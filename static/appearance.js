const appearanceDefaults = {
  preset: 'videoflow', accent: 'default', custom_accent: '#8b5cf6', custom_colors: false,
  background: '#181818', foreground: '#ffffff', font: 'system', density: 'comfortable', reduce_motion: false,
};
const appearancePresets = {
  videoflow: {name:'VideoFlow', description:'El azul de siempre', light:['#f3f6fb','#ffffff','#f7f9fc','#eef3fa','#162033','#246bfd'], dark:['#0c111c','#141b29','#182131','#202b3d','#eef3ff','#6b98ff']},
  graphite: {name:'Grafito', description:'Simple y neutral', light:['#f3f3f3','#ffffff','#fafafa','#ececec','#1f2328','#246bfd'], dark:['#181818','#232323','#292929','#333333','#f5f5f5','#7da5ff']},
  ocean: {name:'Océano', description:'Azules profundos', light:['#eff6fb','#ffffff','#f2f8fc','#e3eef5','#123044','#007c99'], dark:['#071b26','#0e2733','#143340','#1c4352','#ecf8ff','#42cce2']},
  forest: {name:'Bosque', description:'Verde natural', light:['#f2f7f1','#ffffff','#f6faf5','#e8f0e6','#243526','#087f66'], dark:['#0d1b15','#16281e','#1e3327','#2a4334','#edf7ef','#3cd9a0']},
  plum: {name:'Ciruela', description:'Un toque violeta', light:['#f7f3fa','#ffffff','#faf6fc','#efe6f5','#32203c','#7540c8'], dark:['#1c1325','#291d34','#342440','#433150','#f8edff','#bf9cff']},
  sand: {name:'Arena', description:'Tonos cálidos', light:['#f8f4ed','#fffdf8','#f9f5ed','#ede5d6','#3a3022','#95640d'], dark:['#211c16','#2e271e','#393024','#4a3e2e','#fff6e6','#edc17a']},
};
const appearanceAccents = {
  default: ['Del tema', null, null], blue:['Azul','#246bfd','#6b98ff'], green:['Verde','#087f66','#3cd9a0'],
  yellow:['Amarillo','#9a6500','#f5c84c'], pink:['Rosa','#b72175','#f281b2'], orange:['Naranja','#bc4c19','#ffab76'],
  purple:['Morado','#7540c8','#b99aff'], white:['Blanco','#283345','#f2f4f8'], custom:['Personalizado',null,null],
};
const appearanceFonts = {
  system: '"Segoe UI Variable", "Segoe UI", system-ui, sans-serif',
  humanist: '"Trebuchet MS", "Segoe UI", sans-serif',
  serif: 'Georgia, "Times New Roman", serif', mono: '"Cascadia Code", Consolas, monospace',
};
const appearanceMedia = window.matchMedia('(prefers-color-scheme: dark)');
const appearanceState = {draft:null, version:0, inFlight:false, timer:null, valid:true, initialized:false};

function appearanceRGB(hex) { return [1,3,5].map(index => parseInt(hex.slice(index,index+2),16)); }
function appearanceMix(first, second, amount) {
  const a=appearanceRGB(first), b=appearanceRGB(second);
  return '#'+a.map((value,index)=>Math.round(value*(1-amount)+b[index]*amount).toString(16).padStart(2,'0')).join('');
}
function appearanceLuminance(hex) {
  return appearanceRGB(hex).map(value=>{value/=255;return value<=.04045?value/12.92:((value+.055)/1.055)**2.4;})
    .reduce((sum,value,index)=>sum+value*[.2126,.7152,.0722][index],0);
}
function appearanceContrast(first,second) {
  const values=[appearanceLuminance(first),appearanceLuminance(second)].sort((a,b)=>b-a);
  return (values[0]+.05)/(values[1]+.05);
}
function appearanceReadable(color, background, minimum=4.5) {
  const end=appearanceContrast('#ffffff',background)>appearanceContrast('#000000',background)?'#ffffff':'#000000';
  for(let step=0;step<=100;step++) {
    const candidate=appearanceMix(color,end,step/100);
    if(appearanceContrast(candidate,background)>=minimum) return candidate;
  }
  return end;
}
function appearanceRGBA(hex,opacity) {return `rgba(${appearanceRGB(hex).join(',')},${opacity})`;}
function appearanceError(preferences) {
  for(const key of ['custom_accent','background','foreground']) {
    if(!/^#[0-9a-f]{6}$/i.test(preferences[key])) return 'Escribe un color válido, por ejemplo #181818.';
  }
  if(preferences.custom_colors && appearanceContrast(preferences.background,preferences.foreground)<4.5) {
    return 'Elige un fondo y un texto con más contraste para poder leer la aplicación.';
  }
  return '';
}

function applyAppearancePalette(draft) {
  if(!draft) return;
  const preferences=draft.appearance;
  let mode=draft.theme==='system'?(appearanceMedia.matches?'dark':'light'):draft.theme;
  let [bg,surface,surface2,surface3,text,baseAccent]=appearancePresets[preferences.preset][mode];
  if(preferences.custom_colors) {
    bg=preferences.background; text=preferences.foreground;
    mode=appearanceLuminance(bg)<.35?'dark':'light';
    const customSurface=amount=>{
      const result=appearanceMix(bg,text,amount);
      return appearanceContrast(text,result)>=4.5?result:bg;
    };
    surface=customSurface(.045);surface2=customSurface(.075);surface3=customSurface(.12);
  }
  const accent=preferences.accent==='custom'?preferences.custom_accent:
    appearanceAccents[preferences.accent][mode==='dark'?2:1] || baseAccent;
  const primary=appearanceReadable(accent,surface);
  const onPrimary=appearanceContrast('#ffffff',primary)>appearanceContrast('#000000',primary)?'#ffffff':'#000000';
  const primary2=appearanceMix(primary,onPrimary==='#ffffff'?'#000000':'#ffffff',.08);
  const heroColor=appearanceReadable(primary,'#ffffff');
  const variables={
    '--bg':bg,'--surface':surface,'--surface-solid':surface,'--surface-2':surface2,'--surface-3':surface3,'--text':text,
    '--muted':appearanceReadable(appearanceMix(text,surface,.35),surface),
    '--muted-2':appearanceReadable(appearanceMix(text,surface,.43),surface),
    '--line':appearanceRGBA(text,.12),'--line-strong':appearanceRGBA(text,.23),
    '--primary':primary,'--primary-2':primary2,'--primary-soft':appearanceRGBA(primary,.13),
    '--on-primary':onPrimary,'--accent-glow':appearanceRGBA(primary,.22),'--cyan':primary2,
    '--hero-start':appearanceMix(heroColor,'#000000',.3),'--hero-mid':appearanceMix(heroColor,'#000000',.12),
    '--hero-end':heroColor,'--hero-text':'#ffffff',
    '--app-font':appearanceFonts[preferences.font],
  };
  for(const [name,color] of Object.entries({green:mode==='dark'?'#42cc8b':'#087b4d',amber:mode==='dark'?'#f0ad49':'#975b09',red:mode==='dark'?'#ff8290':'#bd3042'})) {
    const readable=appearanceReadable(color,surface);variables['--'+name]=readable;variables['--'+name+'-soft']=appearanceRGBA(readable,.13);
  }
  const root=document.documentElement;
  root.dataset.theme=mode;root.dataset.preset=preferences.preset;root.dataset.density=preferences.density;
  root.dataset.reduceMotion=String(preferences.reduce_motion);root.style.colorScheme=mode;
  for(const [key,value] of Object.entries(variables)) root.style.setProperty(key,value);
  return mode;
}

function applyAppearance(draft) {
  const mode = applyAppearancePalette(draft);
  if (!mode) return;
  const preferences = draft.appearance;
  for(const label of $$('.appearance-preset')) {
    const palette=appearancePresets[label.dataset.preset][mode];
    const sample=label.querySelector('.preset-sample');
    sample.style.setProperty('--sample-bg',palette[0]);sample.style.setProperty('--sample-surface',palette[1]);sample.style.setProperty('--sample-accent',palette[5]);
  }
  const modeName={system:'Automático',light:'Claro',dark:'Oscuro'};
  $('#themeToggle').textContent={system:'◐',light:'☀',dark:'☾'}[draft.theme];
  const next={system:'light',light:'dark',dark:'system'}[draft.theme];
  const toggleLabel=`Modo ${modeName[draft.theme].toLowerCase()}. Cambiar a ${modeName[next].toLowerCase()}`;
  $('#themeToggle').title=toggleLabel;$('#themeToggle').setAttribute('aria-label',toggleLabel);
  $('#appearanceSummary').textContent=`${appearancePresets[preferences.preset].name} · ${modeName[draft.theme]} · ${appearanceAccents[preferences.accent][0]}${preferences.custom_colors?' · Colores propios':''}`;
}

function appearanceStatus(message, error=false) {
  $('#appearanceSaveStatus').textContent=message;
  $('#appearanceSaveStatus').classList.toggle('is-error',error);
}
function syncAppearanceControls() {
  const {theme,appearance:preferences}=appearanceState.draft;
  for(const [name,value] of Object.entries({appearanceMode:theme,appearancePreset:preferences.preset,appearanceAccent:preferences.accent})) {
    $$(`input[name="${name}"]`).forEach(input=>{input.checked=input.value===value;});
  }
  for(const [id,key] of [['CustomAccent','custom_accent'],['Background','background'],['Foreground','foreground']]) {
    $('#appearance'+id).value=preferences[key];$('#appearance'+id+'Hex').value=preferences[key];
  }
  $('#appearanceCustomColors').checked=preferences.custom_colors;
  $('#appearanceFont').value=preferences.font;$('#appearanceDensity').value=preferences.density;
  $('#appearanceMotion').checked=preferences.reduce_motion;
  refreshAppearanceFields();
}
function refreshAppearanceFields() {
  const custom=$('input[name="appearanceAccent"]:checked')?.value==='custom';
  $('#appearanceCustomAccentRow').classList.toggle('hidden',!custom);
  const colors=$('#appearanceCustomColors').checked;
  $$('#appearanceCustomColorFields input').forEach(input=>{input.disabled=!colors;});
  $('#appearanceCustomColorFields').classList.toggle('is-inactive',!colors);
  $('#appearanceContrast').textContent=colors?'El fondo y el texto personalizados sustituyen a los del tema.':'Activa los colores personalizados para modificar el fondo y el texto.';
}
function readAppearanceControls() {
  return {theme:$('input[name="appearanceMode"]:checked').value,appearance:{
    preset:$('input[name="appearancePreset"]:checked').value,accent:$('input[name="appearanceAccent"]:checked').value,
    custom_accent:$('#appearanceCustomAccentHex').value.toLowerCase(),custom_colors:$('#appearanceCustomColors').checked,
    background:$('#appearanceBackgroundHex').value.toLowerCase(),foreground:$('#appearanceForegroundHex').value.toLowerCase(),
    font:$('#appearanceFont').value,density:$('#appearanceDensity').value,reduce_motion:$('#appearanceMotion').checked,
  }};
}
function appearanceChanged() {
  clearTimeout(appearanceState.timer);
  appearanceState.draft=readAppearanceControls();appearanceState.version+=1;
  refreshAppearanceFields();
  const error=appearanceError(appearanceState.draft.appearance);
  appearanceState.valid=!error;
  $('#appearanceRetry').classList.add('hidden');
  if(error) {appearanceStatus(error,true);return;}
  applyAppearance(appearanceState.draft);
  appearanceStatus('Guardando apariencia…');
  appearanceState.timer=window.setTimeout(persistAppearance,200);
}
async function persistAppearance() {
  clearTimeout(appearanceState.timer);
  if(appearanceState.inFlight || !appearanceState.valid) return;
  const version=appearanceState.version;
  const snapshot=JSON.parse(JSON.stringify(appearanceState.draft));
  appearanceState.inFlight=true;
  try {
    const result=await api('/api/settings',{method:'PUT',body:JSON.stringify(snapshot)});
    state.settings.theme=result.settings.theme;state.settings.appearance=result.settings.appearance;
    if(version===appearanceState.version) {
      appearanceStatus('✓ Apariencia guardada en este equipo.');$('#appearanceRetry').classList.add('hidden');
    }
  } catch(error) {
    if(version===appearanceState.version) {appearanceStatus('No se pudo guardar: '+error.message,true);$('#appearanceRetry').classList.remove('hidden');}
  } finally {
    appearanceState.inFlight=false;
    if(version!==appearanceState.version && appearanceState.valid) persistAppearance();
  }
}
function cycleAppearanceMode() {
  appearanceState.draft.theme={system:'light',light:'dark',dark:'system'}[appearanceState.draft.theme];
  syncAppearanceControls();appearanceChanged();
}
function initAppearance() {
  appearanceState.draft={theme:state.settings.theme,appearance:{...appearanceDefaults,...state.settings.appearance}};
  if(!appearanceState.initialized) {
    for(const [key,preset] of Object.entries(appearancePresets)) {
      const label=document.createElement('label');label.className='appearance-preset';label.dataset.preset=key;
      const input=document.createElement('input');input.type='radio';input.name='appearancePreset';input.value=key;
      const sample=document.createElement('span');sample.className='preset-sample';sample.setAttribute('aria-hidden','true');
      sample.style.setProperty('--sample-bg',preset.dark[0]);sample.style.setProperty('--sample-surface',preset.dark[1]);sample.style.setProperty('--sample-accent',preset.dark[5]);
      sample.innerHTML='<i></i><b></b><em></em>';
      const name=document.createElement('strong');name.textContent=preset.name;
      const description=document.createElement('small');description.textContent=preset.description;
      label.append(input,sample,name,description);$('#appearancePresets').append(label);
    }
    for(const [key,accent] of Object.entries(appearanceAccents)) {
      const label=document.createElement('label');label.className='appearance-accent';
      const input=document.createElement('input');input.type='radio';input.name='appearanceAccent';input.value=key;
      const swatch=document.createElement('i');swatch.setAttribute('aria-hidden','true');
      swatch.style.background=key==='custom'?'conic-gradient(#ff6d7b,#edcc62,#42cc8b,#6b98ff,#bf9cff,#ff6d7b)':key==='default'?'var(--primary)':accent[2];
      const name=document.createElement('span');name.textContent=accent[0];label.append(input,swatch,name);$('#appearanceAccents').append(label);
    }
    $('#page-appearance').addEventListener('change',event=>{
      if(!event.target.matches('input,select')) return;
      if(event.target.name==='appearancePreset') $('#appearanceCustomColors').checked=false;
      appearanceChanged();
    });
    for(const id of ['CustomAccent','Background','Foreground']) {
      $('#appearance'+id).addEventListener('input',event=>{$('#appearance'+id+'Hex').value=event.target.value;appearanceChanged();});
      $('#appearance'+id+'Hex').addEventListener('input',event=>{
        if(/^#[0-9a-f]{6}$/i.test(event.target.value)) $('#appearance'+id).value=event.target.value;
        appearanceChanged();
      });
    }
    $('#appearanceReset').onclick=()=>{
      appearanceState.draft={theme:'dark',appearance:{...appearanceDefaults}};syncAppearanceControls();appearanceChanged();
    };
    $('#appearanceRetry').onclick=()=>{appearanceStatus('Guardando apariencia…');persistAppearance();};
    appearanceMedia.addEventListener('change',()=>{
      if(appearanceState.draft.theme==='system' && appearanceState.valid) applyAppearance(appearanceState.draft);
    });
    appearanceState.initialized=true;
  }
  syncAppearanceControls();applyAppearance(appearanceState.draft);
}
