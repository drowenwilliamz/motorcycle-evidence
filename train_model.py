"""Frozen research model: 2021–23 train, 2024 probability calibration, 2025 test.
No test outcomes enter training, calibration, importance or support calculations.
"""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'ml-dependencies'))
import numpy as np,pandas as pd,sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score,brier_score_loss,log_loss
SOURCE=ROOT.parents[1]/'Road Safety'/'STATS19 2025 release'
OUT=ROOT/'dist'/'data'
SEED=14026
definitions=[
 ('age','Casualty age',['Under 16','16–19','20–24','25–34','35–44','45–54','55–64','65+','Unknown'],3),
 ('bike','Motorcycle category',['50cc and under','125cc category','Over 125–500cc','Over 500cc','Electric motorcycle','Unknown capacity'],1),
 ('area','Road setting',['Urban','Rural','Unknown'],0),
 ('road','Road type',['Single carriageway','Dual carriageway','Roundabout','One-way / slip road','Unknown'],0),
 ('speed','Posted speed limit',['20 mph','30 mph','40 mph','50 mph','60 mph','70 mph','Unknown'],1),
 ('junction','Junction context',['Away from junction','At / near junction','Unknown'],1),
 ('light','Lighting',['Daylight','Darkness, street lights lit','Darkness, unlit / no lights','Darkness, lighting unknown','Unknown'],0),
 ('weather','Weather',['Fine, no high winds','Rain, no high winds','High winds','Snow','Fog / mist','Other / unknown'],0),
 ('surface','Road surface',['Dry','Wet / damp','Snow, ice or flood','Unknown'],0),
 ('role','Road user',['Rider','Passenger','Unknown'],0)]
frames=[]
for year in range(2021,2026):
 c=pd.read_csv(SOURCE/f'dft-road-casualty-statistics-casualty-{year}.csv',dtype={'collision_index':'string'},usecols=['collision_index','casualty_reference','casualty_type','age_of_casualty','casualty_class','casualty_severity','casualty_injury_based'])
 c=c[c.casualty_type.isin([2,3,4,5,23,97])].copy()
 a=pd.read_csv(SOURCE/f'dft-road-casualty-statistics-collision-{year}.csv',dtype={'collision_index':'string'},usecols=['collision_index','police_force','urban_or_rural_area','road_type','speed_limit','junction_detail_historic','junction_detail','light_conditions','weather_conditions','road_surface_conditions'])
 assert not a.collision_index.duplicated().any()
 c=c.merge(a,on='collision_index',how='left',validate='many_to_one',indicator=True)
 assert c._merge.eq('both').all()
 c['year']=year;frames.append(c)
d=pd.concat(frames,ignore_index=True)
# Establish eligibility solely from training-period reporting flags, not outcomes.
stats=d[d.year<=2023].groupby(['police_force','year']).casualty_injury_based.agg(['mean','size'])
eligible=[]
for f,g in stats.groupby(level=0):
 if len(g)==3 and (g['mean']>=.95).all() and (g['size']>=20).all():eligible.append(int(f))
cohort=d[d.police_force.isin(eligible)&d.casualty_injury_based.eq(1)].copy()
cohort['age']=pd.cut(cohort.age_of_casualty,[-np.inf,-.1,15,19,24,34,44,54,64,np.inf],labels=[8,0,1,2,3,4,5,6,7]).astype(int)
def mapped(col,mapping,fallback):return cohort[col].map(mapping).fillna(fallback).astype(int)
cohort['bike']=mapped('casualty_type',{2:0,3:1,4:2,5:3,23:4,97:5},5)
cohort['area']=mapped('urban_or_rural_area',{1:0,2:1},2)
cohort['road']=mapped('road_type',{6:0,3:1,1:2,2:3,7:3,12:3},4)
cohort['speed']=mapped('speed_limit',{20:0,30:1,40:2,50:3,60:4,70:5},6)
j=cohort.junction_detail_historic.where(cohort.junction_detail_historic.isin([0,1,2,3,5,6,7,8,9]),cohort.junction_detail)
cohort['junction']=np.select([j.eq(0),j.isin([1,2,3,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19])],[0,1],default=2)
cohort['light']=mapped('light_conditions',{1:0,4:1,5:2,6:2,7:3},4)
cohort['weather']=mapped('weather_conditions',{1:0,2:1,4:2,5:2,3:3,6:3,7:4},5)
cohort['surface']=mapped('road_surface_conditions',{1:0,2:1,3:2,4:2,5:2},3)
cohort['role']=mapped('casualty_class',{1:0,2:1},2)
features=[];offset=0
for key,label,choices,default in definitions:
 features.append({'key':key,'label':label,'choices':choices,'default':default,'offset':offset});offset+=len(choices)
