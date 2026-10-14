"""Reproducible STATS19 analysis; original downloads are never modified.
Public outputs contain aggregate cells, not identifiers, coordinates or personal records.
"""
from pathlib import Path
from collections import Counter
import json, hashlib, time
import pandas as pd
import numpy as np
import openpyxl

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parents[1]/'Road Safety'/'STATS19 2025 release'
OUT=ROOT/'dist'/'data'; OUT.mkdir(parents=True,exist_ok=True)
MC={2,3,4,5,23,97,103,104,105,106}
START=2021
audit={'source_rows':{},'detail_start':START,'checks':{}}
def log(s): print(s,flush=True)
def read(kind,cols):
    for year in range(2021,2026):
        p=SOURCE/f'dft-road-casualty-statistics-{kind}-{year}.csv'
        yield from pd.read_csv(p,usecols=cols,dtype={'collision_index':'string','collision_ref_no':'string'},chunksize=250000,low_memory=False)
def export(name,obj):
    (OUT/name).write_text(json.dumps(obj,separators=(',',':'),allow_nan=False),encoding='utf-8')
def record(df): return json.loads(df.to_json(orient='records'))

# Full historical casualty counts, independent of joins, include discontinued motorcycle types.
hist=Counter(); allhist=Counter(); cas=[]; count=0
cc=['collision_index','collision_year','vehicle_reference','casualty_reference','casualty_class','casualty_type','age_of_casualty','casualty_severity','casualty_adjusted_severity_serious']
for x in read('casualty',cc):
    count+=len(x)
    for key,n in x.groupby(['collision_year','casualty_severity']).size().items(): allhist[key]+=int(n)
    m=x[x.casualty_type.isin(MC)]
    for key,n in m.groupby(['collision_year','casualty_severity']).size().items(): hist[key]+=int(n)
    cas.append(m[m.collision_year>=START].copy())
audit['source_rows']['casualty']=count
c=pd.concat(cas,ignore_index=True); del cas
assert not c.duplicated(['collision_index','casualty_reference']).any(),'Duplicate motorcycle casualty keys'
assert set(c.casualty_severity.unique())<={1,2,3}
assert c.collision_year.max()==2025,'Unexpected last year'
log(f'Motorcycle casualties since {START}: {len(c):,}')
history=[]
hw=openpyxl.load_workbook(SOURCE/'ras0102.xlsx',read_only=True,data_only=True)
rates={r[0]:r for r in hw['Rates'].values if len(r)>6 and r[1]=='Motorcycle users' and isinstance(r[0],int)}
for r in hw['Numbers'].values:
    if len(r)>6 and r[1]=='Motorcycle users' and r[2]=='All ages' and isinstance(r[0],int):
        y,f,ksi,adj,tot=r[0],r[3],r[4],r[5],r[6]
        history.append({'year':y,'fatal':f,'serious':ksi-f,'slight':tot-ksi,'total':tot,'adjusted_ksi':adj if isinstance(adj,(float,int)) else None,'fatal_rate':rates[y][3],'adjusted_ksi_rate':rates[y][5] if isinstance(rates[y][5],(float,int)) else None,'total_rate':rates[y][6]})
history.sort(key=lambda r:r['year'])
assert [r['year'] for r in history]==list(range(1979,2026))
export('history.json',history)
pd.DataFrame(history).to_csv(OUT/'historical-casualties.csv',index=False)

vcols=['collision_index','collision_year','vehicle_reference','vehicle_type','vehicle_manoeuvre_historic','skidding_and_overturning','age_of_driver','engine_capacity_cc','age_of_vehicle']
vehicles=[]; count=0
for x in read('vehicle',vcols):
    count+=len(x); vehicles.append(x[(x.collision_year>=START)&(x.vehicle_type.isin(MC)|x.collision_index.isin(c.collision_index))].copy())
v=pd.concat(vehicles,ignore_index=True); del vehicles
audit['source_rows']['vehicle']=count
assert not v.duplicated(['collision_index','vehicle_reference']).any(),'Duplicate motorcycle vehicle keys'
ids=set(v.collision_index)|set(c.collision_index)
log(f'Motorcycle involvements since {START}: {len(v):,}')

acols=['collision_index','collision_year','collision_severity','number_of_vehicles','number_of_casualties','date','police_force','speed_limit','urban_or_rural_area','junction_detail','junction_detail_historic','road_surface_conditions']
collisions=[]; annual_collisions=Counter(); count=0
for x in read('collision',acols):
    count+=len(x)
    for y,n in x.groupby('collision_year').size().items(): annual_collisions[int(y)]+=int(n)
    collisions.append(x[x.collision_index.isin(ids)].copy())
