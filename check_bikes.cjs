const fs=require('node:fs'),assert=require('node:assert/strict'),vm=require('node:vm');
const E=require('./dist/bikes.js'),data=JSON.parse(fs.readFileSync('dist/data/bikes.json')),rows=E.decode(data);
const base={from:2020,to:2025};
assert.deepEqual(E.sum(rows).n,94770);assert.equal(E.sum(rows).ksi,32117);
assert.equal(E.sum(E.filter(rows,{...base,category:'>500cc'})).ksi,13445);
assert.equal(E.sum(E.filter(rows,{...base,make:'HONDA',category:'51–125cc'})).ksi,3266);
// Includes CBR (119 KSI) plus separately recorded CBR 650 FA (4 KSI).
assert.equal(E.sum(E.filter(rows,{...base,make:'HONDA',search:'HONDA CBR',cc:'649'})).ksi,123);
assert.equal(E.sum(E.filter(rows,{...base,band:'501–750cc'})).ksi,5148);
assert.equal(E.sum(E.filter(rows,{...base,from:2025,to:2025})).ksi,6002);
assert.equal(E.sum(E.filter(rows,{...base,role:'1'})).n+E.sum(E.filter(rows,{...base,role:'2'})).n,94770);
assert.equal(E.filter(rows,{...base,search:'no such model'}).length,0);
assert.ok(E.rank(rows,'share').every(r=>r.n>=50));
assert.equal(E.sum(E.group(rows,['style'])).ksi,32117);
assert.equal(E.sum(E.group(rows,['category','age'])).ksi,32117);
assert.equal(E.sum(E.filter(rows,{...base,role:'1',age:'16–19',category:'51–125cc'})).ksi,2610);
assert.equal(E.sum(E.filter(rows,{...base,role:'1',age:'55–64',category:'>500cc'})).ksi,2948);
assert.ok(rows.filter(r=>['BMW R SERIES','HONDA CB','HONDA NC750','BMW S 1000'].includes(r.model)).every(r=>r.style==='Unclassified / ambiguous'));
assert.ok(E.csv(E.rank(rows,'ksi'),'2020–2025',false).includes('Unavailable when 2020 included'));
// DOM handler checks, not a substitute for browser rendering.
const nodes={};let fail=null,download=null;
function node(id){return nodes[id]??={value:'',disabled:true,hidden:false,innerHTML:'',textContent:'',events:{},addEventListener(e,f){this.events[e]=f;},scrollIntoView(){}};}
const html=fs.readFileSync('dist/bikes.html','utf8');for(const m of html.matchAll(/\bid="([^"]+)"/g))node(m[1]);
const presets=[...html.matchAll(/data-preset="([^"]+)"/g)].map(m=>({...node('preset-'+m[1]),dataset:{preset:m[1]}}));
const ctx=vm.createContext({Intl,Map,Set,Object,String,Number,Math,Array,Promise,Error,Blob,setTimeout,console:{error:e=>fail=e},URL:{createObjectURL:()=> 'blob:csv',revokeObjectURL(){}},document:{getElementById:id=>{assert.ok(nodes[id],id);return nodes[id];},querySelectorAll:()=>presets,createElement:()=>({click(){download=this.download;}})},fetch:async()=>({ok:true,json:async()=>data})});
vm.runInContext(fs.readFileSync('dist/bikes.js','utf8'),ctx);
setImmediate(()=>{
 assert.equal(fail,null);assert.equal(nodes['b-reset'].disabled,false);assert.equal(nodes['b-role'].value,'1');assert.equal(nodes['b-category'].value,'all');
 assert.ok(nodes['b-matrix'].innerHTML.includes('2,610'));assert.ok(nodes['b-matrix'].innerHTML.includes('2,948'));
 nodes['b-age'].value='16–19';nodes['b-filters'].events.input();assert.ok(nodes['b-kpis'].innerHTML.includes('4,120'));
 nodes['b-category'].value='51–125cc';nodes['b-filters'].events.input();assert.ok(nodes['b-kpis'].innerHTML.includes('2,610'));
 nodes['b-cross'].value='style';nodes['b-cross'].events.change();assert.ok(nodes['b-matrix'].innerHTML.includes('Unclassified'));
 nodes['b-age-export'].events.click();assert.equal(download,'motorcycles-by-age.csv');
 nodes['b-reset'].events.click();nodes['b-make'].value='HONDA';nodes['b-search'].value='HONDA CBR';nodes['b-cc'].value='649';nodes['b-filters'].events.input();
 nodes['b-table'].events.click({target:{closest:()=>({dataset:{row:'0'}})}});assert.equal(nodes['b-detail'].hidden,false);assert.ok(nodes['b-detail-table'].innerHTML.includes('649'));
 nodes['b-export'].events.click();assert.equal(download,'motorcycles-and-age-model-comparison.csv');
 nodes['b-reset'].events.click();nodes['b-metric'].value='adj';nodes['b-filters'].events.input();assert.equal(nodes['b-from'].value,'2021');assert.ok(nodes['b-status'].textContent.includes('moved'));
 nodes['b-to'].value='2020';nodes['b-filters'].events.input();assert.equal(nodes['b-to'].value,'2021');
 nodes['b-role'].value='2';nodes['b-filters'].events.input();assert.ok(nodes['b-age-note'].textContent.includes('passenger'));
 nodes['b-metric'].value='share';nodes['b-filters'].events.input();assert.ok(nodes['b-matrix'].innerHTML.includes('Withheld'));
 nodes['b-search'].value='no such model';nodes['b-filters'].events.input();assert.equal(nodes['b-export'].disabled,true);assert.equal(nodes['b-age-export'].disabled,true);assert.ok(nodes['b-status'].textContent.includes('No matching'));
 presets.find(p=>p.dataset.preset==='all').events.click();assert.equal(nodes['b-category'].value,'all');assert.equal(nodes['b-age'].value,'all');
 console.log('PASS: national totals; all-capacity/rider defaults; age filters; matrix; type cross-tab; age CSV; passenger labels; small-cell safeguards; model drilldown; adjusted-year safeguard; empty state. Visual browser verification not performed.');
});
