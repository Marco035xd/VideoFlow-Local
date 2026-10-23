const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes={}; const $=id=>nodes[id]??=( {value:'',disabled:false,textContent:'',children:[],replaceChildren(){this.children=[]},append(x){this.children.push(x)}} );
const downloads=[];
const context={$, $$:()=>[],state:{source:'youtube'},document:{createElement:()=>({textContent:''})},URL,Set,JSON,Number,String,Math,console, toast(){},loadDownloads:async()=>{},api:async(path,opts)=>{const data=JSON.parse(opts.body); if(path==='/api/analyze')return {video:{url:data.url,title:'Video',id:'v',video_options:[{value:'360'},{value:'720'}]}};downloads.push(data);return {ok:true}}};
vm.createContext(context);vm.runInContext(fs.readFileSync('static/extensions.js','utf8'),context);
$('#videoUrl').value='https://youtu.be/a\nhttps://youtu.be/a\nhttps://youtube.com/watch?v=b\nhttps://tiktok.com/@u/video/1';
$('#batchDestination').value='C:/Downloads';$('#batchMode').value='video_audio';$('#batchVideoQuality').value='720';$('#batchAudioQuality').value='192';$('#facebookBrowser').value='';
(async()=>{await vm.runInContext('batchDownload()',context);assert.equal(downloads.length,2);assert(downloads.every(d=>d.quality==='720'&&d.folder==='C:/Downloads'));assert($('#videoUrl').value.includes('tiktok.com'));assert.equal($('#batchStart').disabled,false);console.log('OK: lote, deduplicación, plataforma incorrecta, calidad y conservación de enlaces fallidos.');})().catch(e=>{console.error(e);process.exit(1)});
