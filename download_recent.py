from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request, hashlib,json,time
OUT=Path(__file__).resolve().parents[2]/'Road Safety'/'STATS19 2025 release'
def one(arg):
    kind,year=arg
    name=f'dft-road-casualty-statistics-{kind}-{year}.csv'
    url='https://data.dft.gov.uk/road-accidents-safety-data/'+name
    p=OUT/name
    if not p.exists():
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url,timeout=60) as r:
                    data=r.read()
                if not data.startswith(b'collision_index'): raise ValueError('Unexpected schema')
                p.write_bytes(data); break
            except Exception:
                if attempt==2: raise
    print(name,p.stat().st_size,flush=True)
    return {'file':name,'url':url,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'retrieved':'2026-10-14'}
with ThreadPoolExecutor(max_workers=6) as pool:
    m=list(pool.map(one,[(k,y) for y in range(2025,2020,-1) for k in ['collision','vehicle','casualty']]))
(OUT/'recent_manifest.json').write_text(json.dumps(m,indent=2))
