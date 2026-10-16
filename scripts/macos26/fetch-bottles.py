from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import requests,json,hashlib,tarfile,time,shutil
import argparse
p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--manifest',type=Path,default=Path(__file__).resolve().parents[2]/'runtime/macos26-native-manifest.json');args=p.parse_args()
root=args.cache.resolve();root.mkdir(parents=True,exist_ok=True)
records=json.loads(args.manifest.read_text())['bottles']
(root/'bottles').mkdir(exist_ok=True);(root/'kegs').mkdir(exist_ok=True)
def download(row):
 name=row['name'];dest=root/'bottles'/(name.replace('@','-')+'-'+row['version']+'-'+row['platform']+'-'+row['sha256'][:8]+'.tar.gz');extract=root/'kegs'/name.replace('@','-');marker=extract/'.extracted'
 if marker.exists() and marker.read_text()==row['sha256']:return name
 if extract.exists():shutil.rmtree(extract)
 if not dest.exists():
  repo='homebrew/core/'+name.replace('@','/');s=requests.Session();t=s.get('https://ghcr.io/token',params={'scope':'repository:'+repo+':pull','service':'ghcr.io'},timeout=45);t.raise_for_status();token=t.json()['token']
  for attempt in range(4):
   try:
    with s.get(row['url'],headers={'Authorization':'Bearer '+token},stream=True,timeout=(30,90)) as r:
     r.raise_for_status()
     with dest.with_suffix('.part').open('wb') as out:
      for chunk in r.iter_content(256*1024):out.write(chunk)
    with dest.with_suffix('.part').open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==row['sha256'],name
    dest.with_suffix('.part').replace(dest);break
   except Exception:
    dest.with_suffix('.part').unlink(missing_ok=True)
    if attempt==3:raise
 else:
  with dest.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==row['sha256'],name
 extract.mkdir(exist_ok=True)
 with tarfile.open(dest) as tar:
  def keep(m):
   parts=Path(m.name).parts;relative='/'.join(parts[2:]);low=relative.lower()
   if m.isdir():return True
   return (relative.startswith(('lib/','include/')) and not relative.endswith('.a')) or relative in {'bin/ffmpeg','bin/ffprobe'} or relative.startswith(('.brew/','etc/')) or any(w in low for w in ['license','copying','copyright','notice','sbom'])
  tar.extractall(extract,members=[m for m in tar.getmembers() if keep(m)],filter='data')
 marker.write_text(row['sha256'])
 return name
if __name__=='__main__':
 with ThreadPoolExecutor(max_workers=8) as pool:
  for i,f in enumerate(as_completed([pool.submit(download,r) for r in records.values()]),1):print('Downloaded verified native bottle',i,len(records),f.result(),flush=True)
 print('All pinned macOS26/earlier bottles downloaded and extracted.',flush=True)
