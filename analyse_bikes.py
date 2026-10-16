"""Aggregate motorcycle casualties by recorded model and capacity; no individual records exported."""
from pathlib import Path
import json,re
import pandas as pd
ROOT=Path(__file__).resolve().parent
DATA=ROOT.parents[1]/'Road Safety'
MC={2,3,4,5,23,97,103,104,105,106}
cc=['collision_index','collision_year','vehicle_reference','casualty_reference','casualty_class','casualty_type','casualty_severity','casualty_adjusted_severity_serious']
vc=['collision_index','collision_year','vehicle_reference','generic_make_model','engine_capacity_cc']
cs=[];vs=[]
for y in range(2020,2026):
    folder=DATA/('Road Safety Open Data - DfT STATS19' if y==2020 else 'STATS19 2025 release')
    suffix='last-5-years' if y==2020 else str(y)
    for kind,cols,dest in [('casualty',cc,cs),('vehicle',vc,vs)]:
        x=pd.read_csv(folder/f'dft-road-casualty-statistics-{kind}-{suffix}.csv',usecols=cols,dtype={'collision_index':str},low_memory=False)
        x=x[x.collision_year.eq(y)]
        if kind=='casualty': x=x[x.casualty_type.isin(MC)&x.casualty_class.isin([1,2])]
        dest.append(x)
c=pd.concat(cs);v=pd.concat(vs)
assert not c.duplicated(['collision_index','collision_year','casualty_reference']).any()
keys=['collision_index','collision_year','vehicle_reference']
assert not v.duplicated(keys).any()
d=c.merge(v,on=keys,how='left',validate='many_to_one',indicator=True)
assert d._merge.eq('both').all()
d['model']=d.generic_make_model.fillna('Unknown / redacted').str.strip().str.upper().replace({'-1':'Unknown / redacted','MAKE AND MODEL REDACTED':'Unknown / redacted'})
def make(s):
    if s=='Unknown / redacted': return 'Unknown / redacted'
    for m in ['ROYAL ENFIELD','MOTO GUZZI','MV AGUSTA','HARLEY DAVIDSON']:
        if s.startswith(m+' '): return m
    return s.split(' ')[0]
d['make']=d.model.map(make)
# Curated broad families only. Ambiguous series deliberately remain unclassified.
# Sources describe family styles; they do not prove historic variant or safety-system fitment.
sources={
 'honda':'https://www.honda.co.uk/motorcycles/range/super-sport.html',
 'pcx':'https://2rom-prd-data.hondamotopub.com/pc/HMJ/PCX/2020/11K96J02_motopub.pdf',
 'vision':'https://motos.honda.es/wp-content/uploads/manuales/NSC110_OM_35K2CA10_SPA_WEB.pdf',
 'kawasaki':'https://www.kawasaki.co.uk/en/Motorcycles.html',
 'ducati':'https://www.ducati.com/us/en/bikes/multistrada',
 'classic':'https://www.triumphmotorcycles.co.uk/bikes/classic/',
 'touring':'https://www.honda.co.uk/content/dam/local/uk/brochures/motorcycles/21YMBrochures/21YMHUKMCSTREETTOURINGLR1.pdf',
 'harley':'https://www.harley-davidson.com/content/dam/h-d/documents/tools/get-a-catalog/global/2020_Big_Book_Internationall.pdf',
 'yamaha':'https://www.yamaha-motor.eu/gb/en/brochures/motorcycles/',
 'suzuki':'https://bikes.suzuki.co.uk/bikes/sport/',
 'triumph_road':'https://www.triumphmotorcycles.co.uk/bikes/roadsters',
 'triumph_adv':'https://www.triumphmotorcycles.co.uk/motorcycles/adventure',
 'ktm':'https://press.ktm.com/news-2023-ktm-street-range-flashes-with-a-fresh-selection-of-new-colorways?id=172327&l=north+america&menueid=6521',
 'nmax':'https://cdn2.yamaha-motor.eu/prod/owner-manuals/Scooters/Nmax.pdf',
 'honda_adv':'https://www.honda.co.uk/content/dam/local/uk/brochures/motorcycles/21YMBrochures/21YMHUKMCAdventureLR1.pdf'
}
rules=[
 (r'^DUCATI MULTISTRADA','Adventure / crossover','ducati'),
 (r'^TRIUMPH BONNEVILLE','Retro / classic','classic'),
 (r'^HONDA (?:GL ?1800|GOLD WING)','Touring','touring'),
 (r'^HARLEY[- ]DAVIDSON XL(?: |$|[0-9])','Cruiser','harley'),
 (r'^HONDA WW125','Scooter','pcx'),
 (r'^HONDA NSC(?: |$|110)','Scooter','vision'),
 (r'^KAWASAKI ZX(?: |$|[0-9])','Sports / sports touring','kawasaki'),
 (r'^HONDA CBR','Sports / sports touring','honda'),
 (r'^YAMAHA YZF','Sports / sports touring','yamaha'),
 (r'^SUZUKI GSXR','Sports / sports touring','suzuki'),
 (r'^YAMAHA MT(?: |$|[0-9])','Naked / roadster','yamaha'),
 (r'^TRIUMPH (?:STREET TRIPLE|SPEED TRIPLE|TRIDENT)(?: |$)','Naked / roadster','triumph_road'),
 (r'^KTM (?:125|200|390) DUKE(?: |$)','Naked / roadster','ktm'),
 (r'^KTM RC (?:125|390)(?: |$)','Sports / sports touring','ktm'),
 (r'^TRIUMPH TIGER(?: |$)','Adventure / crossover','triumph_adv'),
 (r'^YAMAHA TRACER(?: |$)','Sports / sports touring','yamaha'),
 (r'^HONDA (?:CB500X|NC750X|CRF1100|X-ADV)','Adventure / crossover','honda_adv'),
 (r'^YAMAHA GPD(?: |$|125)','Scooter','nmax')
]
def classify(s):
    for pattern,style,source in rules:
        if re.search(pattern,s): return style,source
    return 'Unclassified / ambiguous',''
