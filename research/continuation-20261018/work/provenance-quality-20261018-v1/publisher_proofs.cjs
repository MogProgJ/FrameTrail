const fs=require('fs'),path=require('path'),{chromium}=require('C:/Users/nazee/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R=path.resolve('outputs/external-provenance-quality-20261018-v1');
(async()=>{const input=JSON.parse(fs.readFileSync(path.join(R,'publisher-image-links.json'),'utf8'));const rows=[];
for(const p of input){let items=p.images.map(i=>({url:i['data-lazy-src']||i['data-src']||i.src||'',alt:i.alt||''}));items=items.filter((i,k,a)=>i.url.startsWith('https:')&&a.findIndex(j=>j.url===i.url)===k);
 if(p.id==='satori')items=items.filter(i=>/Blue-[23]\.jpg/.test(i.url));
 if(p.id==='design-dazzle')items=items.filter(i=>i.url.includes('/2016/11/'));
 if(p.id==='zdesign')items=items.filter(i=>i.url.includes('tops-appliance-cabinet'));
 if(p.id==='thou-swell')items=items.filter(i=>/swell-[134]-683/.test(i.url));
 if(p.id==='beauparlant')items=items.filter(i=>/Hocken\d/.test(i.url));
 for(let k=0;k<items.length;k++)rows.push({id:p.id+'-'+(k+1),page:p.url,...items[k]});}
fs.writeFileSync(path.join(R,'publisher-proof-index.json'),JSON.stringify(rows,null,2));
const browser=await chromium.launch({headless:true,executablePath:'C:/Users/nazee/AppData/Local/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-win64/chrome-headless-shell.exe'});
try{const page=await browser.newPage({viewport:{width:1200,height:900}});for(let start=0;start<rows.length;start+=9){const subset=rows.slice(start,start+9);await page.setContent('<style>body{background:#132031;color:white;font:16px Arial}main{display:grid;grid-template-columns:repeat(3,390px)}img{width:380px;height:350px;object-fit:contain}article{height:390px}</style><main>'+subset.map(i=>`<article>${i.id}<br><img src="${i.url.replaceAll('&','&amp;')}"></article>`).join('')+'</main>',{waitUntil:'load',timeout:50000});for(const r of await page.locator('img').evaluateAll(imgs=>imgs.map(i=>({url:i.src,loaded:i.complete&&i.naturalWidth>0})))){const item=rows.find(i=>i.url===r.url);if(item)item.loaded=r.loaded;}await page.screenshot({path:path.join(R,'proofs',`publisher-${start/9+1}.png`),fullPage:true});}fs.writeFileSync(path.join(R,'publisher-proof-index.json'),JSON.stringify(rows,null,2));console.log(JSON.stringify({images:rows.length,loaded:rows.filter(i=>i.loaded).length}));}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1});
