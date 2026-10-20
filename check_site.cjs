// Calculation and event-handler checks with a minimal DOM stub. Not browser/layout QA.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.join(__dirname,'dist'),html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const nodes={};
for(const m of html.matchAll(/<(\w+)[^>]*\bid="([^"]+)"[^>]*>/g))nodes[m[2]]={tag:m[1],value:'',hidden:false,events:{},textContent:'',_html:'',addEventListener(k,f){this.events[k]=f;},set innerHTML(v){this._html=v;if(this.tag==='select'){this.value=String(v.match(/<option value="([^"]*)"/)?.[1]??'');}},get innerHTML(){return this._html;}};
nodes.metric.value='fatal';nodes['history-metric'].value='fatal';
let failure=null,downloadURL=null;
const ctx=vm.createContext({console:{log:console.log,error:e=>{failure=e;}},Intl,Map,Set,Number,String,Math,Array,Object,Promise,Error,Blob,setTimeout,location:{hash:''},URL:{createObjectURL:()=> 'blob:test',revokeObjectURL:()=>{}},window:{addEventListener:()=>{}},document:{getElementById:id=>{assert.ok(nodes[id],`Unknown element ${id}`);return nodes[id];},querySelectorAll:()=>[],createElement:()=>({click(){downloadURL=this.download;}})},fetch:async url=>({ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(root,url),'utf8'))})});
vm.runInContext(fs.readFileSync(path.join(root,'app.js'),'utf8'),ctx);
setImmediate(()=>{
 assert.equal(failure,null,'Initialization error');assert.equal(ctx.window.analysisReady,true);
 const annual=JSON.parse(fs.readFileSync(path.join(root,'data/annual.json')));
 const results=()=>JSON.parse(vm.runInContext('JSON.stringify(summary)',ctx));
 assert.deepEqual(results().map(x=>x.total),annual.map(x=>x.casualties));
 assert.deepEqual(results().map(x=>x.fatal),annual.map(x=>x.fatal));
 assert.ok(nodes.kpis.innerHTML.includes('81,166'));
 nodes.from.value='2025';nodes.to.value='2025';nodes.role.value='0';ctx.render();
 assert.equal(results()[0].total,14903);assert.equal(results()[0].fatal,372);
 nodes.role.value='1';ctx.render();assert.equal(results()[0].total,544);assert.equal(results()[0].fatal,14);
 // Age and category cross-filter, independently checked from original casualty CSV.
 nodes.role.value='all';nodes.age.value='1';nodes.bike.value='1';ctx.render();
 const check=JSON.parse(fs.readFileSync(path.join(__dirname,'verification.json')));
 assert.equal(results()[0].total,check.age16_19_125_total);assert.equal(results()[0].fatal,check.age16_19_125_fatal);
 for(const metric of ['total','fatal','adjksi','rawksi']){nodes.metric.value=metric;ctx.render();assert.ok(!nodes.trend.innerHTML.includes('NaN'));assert.ok(!nodes['bike-chart'].innerHTML.includes('NaN'));}
 nodes.reset.events.click();assert.equal(results().length,5);assert.equal(results().reduce((s,x)=>s+x.total,0),81166);
 nodes.from.value='2025';nodes.to.value='2021';ctx.render();assert.equal(nodes.to.value,'2025');
 nodes['history-metric'].value='fatal_rate';ctx.renderHistory();assert.ok(nodes['history-chart'].innerHTML.includes('per billion'));assert.ok(nodes['history-table'].innerHTML.includes('127.8'));
 nodes['history-modern'].events.click();assert.equal(nodes['history-from'].value,'2005');
 nodes.download.events.click();assert.equal(downloadURL,'motorcycle-summary-2025-2025.csv');
 assert.ok(nodes['findings-content'].innerHTML.includes('13.5%'));
 const uncertainty=JSON.parse(fs.readFileSync(path.join(root,'data/uncertainty.json'),'utf8'));
 assert.equal(uncertainty.rows.length,9);
 assert.deepEqual(uncertainty.rows.filter(r=>r.p<.05).map(r=>r.age),['35–44','65+']);
 assert.ok(uncertainty.rows.every(r=>r.p_holm>=r.p&&r.p_holm<=1));
 assert.ok(uncertainty.rows.every(r=>r.p_holm>=.05));
 assert.ok(nodes['change-table'].innerHTML.includes('0.264'));
 assert.ok(nodes['change-table'].innerHTML.includes('0.139'));
 assert.ok(nodes['uncertainty-summary'].textContent.includes('No age group'));
 const guide=fs.readFileSync(path.join(root,'evidence.html'),'utf8');
 assert.ok(guide.includes('No request has been submitted'));
 assert.ok(!guide.includes('<script src="bikes.js"'));
 for(const p of [...guide.matchAll(/(?:src|href)="([^"#]+)"/g)].map(x=>x[1]).filter(x=>!x.startsWith('http')))assert.ok(fs.existsSync(path.join(root,p.split('#')[0])),`Broken guide link ${p}`);
 assert.ok(nodes.audit.innerHTML.includes('Reconciled'));
 for(const p of [...html.matchAll(/(?:src|href)="([^"#]+)"/g)].map(x=>x[1]).filter(x=>!x.startsWith('http')))assert.ok(fs.existsSync(path.join(root,p)),`Broken local link ${p}`);
 console.log('PASS: initialization; annual controls; rider/passenger filters; independent age/capacity cross-filter; four measures; reset; year boundary; historical rate view; CSV handler; local links. Browser visual verification remains unavailable.');
});
