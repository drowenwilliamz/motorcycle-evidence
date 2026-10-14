"""Download official DfT files without changing the original local extracts."""
from pathlib import Path
import urllib.request, concurrent.futures, hashlib, json, time

OUT = Path(__file__).resolve().parents[2] / 'Road Safety' / 'STATS19 2025 release'
OUT.mkdir(parents=True, exist_ok=True)
BASE = 'https://data.dft.gov.uk/road-accidents-safety-data/'
urls = [BASE + f'dft-road-casualty-statistics-{kind}-1979-latest-published-year.csv' for kind in ['collision','vehicle','casualty']]
urls += ['https://assets.publishing.service.gov.uk/media/6ab2a71d997a4b2950cced58/dft-road-casualty-statistics-road-safety-open-dataset-data-guide-2025.xlsx', 'https://assets.publishing.service.gov.uk/media/691c644021ef5aaa6543eef0/dft-road-casualty-statistics-severity-adjustment-figure-guidance.docx']
def fetch(url):
    p = OUT / url.split('/')[-1]
    if not p.exists():
        partial = p.with_suffix(p.suffix+'.partial')
        with urllib.request.urlopen(url, timeout=120) as r, partial.open('wb') as f:
            expected = int(r.headers.get('Content-Length',0))
            count=0
            while block:=r.read(4*1024*1024):
                f.write(block); count+=len(block)
            if expected and count!=expected: raise ValueError(f'Incomplete {p.name}')
        partial.replace(p)
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(8*1024*1024): h.update(b)
    result={'file':p.name,'url':url,'bytes':p.stat().st_size,'sha256':h.hexdigest(),'retrieved':'2026-10-14'}
    print(json.dumps(result),flush=True)
    return result
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    manifest=list(pool.map(fetch,urls))
(OUT/'source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
