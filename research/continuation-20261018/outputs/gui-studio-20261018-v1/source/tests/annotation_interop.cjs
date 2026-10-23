// Pure JS fixture generator for Python/JavaScript correction-history interoperability.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const seed=JSON.parse(fs.readFileSync(0,'utf8'));
const context=vm.createContext({structuredClone,document:{getElementById(id){
 if(id!=='payload')throw Error('Pure test cannot access UI.');return {textContent:JSON.stringify({seed,state:seed})};
}}});
const script=fs.readFileSync(path.resolve(__dirname,'../scripts/annotation-editor.js'),'utf8');
vm.runInContext(script.split("$('overlay').addEventListener('pointerdown'")[0]+'\nglobalThis.logic={transact,replacementActions};',context);
const image=seed.images[0],obj=image.objects[0];
const observation={id:'observation-js-bracelet',label:'bracelet',box:[1,2,10,20],status:'confirmed',note:'JS fixture',origin:{kind:'manual-observation'}};
const {transact,replacementActions}=context.logic;
const state=transact(seed,image.id,replacementActions(obj,observation),'human-reviewer','2026-10-04T15:00:00Z');
process.stdout.write(JSON.stringify(state));