def encode(frame):
 return np.concatenate([np.eye(len(f['choices']),dtype=np.float64)[frame[f['key']].to_numpy()] for f in features],axis=1)
train=cohort[cohort.year<=2023];cal=cohort[cohort.year==2024];test=cohort[cohort.year==2025]
assert not set(train.collision_index)&set(cal.collision_index)
assert not set(train.collision_index)&set(test.collision_index)
assert not set(cal.collision_index)&set(test.collision_index)
X,Xc,Xt=map(encode,[train,cal,test])
y,yc,yt=[x.casualty_severity.le(2).astype(int).to_numpy() for x in [train,cal,test]]
print('Split counts',len(y),len(yc),len(yt),'eligible forces',len(eligible),flush=True)
lr=LogisticRegression(C=1.0,max_iter=1000,solver='lbfgs',random_state=SEED).fit(X,y)
gb=GradientBoostingClassifier(n_estimators=120,learning_rate=.05,max_depth=2,min_samples_leaf=100,subsample=.8,random_state=SEED).fit(X,y)
def calibrate(model):
 z=model.decision_function(Xc).reshape(-1,1)
 return LogisticRegression(C=1e6,solver='lbfgs',max_iter=1000).fit(z,yc)
lrc,gbc=calibrate(lr),calibrate(gb)
def predict(model,calibrator,x):return calibrator.predict_proba(model.decision_function(x).reshape(-1,1))[:,1]
pl,pg=predict(lr,lrc,Xt),predict(gb,gbc,Xt)
def score(p):return {'auc':float(roc_auc_score(yt,p)),'brier':float(brier_score_loss(yt,p)),'log_loss':float(log_loss(yt,p)),'mean_probability':float(np.mean(p))}
metrics={'logistic':score(pl),'boosted':score(pg),'constant':score(np.full(len(yt),yc.mean()))}
# Paired cluster bootstrap: collision, rather than individual casualty, is sampling unit.
groups=pd.factorize(test.collision_index)[0];ng=groups.max()+1
sizes=np.bincount(groups);lossdiff=np.bincount(groups,weights=(yt-pl)**2-(yt-pg)**2)
rng=np.random.default_rng(SEED);boot=[]
for _ in range(600):
 ix=rng.integers(0,ng,ng);boot.append(float(lossdiff[ix].sum()/sizes[ix].sum()))
improvement={'brier_reduction':metrics['logistic']['brier']-metrics['boosted']['brier'],'ci95':[float(x) for x in np.quantile(boot,[.025,.975])],'bootstrap_replicates':600,'unit':'collision'}
# Explain on calibration data only. Not causal importance or held-out tuning.
pc=predict(gb,gbc,Xc);base=brier_score_loss(yc,pc);importance=[]
for f in features:
 losses=[];start=f['offset'];end=start+len(f['choices'])
 for _ in range(5):
  xp=Xc.copy();xp[:,start:end]=xp[rng.permutation(len(xp)),start:end]
  losses.append(float(brier_score_loss(yc,predict(gb,gbc,xp))-base))
 importance.append({'feature':f['label'],'brier_increase':float(np.mean(losses)),'repeat_sd':float(np.std(losses))})
