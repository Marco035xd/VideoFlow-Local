const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context=vm.createContext({document:{addEventListener(){}},performance});
vm.runInContext(fs.readFileSync('static/arcade.js','utf8'),context);
vm.runInContext('globalThis.activations=0;globalThis.code=new KonamiCode(()=>activations++);',context);
const sequence=['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];
let time=100;
function type(keys,extra={}) { for(const key of keys) context.code.handle({key,target:{},...extra},time+=100); }
type(sequence.slice(0,9));assert.equal(context.activations,0);type(['A']);assert.equal(context.activations,1);
type(['ArrowUp','x',...sequence.slice(2)]);assert.equal(context.activations,1);
type(sequence,{target:{closest:()=>({})}});assert.equal(context.activations,1,'Typing in an input must not activate the game');
type(sequence,{repeat:true});type(sequence,{ctrlKey:true});assert.equal(context.activations,1);
type(sequence.slice(0,5));time+=5000;type(sequence.slice(5));assert.equal(context.activations,1);
type(['x',...sequence]);assert.equal(context.activations,2);
type(sequence);assert.equal(context.activations,3,'Code can reopen the secret after closing it');
console.log('PASS: exact Konami sequence, uppercase A/B, repeat/modifier/input exclusions, timeout and reactivation.');