a=pd.concat(collisions,ignore_index=True); del collisions
audit['source_rows']['collision']=count
assert not a.collision_index.duplicated().any(),'Duplicate collision keys'
audit['checks']['motorcycle_casualty_duplicate_keys']=0
audit['checks']['motorcycle_vehicle_duplicate_keys']=0
audit['checks']['selected_collision_duplicate_keys']=0
audit['checks']['casualties_without_collision']=int((~c.collision_index.isin(a.collision_index)).sum())
audit['checks']['vehicles_without_collision']=int((~v.collision_index.isin(a.collision_index)).sum())
assert audit['checks']['casualties_without_collision']==0
assert audit['checks']['vehicles_without_collision']==0
v=v.drop(columns='collision_year').merge(a,on='collision_index',how='left',validate='many_to_one')
c=c.merge(v.drop(columns='collision_year'),on=['collision_index','vehicle_reference'],how='left',validate='many_to_one',indicator=True)
audit['checks']['casualties_without_motorcycle_vehicle']=int((c._merge!='both').sum())
assert audit['checks']['casualties_without_motorcycle_vehicle']==0
audit['checks']['casualty_vehicle_type_disagreements']=int((c.casualty_type!=c.vehicle_type).sum())
v=v[v.vehicle_type.isin(MC)].copy()

def dimensions(d,agefield):
    d=d.copy()
    d['year']=d.collision_year.astype(int)
    d['age']=pd.cut(d[agefield],[-np.inf,-0.1,15,19,24,34,44,54,64,np.inf],labels=[8,0,1,2,3,4,5,6,7]).astype(int)
    typefield='casualty_type' if 'casualty_type' in d else 'vehicle_type'
    d['bike']=d[typefield].map({2:0,3:1,4:2,5:3,23:4,97:5}).fillna(5).astype(int)
    d['area']=d.urban_or_rural_area.map({1:0,2:1}).fillna(2).astype(int)
    # Historic codes preserve roundabout junctions; fallback to current field when absent.
    j=d.junction_detail_historic.where(d.junction_detail_historic.isin([0,1,2,3,5,6,7,8,9]),d.junction_detail)
    d['junction']=np.select([j.eq(0),j.isin([1,2,3,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19])],[0,1],default=2)
    d['skid']=d.skidding_and_overturning.map({0:0,1:1,2:2,5:3}).fillna(4).astype(int)
    d['bend']=np.select([d.vehicle_manoeuvre_historic.isin([16,17]),d.vehicle_manoeuvre_historic.between(1,18)],[1,0],default=2)
    d['speed']=d.speed_limit.where(d.speed_limit.isin([20,30,40,50,60,70]),-1).astype(int)
    d['surface']=d.road_surface_conditions.map({1:0,2:1,3:2,4:2,5:2}).fillna(3).astype(int)
    d['force']=d.police_force.fillna(-1).astype(int)
    return d
c=dimensions(c,'age_of_casualty'); v=dimensions(v,'age_of_driver')
c['role']=c.casualty_class.map({1:0,2:1}).fillna(2).astype(int)
c['severity']=c.casualty_severity.astype(int)
c['count']=1
c['adj_serious']=pd.to_numeric(c.casualty_adjusted_severity_serious,errors='coerce')
nonfatal=c.severity!=1
audit['checks']['nonfatal_invalid_adjustment']=int((nonfatal & (~c.adj_serious.between(0,1))).sum())
assert audit['checks']['nonfatal_invalid_adjustment']==0,'Missing adjustment values'
c.loc[~nonfatal,'adj_serious']=0
dims=['year','age','bike','area','junction','skid','bend','speed','surface','force','role','severity']
cube=c.groupby(dims,dropna=False).agg(n=('count','sum'),adjusted_serious=('adj_serious','sum')).reset_index()
cube.adjusted_serious=cube.adjusted_serious.round(6)
assert cube.n.sum()==len(c)
export('explorer.json',{'columns':list(cube.columns),'rows':cube.values.tolist()})
annual=[]
for y,g in c.groupby('year'):
    vg=v[v.year==y]
    annual.append({'year':int(y),'casualties':len(g),'riders':int((g.role==0).sum()),'passengers':int((g.role==1).sum()),'fatal':int((g.severity==1).sum()),'rider_fatal':int(((g.role==0)&(g.severity==1)).sum()),'serious':int((g.severity==2).sum()),'adjusted_serious':round(g.adj_serious.sum(),2),'adjusted_ksi':round((g.severity==1).sum()+g.adj_serious.sum(),2),'motorcycle_vehicles':len(vg),'motorcycle_collisions':int(vg.collision_index.nunique()),'all_collisions':annual_collisions[int(y)]})