importance.sort(key=lambda x:x['brier_increase'],reverse=True)
bins=[]
for ix in np.array_split(np.argsort(pg),5):bins.append({'n':len(ix),'predicted':float(pg[ix].mean()),'observed':float(yt[ix].mean())})
support={','.join(map(str,k)):int(n) for k,n in train.groupby(['age','bike','area']).size().items()}
freq={f['key']:{str(k):int(v) for k,v in train[f['key']].value_counts().items()} for f in features}
base_raw=float(gb._raw_predict_init(X[:1])[0,0])
def tree(t):
 return {'left':t.children_left.tolist(),'right':t.children_right.tolist(),'feature':t.feature.tolist(),'threshold':t.threshold.tolist(),'value':t.value[:,0,0].tolist()}
def calibration(m):return {'slope':float(m.coef_[0,0]),'intercept':float(m.intercept_[0])}
model={'version':'2026-10-14-v1','features':features,'target':'Recorded KSI among motorcycle casualties in established injury-based reporting areas','boosted':{'base':base_raw,'learning_rate':gb.learning_rate,'trees':[tree(e[0].tree_) for e in gb.estimators_],'calibration':calibration(gbc)},'logistic':{'intercept':float(lr.intercept_[0]),'coefficients':lr.coef_[0].tolist(),'calibration':calibration(lrc)},'support':support,'feature_counts':freq,'minimum_support':50}
force_labels=json.loads((OUT/'labels.json').read_text())['force']
report={'version':model['version'],'trained':'2026-10-14','cohort_rule':'Police forces with at least 95% injury-based reporting and at least 20 motorcycle casualties in each of 2021, 2022 and 2023; retain injury-based records only in every split. Eligibility uses training years only.','eligible_forces':[force_labels.get(str(f),str(f)) for f in eligible],'features':[f['label'] for f in features],'splits':[{'period':name,'n':len(frame),'ksi':int(frame.casualty_severity.le(2).sum()),'collisions':int(frame.collision_index.nunique())} for name,frame in [('Training: 2021–2023',train),('Calibration: 2024',cal),('Held-out test: 2025',test)]],'all_recent_motorcycle_casualties':len(d),'cohort_total':len(cohort),'test_observed':float(yt.mean()),'metrics':metrics,'comparison':improvement,'calibration_bins':bins,'importance':importance,'libraries':{'scikit_learn':sklearn.__version__,'numpy':np.__version__},'parameters':{'seed':SEED,'trees':120,'depth':2,'min_leaf':100,'learning_rate':.05,'subsample':.8},'limits':['Not a crash probability or causal intervention estimate.','Cohort excludes reporting areas that did not meet the training-period rule, and is not representative of all Great Britain.','Only one later-year test; no claim of validation in future years or other countries.','No collision severity, casualty count, severity-adjustment weights, skid or impact variables are predictors.','Probabilities are for recorded KSI under injury-based reporting, not DfT adjusted KSI.','Scenario support counts match age band, category and urban/rural setting only; they do not validate the full combination.','Permutation importance is measured in 2024 calibration data and describes model dependence, not causes.','Probability calibration used 2024 only. Models and hyperparameters were fixed before test evaluation.']}
for name,obj in [('ai-model.json',model),('ai-report.json',report)]:
 (OUT/name).write_text(json.dumps(obj,separators=(',',':'),allow_nan=False),encoding='utf-8')
# Cross-language fixtures from fitted estimators: no identifiers or outcomes exported.
sample=test.iloc[np.linspace(0,len(test)-1,100,dtype=int)]
xs=encode(sample);fixtures=[{'input':[int(row[f['key']]) for f in features],'boosted':float(p),'logistic':float(q)} for (_,row),p,q in zip(sample.iterrows(),predict(gb,gbc,xs),predict(lr,lrc,xs))]
(ROOT/'ai-verification.json').write_text(json.dumps(fixtures),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
