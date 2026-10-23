// Pure RF editor logic/form-stub tests; no claim of actual browser rendering or pointer verification.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),workspace=process.argv[2];
const payload=workspace ? {seed:JSON.parse(fs.readFileSync(path.join(workspace,'seed.json'),'utf8')),
 state:JSON.parse(fs.readFileSync(path.join(workspace,process.argv[4]||'annotations.json'),'utf8')),
 proposals:JSON.parse(fs.readFileSync(path.join(workspace,'rf-proposals.json'),'utf8'))} : JSON.parse(fs.readFileSync(0,'utf8'));
const script=fs.readFileSync(path.join(root,'scripts/annotation-editor.js'),'utf8');new vm.Script(script);
if(workspace && process.argv[3]){
 const page=fs.readFileSync(process.argv[3],'utf8'),blocks=[...page.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
 assert.equal(blocks.length,2);assert.deepEqual(JSON.parse(blocks[0][1]),payload);
 assert.equal(blocks[1][1].replaceAll('\r\n','\n').trim(),script.replaceAll('\r\n','\n').trim());
 assert.doesNotMatch(page,/<script[^>]+src=/);assert.match(page,/id="rf-list"/);assert.match(page,/id="rf-use-match"/);
}
const context=vm.createContext({structuredClone,document:{getElementById(id){
 if(id!=='payload')throw Error('Unexpected pure-logic UI access');return {textContent:JSON.stringify(payload)};
}}});
vm.runInContext(script.split("$('overlay').addEventListener('pointerdown'")[0]+
 '\nglobalThis.logic={validate,transact,proposalObject,proposalOverlap,selectProposal,proposalLinkTarget,proposalStatus,edit,useMatchingSaved,rejectSelected,fitImageSize,fitPhoto,point,showBoxList,guardForm,getState:()=>clone(state)};',context);
const l=context.logic,clone=x=>JSON.parse(JSON.stringify(x));l.validate(payload.state);
for(let n=0;n<payload.state.images.length;n++)for(const obj of payload.state.images[n].objects.concat(payload.state.images[n].observations||[]))if(obj.linked_to){
 vm.runInContext(`index=${n};`,context);
 const target=payload.state.images[n].objects.concat(payload.state.images[n].observations||[]).find(x=>x.id===obj.linked_to);
 assert.equal(l.proposalLinkTarget(payload.state,payload.state.images[n],obj).id,target.id);
 assert.match(l.proposalStatus(obj),/applied to saved box/);assert.equal(obj.status,'rejected');
}
vm.runInContext('index=0;',context);
const img=payload.state.images[0],supported=payload.proposals.images[0].candidates.find(x=>x.raw_id!==null);
const original=clone(l.proposalObject(img.id,supported.id));assert.equal(original.status,'pending');
assert.equal(original.origin.model,'RF-DETR Small');
const action={kind:'proposal-add',id:original.id,after:original};
const once=l.transact(payload.state,img.id,[action],'human-reviewer','2026-10-07T18:00:00Z');
assert.throws(()=>l.transact(once,img.id,[action],'human-reviewer','2026-10-07T18:00:01Z'));
for(const fields of [{status:'confirmed'},{raw_id:57},{box:[0,0,1,1]}])
 assert.throws(()=>l.transact(payload.state,img.id,[{...action,after:{...original,...fields}}],'human-reviewer','2026-10-07T18:00:00Z'));
// Importing an older state must remain valid with the same immutable seed; unlogged edits cannot pass.
l.validate(payload.state);const bad=clone(payload.state);bad.approved_for_training=true;assert.throws(()=>l.validate(bad));
function node(name='div'){
 const result={children:[],attributes:{},value:'',textContent:'',checked:false,hidden:false,disabled:false,
  classList:{remove(){},toggle(){}},replaceChildren(){this.children=[];if(name==='select')this.value='';},
  append(...items){this.children.push(...items);if(name==='select' && !this.value && items[0])this.value=items[0].value;},
  setAttribute(k,v){this.attributes[k]=v;},getAttribute(k){return this.attributes[k];},addEventListener(){},focus(){this.focused=true;},style:{}};
 Object.defineProperty(result,'valueAsNumber',{get(){return this.value===''?NaN:Number(this.value);}});return result;
}
const fields=new Map(),get=id=>{if(!fields.has(id))fields.set(id,node(['class','rf-match'].includes(id)?'select':'div'));return fields.get(id);};
context.document={getElementById:get,createElement:node,createElementNS:(_,name)=>node(name)};
context.crypto=require('node:crypto');context.localStorage={setItem(){}};
get('show-boxes').checked=true;get('show-model').checked=true;get('show-rf').checked=true;get('reviewer').value='human-reviewer';
l.showBoxList('rf');l.selectProposal(supported.id);assert.equal(get('class').value,String(supported.raw_id));assert.equal(get('rf-panel').hidden,false);
if(l.proposalOverlap(original).length){
 assert.throws(()=>l.edit('confirmed'));assert.ok(get('edit-status').textContent);
 const target=get('rf-match').value;assert.ok(target);l.useMatchingSaved(target);
 const updated=clone(l.getState());l.validate(updated);
 assert.equal(updated.images[0].objects.length,img.objects.length+1); // preserved rejected RF record, not an extra active target
 assert.equal(updated.images[0].objects.find(x=>x.id===original.id).status,'rejected');
 assert.equal(updated.images[0].objects.find(x=>x.id===target).status,'confirmed');
 assert.equal(updated.images[0].objects.find(x=>x.id===original.id).linked_to,target);
 assert.match(l.proposalStatus(updated.images[0].objects.find(x=>x.id===original.id)),/applied to saved box.*confirmed/);
 l.selectProposal(supported.id);vm.runInContext('globalThis.selectedAfterLink=selected;',context);assert.equal(context.selectedAfterLink,target);
 const linked=updated.images[0].objects.find(x=>x.id===original.id);
 assert.throws(()=>l.transact(updated,img.id,[{kind:'update',id:linked.id,after:{...linked,status:'confirmed'}}],'human-reviewer','2026-10-08T20:00:00Z'));
}else{
 l.edit('confirmed');assert.equal(clone(l.getState()).images[0].objects.at(-1).status,'confirmed');
}
const outsideRow=payload.proposals.images.find(x=>x.candidates.some(p=>p.raw_id===null));
if(outsideRow){
 vm.runInContext(`index=${payload.state.images.findIndex(x=>x.id===outsideRow.image_id)};`,context);
 const outside=outsideRow.candidates.find(x=>x.raw_id===null);l.selectProposal(outside.id);
 assert.equal(get('class').value,'outside');assert.equal(get('outside-label').value,outside.name);
 get('rf-distinct').checked=true;l.edit();const result=clone(l.getState());l.validate(result);
 assert.equal(result.images.find(x=>x.id===outsideRow.image_id).observations.at(-1).origin.kind,'model-observation');
 assert.equal(result.images.find(x=>x.id===outsideRow.image_id).observations.at(-1).status,'confirmed');
}
// Removal has its own visible input; notes/provenance are not mistaken for a reason.
const finalState=clone(l.getState());
vm.runInContext(`state=${JSON.stringify(payload.state)};index=0;selected=image().objects.find(x=>x.status!=='rejected' && !proposalLinkTarget(state,image(),x)).id;draft=null;dirty=false;render();`,context);
const beforeRemoval=clone(l.getState());
assert.throws(()=>l.rejectSelected('   '),/reason/);assert.equal(get('reject-reason').focused,true);
assert.equal(get('reject-reason').getAttribute('aria-invalid'),'true');assert.deepEqual(clone(l.getState()),beforeRemoval);
get('reject-reason').value='Wrong boundary';assert.throws(()=>l.guardForm());assert.throws(()=>l.edit(),/removal reason/);
vm.runInContext('dirty=true;',context);assert.throws(()=>l.rejectSelected('Wrong boundary'),/other box edits/);
assert.deepEqual(clone(l.getState()),beforeRemoval);vm.runInContext('dirty=false;',context);
l.rejectSelected('  Wrong boundary  ');const removed=clone(l.getState());l.validate(removed);
assert.deepEqual(removed.events.slice(0,beforeRemoval.events.length),beforeRemoval.events);
assert.equal(removed.events.at(-1).after.status,'rejected');assert.equal(removed.events.at(-1).after.note,'Wrong boundary');
assert.deepEqual(removed.events.at(-1).before,removed.images[0].objects.find(x=>x.id===removed.events.at(-1).object_id) && beforeRemoval.images[0].objects.find(x=>x.id===removed.events.at(-1).object_id));
assert.equal(get('reject-reason').value,'');
// RF removal records original catalogue prediction first, then the explicit rejection.
vm.runInContext(`state=${JSON.stringify(payload.state)};index=0;selected=null;draft=null;dirty=false;render();`,context);
l.selectProposal(supported.id);l.rejectSelected('Duplicate already represented');
const rejectedRf=clone(l.getState());l.validate(rejectedRf);
const lastTwo=rejectedRf.events.slice(-2);assert.equal(lastTwo[0].kind,'proposal-add');assert.equal(lastTwo[1].after.status,'rejected');
assert.deepEqual(lastTwo[0].after,original);assert.equal(lastTwo[1].after.note,'Duplicate already represented');
// Bounded frame preserves aspect ratio and overlay coordinate mapping, for portrait/landscape and resize.
for(const [w,h,fw,fh] of [[683,1024,1200,600],[1024,683,500,800],[1000,1000,400,300]]){
 const size=l.fitImageSize(w,h,fw,fh);assert.ok(size.width<=fw+1e-8 && size.height<=fh+1e-8);
 assert.ok(Math.abs(size.width/size.height-w/h)<1e-9);
 get('image-frame').clientWidth=fw;get('image-frame').clientHeight=fh;l.fitPhoto();
 const img=l.getState().images[0],width=parseFloat(get('stage').style.width),height=parseFloat(get('stage').style.height);
 get('overlay').getBoundingClientRect=()=>({left:30,top:50,width,height});
 assert.deepEqual(clone(l.point({clientX:30+width/2,clientY:50+height/2})),[img.width/2,img.height/2]);
}
assert.equal(l.fitImageSize(0,100,300,300),null);assert.equal(l.fitImageSize(100,100,0,300),null);
l.showBoxList('rf');assert.equal(get('rf-panel').hidden,false);assert.equal(get('saved-panel').hidden,true);
assert.equal(get('rf-tab').getAttribute('aria-selected'),'true');
l.showBoxList('saved');assert.equal(get('rf-panel').hidden,true);assert.equal(get('saved-panel').hidden,false);
vm.runInContext(`state=${JSON.stringify(finalState)};`,context);
if(workspace)console.log('RF editor payload, history, removal, frame sizing, tabs, duplicate-resolution and form-stub tests passed; browser interaction not tested.');
else process.stdout.write(JSON.stringify(clone(l.getState())));
