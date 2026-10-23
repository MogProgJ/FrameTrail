// Pure editor validation/replay tests. No browser or UI automation.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),template=fs.readFileSync(path.join(root,'scripts/annotation-editor-simple.html'),'utf8');
const script=fs.readFileSync(path.join(root,'scripts/annotation-editor.js'),'utf8');
assert.match(template,/<select id="class"/);assert.doesNotMatch(template,/<datalist/);
new vm.Script(script); // Syntax-check complete editor, including UI handlers.
const workspace=process.argv[2];if(!workspace)throw Error('Pass a prepared workspace.');
const seed=JSON.parse(fs.readFileSync(path.join(workspace,'seed.json'),'utf8'));
const state=JSON.parse(fs.readFileSync(path.join(workspace,process.argv[3]||'annotations-corrected-v2.json'),'utf8'));
if(process.argv[4]){
 const page=fs.readFileSync(process.argv[4],'utf8'),blocks=[...page.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
 assert.equal(blocks.length,2);assert.deepEqual(JSON.parse(blocks[0][1]),{seed,state});
 assert.ok(blocks[1][1].replaceAll('\r\n','\n').trim()===script.replaceAll('\r\n','\n').trim(),
  'Embedded script differs from source (after normalizing Windows line endings).');new vm.Script(blocks[1][1]);
 assert.doesNotMatch(page,/__ANNOTATION_(PAYLOAD|SCRIPT)__/);assert.doesNotMatch(page,/<script[^>]+src=/);
}
const context=vm.createContext({structuredClone,document:{getElementById(id){
 if(id!=='payload')throw Error('Pure tests must not access UI.');return {textContent:JSON.stringify({seed,state})};
}}});
vm.runInContext(script.split("$('overlay').addEventListener('pointerdown'")[0]+'\nglobalThis.logic={validate,validBox,replay,validObservation,classChoices,createDraft,transact,replacementActions,equal,renderForm,updatePicker,updateButtons,searchLabels,edit,guardForm,getState:()=>clone(state)};',context);
const {validate,validBox,replay,validObservation,classChoices,createDraft,transact,replacementActions,equal}=context.logic,clone=x=>JSON.parse(JSON.stringify(x));
validate(state);assert.equal(validBox([0,0,10,10],{width:10,height:10}),true);
for(const box of [[0,0,0,10],[-1,0,10,10],[0,0,11,10],[NaN,0,10,10]])assert.equal(validBox(box,{width:10,height:10}),false);
for(const mutate of [x=>x.approved_for_training=true,x=>x.images[0].sha256='changed',
 x=>x.images[0].objects[0].box=[0,0,1,1],x=>x.events[0].seq=2,x=>x.events[0].actor='',x=>x.classes.reverse()]){
 const bad=clone(state);mutate(bad);assert.throws(()=>validate(bad));
}
const target=clone(seed),img=target.images[0],original=clone(img.objects[0]),after=clone(original);
after.box=[0,0,10,10];after.note='Boundary unit test';
const change={seq:1,at:'2026-10-04T14:00:00Z',actor:'unit-test',image_id:img.id,kind:'update',object_id:original.id,before:original,after};
replay(change,target);target.events.push(change);validate(target);
const rejected=clone(change);rejected.before=clone(after);rejected.after.status='rejected';rejected.after.note='';assert.throws(()=>replay(rejected,target));
const provenance=clone(change);provenance.before=clone(after);provenance.after.origin={kind:'manual'};assert.throws(()=>replay(provenance,target));
const manual={id:'manual-unit-test',raw_id:381,box:[0,0,10,10],status:'pending',note:'Test',origin:{kind:'manual'}};
const add={seq:2,at:change.at,actor:'unit-test',image_id:img.id,kind:'add',object_id:manual.id,before:null,after:manual};
replay(add,target);target.events.push(add);validate(target);assert.throws(()=>replay(add,target));
const draft=clone(createDraft([0,0,10,10],img));assert.deepEqual(draft,{box:[0,0,10,10]});
assert.equal(classChoices('bracelet').length,0);assert.equal(classChoices('necklace').some(x=>x.name==='Necklace'),true);
assert.equal(classChoices('bracelet','115').some(x=>x.raw_id===115),true); // Search never silently overwrites the selected class.
const observation={id:'observation-bracelet',label:'bracelet',box:[0,0,10,10],status:'confirmed',note:'',origin:{kind:'manual-observation'}};
const converted=transact(target,img.id,replacementActions(manual,observation),'human-reviewer',change.at);
validate(converted);assert.equal(converted.images[0].objects.find(x=>x.id===manual.id).status,'rejected');
assert.equal(converted.images[0].observations[0].label,'bracelet');assert.equal(converted.classes.length,601);
assert.equal(converted.images[0].objects.some(x=>x.label==='bracelet'),false);
const reversed=clone(converted);reversed.images[0].observations[0].label='evil';assert.throws(()=>validate(reversed));
for(const mutate of [x=>x.label='',x=>x.label='Clothing',x=>x.raw_id=115,x=>x.box=[0,0,0,10],x=>x.origin={kind:'publisher'},x=>x.status='approved']){
 const bad=clone(observation);mutate(bad);assert.throws(()=>validObservation(bad,img));
 const snapshot=clone(target);assert.throws(()=>transact(target,img.id,replacementActions(manual,bad),'human-reviewer',change.at));
 assert.deepEqual(target,snapshot); // A failing two-event conversion is atomic.
}
const supported={...clone(manual),id:'manual-back-to-person',status:'confirmed'};
const convertedBack=transact(converted,img.id,replacementActions(observation,supported),'human-reviewer',change.at);
validate(convertedBack);assert.equal(convertedBack.images[0].observations[0].status,'rejected');
assert.equal(convertedBack.images[0].objects.at(-1).raw_id,381);
function reorder(value){if(Array.isArray(value))return value.map(reorder);if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).reverse().map(([k,v])=>[k,reorder(v)]));return value;}
validate(reorder(converted));assert.equal(equal(converted,reorder(converted)),true);
// Minimal form stubs test code paths, not rendering, native browser controls or real pointer interaction.
function node(name='div'){
 const result={children:[],attributes:{},value:'',textContent:'',checked:false,hidden:false,disabled:false,
  classList:{remove(){},toggle(){}},replaceChildren(){this.children=[];if(name==='select')this.value='';},
  append(...items){this.children.push(...items);},setAttribute(key,value){this.attributes[key]=value;},
  getAttribute(key){return this.attributes[key];},addEventListener(){},style:{}};
 Object.defineProperty(result,'valueAsNumber',{get(){return this.value===''?NaN:Number(this.value);}});
 return result;
}
const fields=new Map(),get=id=>{if(!fields.has(id))fields.set(id,node(id==='class'?'select':'div'));return fields.get(id);};
context.document={getElementById:get,createElement:node,createElementNS:(_,name)=>node(name)};
context.crypto=require('node:crypto');context.localStorage={setItem(){}};
get('show-boxes').checked=true;get('show-model').checked=true;get('reviewer').value='form-unit-reviewer';
const l=context.logic;l.renderForm();assert.equal(get('class').value,'');assert.equal(get('reason').value,'');
assert.equal(get('box-fields').disabled,true);
vm.runInContext(`selected=image().objects[0].id;renderForm();`,context);
assert.equal(get('class').value,String(state.images[0].objects[0].raw_id));
get('class-search').value='bracelet';l.searchLabels();assert.equal(get('class').value,'');
assert.equal(get('confirm').disabled,true);assert.throws(()=>l.guardForm());
get('reason').value='Unsaved note';vm.runInContext('dirty=true;',context);assert.throws(()=>l.guardForm());
vm.runInContext('dirty=false;selected=null;draft=createDraft([0,0,10,10],image());renderForm();',context);
assert.equal(get('class').value,'');assert.equal(get('reason').value,'');assert.equal(get('confirm').disabled,true);
get('class-search').value='bracelet';l.updatePicker();assert.deepEqual(get('class').children.map(x=>x.value),['','outside']);
get('class').value='outside';get('outside-label').value='bracelet';l.updateButtons();
assert.equal(get('confirm').disabled,false);assert.equal(get('confirm').textContent,'Confirm observation');
l.edit();const formState=clone(l.getState());validate(formState);
assert.equal(formState.images[0].observations.at(-1).label,'bracelet');assert.equal(formState.images[0].observations.at(-1).note,'');
assert.equal(formState.images[0].observations.at(-1).status,'confirmed');
assert.equal(formState.images[0].objects.length,state.images[0].objects.length);
console.log('Editor syntax and pure logic/integrity tests passed; browser interaction not tested.');