for r in annual:
    official=next(h for h in history if h['year']==r['year'])
    assert r['casualties']==official['total']
    assert r['fatal']==official['fatal']
    assert r['serious']==official['serious']
    assert abs(r['adjusted_ksi']-official['adjusted_ksi'])<.02
export('annual.json',annual)
pd.DataFrame(annual).to_csv(OUT/'annual-motorcycle-summary.csv',index=False)

# Fixed claim checks, clearly separated from explorer filters.
recent=c[c.year.between(2021,2025)]; rv=v[v.year.between(2021,2025)]
fatal=recent[recent.severity==1]
claims={
 'recent_casualties':len(recent),'recent_fatal':len(fatal),
 'recent_adjusted_ksi':round(len(fatal)+recent.adj_serious.sum(),2),
 'rural_bend_fatal':int(((fatal.area==1)&(fatal.bend==1)).sum()),
 'fatal_bend_unknown':int((fatal.bend==2).sum()),
 'recent_motorcycle_collisions':int(rv.collision_index.nunique()),
 'junction_collisions':int(rv.loc[rv.junction==1,'collision_index'].nunique()),
 'junction_unknown_collisions':int(rv.loc[rv.junction==2,'collision_index'].nunique()),
 'up_to_125_collisions':int(rv.loc[rv.bike.isin([0,1]),'collision_index'].nunique()),
 'class_125_collisions':int(rv.loc[rv.bike==1,'collision_index'].nunique()),
 'skid_unknown_casualties':int((recent.skid==4).sum()),
 'bend_by_year':[{'year':int(y),'fatal':int((g.severity==1).sum()),'rural_bend_fatal':int(((g.severity==1)&(g.area==1)&(g.bend==1)).sum()),'fatal_unknown_bend':int(((g.severity==1)&(g.bend==2)).sum())} for y,g in recent.groupby('year')]
}
export('claims.json',claims)

# Decode police force names from the supplied official guide.
w=openpyxl.load_workbook(SOURCE/'guide-2025.xlsx',read_only=True,data_only=True)
forces={str(int(r[2])):r[3] for r in w.active.values if r[1]=='police_force' and isinstance(r[2],(int,float))}
export('labels.json',{'force':forces,'age':['Under 16','16–19','20–24','25–34','35–44','45–54','55–64','65+','Unknown'], 'bike':['50cc and under','125cc category','Over 125–500cc','Over 500cc','Electric motorcycle','Unknown capacity'], 'area':['Urban','Rural','Unknown'], 'junction':['Away from junction','At / near junction','Unknown'], 'skid':['No skid / overturn recorded','Skidded','Skidded and overturned','Overturned','Unknown'], 'bend':['Other recorded manoeuvre','Recorded bend manoeuvre','Unavailable / unknown'], 'surface':['Dry','Wet / damp','Snow, ice or flood','Unknown'], 'role':['Rider','Passenger','Other / unknown']})
audit['checks']['casualty_counts_reconcile_to_history']=True
audit['checks']['aggregated_cells_reconcile']=True
audit['detail_motorcycle_casualties']=len(c)
audit['years']=[int(min(h['year'] for h in history)),int(max(h['year'] for h in history))]
audit['checks']['recent_totals_match_official_RAS0102']=True
audit['notes']=['Historical counts and national mileage rates come from DfT RAS0102, 1979–2025.','Detailed counts are motorcycle riders and passengers by casualty type in final 2021–2025 records.','Modern joins validated on collision_index and vehicle_reference; casualty keys on collision_index and casualty_reference.','Unknowns remain visible. No imputation or subgroup exposure rates.','Bend evidence uses historic manoeuvre only; unavailable new-specification values are not coded as no bend.']
export('audit.json',audit)
manifest=json.loads((SOURCE/'recent_manifest.json').read_text())+json.loads((SOURCE/'tables_manifest.json').read_text())
export('sources.json',manifest)
log(json.dumps({'audit':audit,'annual':annual[-2:],'claims':claims},indent=2))
