'use strict';
// The exact fitted coefficients and trees are exported by train_model.py.
// No individual records, external inference service or browser training is needed.
const ModelEngine={
 sigmoid(z){return z>=0?1/(1+Math.exp(-z)):Math.exp(z)/(1+Math.exp(z));},
 predict(model,input){
  if(input.length!==model.features.length||input.some((v,i)=>!Number.isInteger(v)||v<0||v>=model.features[i].choices.length))throw Error('Invalid model input');
  const x=new Array(model.logistic.coefficients.length).fill(0);
  model.features.forEach((f,i)=>x[f.offset+input[i]]=1);
  let raw=model.boosted.base;
  for(const t of model.boosted.trees){let node=0;while(t.left[node]!==-1)node=x[t.feature[node]]<=t.threshold[node]?t.left[node]:t.right[node];raw+=model.boosted.learning_rate*t.value[node];}
  const logit=model.logistic.intercept+model.logistic.coefficients.reduce((s,w,i)=>s+w*x[i],0);
  const cal=(z,c)=>this.sigmoid(c.slope*z+c.intercept);
  return {boosted:cal(raw,model.boosted.calibration),logistic:cal(logit,model.logistic.calibration)};
 },
 support(model,input){
  const count=model.support[input.slice(0,3).join(',')]||0;
  const rare=model.features.filter((f,i)=>(model.feature_counts[f.key][String(input[i])]||0)<model.minimum_support).map(f=>f.label);
  return {count,rare,allowed:count>=model.minimum_support&&!rare.length};
 }
};
if(typeof module!=='undefined')module.exports=ModelEngine;
if(typeof document!=='undefined'){
 let model,report,lastResult;
 const el=id=>document.getElementById(id),p=v=>(v*100).toFixed(0)+'%',num=v=>new Intl.NumberFormat('en-GB').format(v),safe=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const tab=(headers,rows)=>'<table><thead><tr>'+headers.map(h=>`<th scope="col">${safe(h)}</th>`).join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map((x,i)=>i?`<td>${safe(x)}</td>`:`<th scope="row">${safe(x)}</th>`).join('')+'</tr>').join('')+'</tbody></table>';
 function markChanged(){el('ai-results').hidden=true;el('ai-export').disabled=true;lastResult=null;el('ai-status').textContent='Scenario changed. Run AI analysis to calculate a new estimate.';}
 function run(){
  const input=model.features.map(f=>Number(el('ai-'+f.key).value));
  const support=ModelEngine.support(model,input);
  el('ai-results').hidden=false;
  if(!support.allowed){
   el('ai-result-body').innerHTML=`<h3>Not enough training support</h3><p>There are ${num(support.count)} training casualties matching this age band, motorcycle category and road setting. This prototype requires at least ${model.minimum_support}.${support.rare.length?' At least one selected category also has fewer than '+model.minimum_support+' training records: '+safe(support.rare.join(', '))+'.':''}</p><p>No probability is shown. A model can calculate a number for a poorly supported combination, but that does not make it useful.</p>`;
   el('ai-status').textContent='Analysis complete. Estimate withheld because training support is limited.';el('ai-export').disabled=true;lastResult=null;return;
  }
  const result=ModelEngine.predict(model,input);lastResult={input,result,support};
  el('ai-result-body').innerHTML=`<p class="eyebrow">ESTIMATED RECORDED KSI SHARE</p><div class="ai-estimates"><div><span>Boosted-tree AI model</span><strong>${p(result.boosted)}</strong></div><div><span>Logistic regression comparison</span><strong>${p(result.logistic)}</strong></div></div><p>Estimated probability of a <strong>fatal or serious recorded injury, conditional on being a motorcycle casualty</strong> in the model’s reporting-area cohort.</p><p>This is not the chance of crashing, an individual safety score, or the effect of changing a riding decision.</p><div class="ai-support"><strong>${num(support.count)}</strong> training casualties match the selected age band, motorcycle category and road setting. This count does not validate every combination of the other inputs.</div><details><summary>Scenario used for this result</summary><dl class="ai-scenario">${model.features.map((f,i)=>`<dt>${safe(f.label)}</dt><dd>${safe(f.choices[input[i]])}</dd>`).join('')}</dl></details>`;
  el('ai-status').textContent='Analysis complete. The trained models ran locally in your browser.';el('ai-export').disabled=false;
 }
 function renderReport(){
  const m=report.metrics,ci=report.comparison.ci95,better=ci[0]>0;
  el('ai-verdict').textContent=better?'The boosted-tree model improved on logistic regression on the 2025 test using Brier score. This is evidence of predictive value in this cohort, not proof of causation or future reliability.':ci[1]<0?'The simpler logistic regression performed slightly better than the boosted-tree model on the 2025 test. Both models have modest discrimination. This AI feature is an exploratory demonstration, not evidence that extra complexity helps.':'The 2025 test did not establish a clear Brier-score improvement over logistic regression. The AI model remains an exploratory demonstration; the simpler model is a credible alternative.';
  el('ai-model-summary').textContent=ci[1]<0?'Test finding: the simpler regression performed slightly better. Both estimates are shown for comparison.':'Research prototype: compare the AI estimate with the simpler regression and review the test results below.';
  el('ai-metrics').innerHTML=tab(['2025 test','Boosted trees','Logistic regression','Constant baseline'],[['Brier score (lower is better)',m.boosted.brier.toFixed(4),m.logistic.brier.toFixed(4),m.constant.brier.toFixed(4)],['AUC (higher is better)',m.boosted.auc.toFixed(3),m.logistic.auc.toFixed(3),m.constant.auc.toFixed(3)],['Average predicted KSI share',p(m.boosted.mean_probability),p(m.logistic.mean_probability),p(m.constant.mean_probability)],['Observed KSI share',p(report.test_observed),p(report.test_observed),p(report.test_observed)]]);
  el('ai-uncertainty').textContent=`Brier-score improvement over regression: ${report.comparison.brier_reduction.toFixed(4)}; approximate 95% paired bootstrap interval ${ci[0].toFixed(4)} to ${ci[1].toFixed(4)}. Resampling is by collision (${report.comparison.bootstrap_replicates} replicates). Positive values favour boosted trees. This interval is not uncertainty around an individual scenario’s probability.`;
  el('ai-splits').innerHTML=tab(['Purpose','Casualties','Recorded KSI','Distinct collisions'],report.splits.map(r=>[r.period,num(r.n),num(r.ksi),num(r.collisions)]));
  el('ai-cohort').textContent=`${num(report.cohort_total)} of ${num(report.all_recent_motorcycle_casualties)} recent motorcycle casualties meet the model cohort rule. ${report.eligible_forces.length} police force areas qualify. The model is not representative of all Great Britain.`;
  el('ai-forces').textContent=report.eligible_forces.join(', ')+'.';
  el('ai-calibration').innerHTML=tab(['2025 prediction band','Casualties','Mean prediction','Observed KSI'],report.calibration_bins.map((b,i)=>[`${i+1} of 5${i===0?' (lowest)':i===4?' (highest)':''}`,num(b.n),p(b.predicted),p(b.observed)]));
  const top=report.importance.slice(0,6),max=Math.max(.000001,...top.map(x=>x.brier_increase));
  el('ai-importance').innerHTML='<div class="bars">'+top.map(r=>`<div class="bar-row"><span class="bar-name">${safe(r.feature)}</span><div class="bar-track" aria-hidden="true"><div class="bar-fill" style="width:${Math.max(0,r.brier_increase)/max*100}%"></div></div><span class="bar-value">${r.brier_increase.toFixed(4)}</span></div>`).join('')+'</div>';
  el('ai-model-version').textContent=`Model ${model.version} · 120 boosted trees · trained once, not retrained by this button`;
 }
 function download(){if(!lastResult)return;const {input,result,support}=lastResult;const q=x=>'"'+String(x).replaceAll('"','""')+'"';const rows=[['Motorcycle Evidence — Dr Owen Williams'],['Model',model.version],['Target',model.target],...model.features.map((f,i)=>[f.label,f.choices[input[i]]]),['Boosted-tree probability',result.boosted],['Logistic-regression probability',result.logistic],['Training support (age/category/setting only)',support.count],['Limit','Conditional on recorded casualty in the model cohort; not crash risk or causal effect.']];const url=URL.createObjectURL(new Blob(['\ufeff'+rows.map(r=>r.map(q).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='motorcycle-ai-scenario.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 async function initAI(){try{[model,report]=await Promise.all(['ai-model','ai-report'].map(async name=>{const r=await fetch('data/'+name+'.json');if(!r.ok)throw Error('Model data unavailable');return r.json();}));el('ai-fields').innerHTML=model.features.map(f=>`<label>${safe(f.label)}<select id="ai-${f.key}">${f.choices.map((x,i)=>`<option value="${i}"${i===f.default?' selected':''}>${safe(x)}</option>`).join('')}</select></label>`).join('');renderReport();el('ai-run').disabled=false;el('ai-status').textContent='Choose a scenario, then run the trained model.';el('ai-run').addEventListener('click',run);el('ai-fields').addEventListener('change',markChanged);el('ai-reset').addEventListener('click',()=>{model.features.forEach(f=>el('ai-'+f.key).value=String(f.default));markChanged();});el('ai-export').addEventListener('click',download);}catch(e){el('ai-status').textContent='The model could not be loaded. Please reload the page. The data explorer remains available.';el('ai-run').disabled=true;console.error(e);}}
 initAI();
}