mapping={s:classify(s) for s in d.model.unique()}
d['style']=d.model.map(lambda x:mapping[x][0])
d['cc']=pd.to_numeric(d.engine_capacity_cc,errors='coerce').fillna(-1).astype(int)
d.loc[d.cc.le(0),'cc']=-1
d['category']=d.casualty_type.map({2:'≤50cc',3:'51–125cc',4:'126–500cc',5:'>500cc',23:'Electric',97:'Other / unknown'}).fillna('Other / unknown')
d['band']=pd.cut(d.cc,[0,50,125,500,750,1000,float('inf')],labels=['≤50cc','51–125cc','126–500cc','501–750cc','751–1000cc','>1000cc']).astype('string').fillna('Unknown capacity')
d.loc[d.casualty_type.eq(23),'band']='Electric'
d['fatal']=d.casualty_severity.eq(1).astype(int)
d['ksi']=d.casualty_severity.le(2).astype(int)
d['n']=1
weights=pd.to_numeric(d.casualty_adjusted_severity_serious,errors='coerce')
assert weights[d.fatal.eq(0)].between(0,1).all()
d['adj']=d.fatal+weights.where(d.fatal.eq(0),0)
hist=json.loads((ROOT/'dist/data/history.json').read_text())
for y,g in d.groupby('collision_year'):
    h=next(x for x in hist if x['year']==y)
    assert len(g)==h['total'] and g.fatal.sum()==h['fatal'] and g.ksi.sum()==h['fatal']+h['serious']
    if y>=2021: assert abs(g.adj.sum()-h['adjusted_ksi'])<.03
# 2020 has an older adjustment vintage: never export as comparable adjusted estimates.
d.loc[d.collision_year.eq(2020),'adj']=0
group=['collision_year','make','model','style','category','band','cc','casualty_class']
g=d.groupby(group,dropna=False).agg(n=('n','sum'),fatal=('fatal','sum'),ksi=('ksi','sum'),adj=('adj','sum')).reset_index()
g['adj']=g.adj.round(6)
assert g.n.sum()==len(d)
obj={'columns':list(g.columns),'rows':json.loads(g.to_json(orient='values')),'sources':sources,'mapping':[{'model':s,'style':v[0],'source':v[1]} for s,v in sorted(mapping.items()) if v[1]],'audit':{'casualties':len(d),'recordedKsi':int(d.ksi.sum()),'unknownModelCasualties':int(d.model.eq('Unknown / redacted').sum()),'classifiedCasualties':int(d.style.ne('Unclassified / ambiguous').sum()),'duplicateKeys':0,'unmatchedCasualties':0,'nationalRecordedTotalsReconciled':True,'adjustedFrom':2021},'date':'2026-10-16'}
(ROOT/'dist/data/bikes.json').write_text(json.dumps(obj,separators=(',',':'),allow_nan=False),encoding='utf-8')
print(json.dumps(obj['audit']))
print('Over 500cc generic families:')
print(d[d.category.eq('>500cc')].groupby(['model','style']).agg(n=('n','sum'),ksi=('ksi','sum')).sort_values('ksi',ascending=False).head(20).to_string())
print('Actual capacity bands:')
print(d.groupby('band').agg(n=('n','sum'),ksi=('ksi','sum')).to_string())
