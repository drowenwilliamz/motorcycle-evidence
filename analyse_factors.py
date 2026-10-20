from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import json,hashlib
ROOT=Path(__file__).resolve().parent
SRC=ROOT.parents[1]/'Road Safety'/'Published factors'
N='urn:oasis:names:tc:opendocument:xmlns:table:1.0'
def read(p):
 tree=etree.fromstring(ZipFile(p).read('content.xml'));tabs={}
 for tab in tree.findall('.//{'+N+'}table'):
  rows=[]
  for row in tab.findall('{'+N+'}table-row'):
   vals=[]
   for c in row:
    vals.extend([' '.join(c.itertext()).strip()]*min(int(c.get('{'+N+'}number-columns-repeated','1')),50))
   while vals and not vals[-1]:vals.pop()
   if vals:rows.append(vals)
  tabs[tab.get('{'+N+'}name')]=rows
 return tabs
urls={'ras0701':'https://assets.publishing.service.gov.uk/media/6a639b742dc18ebe4c3b2bcf/ras0701.ods','ras0702':'https://assets.publishing.service.gov.uk/media/6a639b8cabcde513b38b6eae/ras0702.ods','ras0701_split':'https://assets.publishing.service.gov.uk/media/6ab260b3fceb6fb3a6500fac/ras0701_split.ods'}
out={'retrieved':'2026-10-20','sources':urls,'rows':[],'split':[],'audit':{}}
def number(v):
 try:return float(v.replace(',',''))
 except (ValueError,AttributeError):return None
for key,prefix,pop,kind in [('ras0702','Vehicle','Motorcycle','vehicle'),('ras0701','Road_user_type','Motorcycle users','casualty')]:
 tabs=read(SRC/(key+'.ods'));nums=tabs[prefix+'_number'];nh=nums[4]
 lookup={(r[0],r[1],r[3]):r for r in nums[5:] if len(r)>4 and r[2]==pop}
 denominator='Vehicles in collisions with at least 1 RSF' if kind=='vehicle' else 'Any RSF'
 for mode,suffix in [('converted','converted_percent' if kind=='vehicle' else 'convert_percent'),('direct','direct_percent')]:
  sheet=prefix+'_'+suffix;rs=tabs[sheet];h=rs[4]
  for r in rs[5:]:
   if len(r)<5 or r[2]!=pop:continue
   for i,y in enumerate(h[4:],4):
    if not y.isdigit() or int(y)<2020:continue
    countcol=nh.index(y+(' converted' if mode=='converted' else ' directly recorded'))
    count=number(lookup[r[0],r[1],r[3]][countcol]);den=number(lookup[denominator,denominator,r[3]][countcol]);pct=number(r[i])
    if pct is not None:assert 0<=pct<=100
    # DfT counts/adjusted estimates and percentages are rounded independently.
    if pct is not None and count is not None and den and den>100:assert abs(100*count/den-pct)<1.1,(key,r[1],y)
    out['rows'].append(dict(kind=kind,mode=mode,year=int(y),section=r[0],factor=r[1],severity=r[3],percent=pct,count=count,denominator=den,source=key,sheet=sheet))
 out['audit'][key]={'sha256':hashlib.sha256((SRC/(key+'.ods')).read_bytes()).hexdigest(),'notes':tabs['Notes']}
tabs=read(SRC/'ras0701_split.ods')
for r in tabs['Road_user_type_percent'][5:]:
 if len(r)>6 and r[4]=='Motor Cyclist' and r[0]=='Direct' and r[5]=='KSI (adjusted) percent' and 'observation' in r[3]:
  out['split'].append({'assignment':r[1],'factor':r[3],'percent2025':number(r[-1])})
out['audit']['ras0701_split']={'sha256':hashlib.sha256((SRC/'ras0701_split.ods').read_bytes()).hexdigest(),'notes':tabs['Notes']}
assert len(out['split'])==4
assert len({(r['kind'],r['mode'],r['year'],r['severity'],r['section'],r['factor']) for r in out['rows']})==len(out['rows'])
(ROOT/'dist/data/factors.json').write_text(json.dumps(out,separators=(',',':'),allow_nan=False))
for r in out['rows']:
 if r['kind']=='vehicle' and r['year']==2025 and r['severity']=='FSC (adjusted)' and ('braking' in r['factor'] or 'observation' in r['factor'] or r['factor']==denominator):print(r)
print('Validated',len(out['rows']),'published factor cells')

