const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),vm=require('node:vm');
const root=path.join(__dirname,'dist');
const engine=require('./dist/ai.js'),model=JSON.parse(fs.readFileSync(path.join(root,'data/ai-model.json'))),fixtures=JSON.parse(fs.readFileSync(path.join(__dirname,'ai-verification.json')));
let maxError=0;
for(const row of fixtures){const pred=engine.predict(model,row.input);for(const key of ['boosted','logistic']){const error=Math.abs(pred[key]-row[key]);maxError=Math.max(maxError,error);assert.ok(error<1e-10,`Python/JS disagreement ${error}`);}}
assert.throws(()=>engine.predict(model,[]));assert.throws(()=>engine.predict(model,new Array(10).fill(-1)));assert.throws(()=>engine.predict(model,new Array(10).fill(NaN)));
const defaultInput=model.features.map(f=>f.default);assert.ok(engine.support(model,defaultInput).allowed);
const rareInput=[0,4,1,...defaultInput.slice(3)];assert.equal(engine.support(model,rareInput).allowed,false);
// Handler tests with a DOM stub. These do not replace visual browser checks.
let nodes={},downloaded=false,failure=null;
function node(tag,id){return nodes[id]??=( {tag,value:'',hidden:false,disabled:false,textContent:'',events:{},_html:'',addEventListener(k,f){this.events[k]=f},set innerHTML(v){this._html=v;parse(v);},get innerHTML(){return this._html;}});}
function parse(html){for(const m of html.matchAll(/<(\w+)[^>]*\bid="([^"]+)"[^>]*>/g))node(m[1],m[2]);for(const m of html.matchAll(/<select id="([^"]+)">([\s\S]*?)<\/select>/g)){const chosen=[...m[2].matchAll(/<option value="([^"]+)"([^>]*)>/g)];if(chosen.length)nodes[m[1]].value=(chosen.find(x=>x[2].includes('selected'))||chosen[0])[1];}}
parse(fs.readFileSync(path.join(root,'index.html'),'utf8'));
const ctx=vm.createContext({console:{error:e=>failure=e},Intl,Map,Number,String,Math,Array,Object,Promise,Error,Blob,setTimeout,URL:{createObjectURL:()=> 'blob:test',revokeObjectURL:()=>{}},document:{getElementById:id=>{assert.ok(nodes[id],`Missing ${id}`);return nodes[id]},createElement:()=>({click(){downloaded=this.download;}})},fetch:async url=>({ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(root,url),'utf8'))})});
vm.runInContext(fs.readFileSync(path.join(root,'ai.js'),'utf8'),ctx);
setImmediate(()=>{
 assert.equal(failure,null);assert.equal(nodes['ai-run'].disabled,false);assert.ok(nodes['ai-verdict'].textContent.includes('regression performed slightly better'));
 nodes['ai-run'].events.click();assert.ok(nodes['ai-result-body'].innerHTML.includes('Estimated probability'));assert.equal(nodes['ai-export'].disabled,false);assert.ok(nodes['ai-status'].textContent.includes('locally in your browser'));
 nodes['ai-export'].events.click();assert.equal(downloaded,'motorcycle-ai-scenario.csv');
 nodes['ai-fields'].events.change();assert.equal(nodes['ai-results'].hidden,true);assert.equal(nodes['ai-export'].disabled,true);
 nodes['ai-age'].value='0';nodes['ai-bike'].value='4';nodes['ai-area'].value='1';nodes['ai-run'].events.click();assert.ok(nodes['ai-result-body'].innerHTML.includes('Not enough training support'));assert.equal(nodes['ai-export'].disabled,true);
 nodes['ai-reset'].events.click();model.features.forEach(f=>assert.equal(nodes['ai-'+f.key].value,String(f.default)));
 console.log(`PASS: 100 Python/JavaScript prediction pairs, max error ${maxError}; input validation; support gate; real inference handler; stale-result clearing; reset; export; honest model comparison. Visual browser checks not performed.`);
});
