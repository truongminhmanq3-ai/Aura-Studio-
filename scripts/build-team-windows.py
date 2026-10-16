"""Build the private Windows x64 package with existing pinned native engines."""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,subprocess,sys,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE_URL='https://github.com/MachHongHai/HaizFlow/releases/download/v0.1.8/'
CORE_NAME='HaizFlow-Core-0.1.8-windows-x64-full.zip'
CORE_SHA='0bbdd74d4df001b1ef4b4fd6b134dfdcba3c1f4d6d9e39010c63e845d73fe119'

def digest(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def fetch(url,path,expected):
 if path.exists() and digest(path)==expected:return
 print('Downloading',path.name,flush=True)
 temporary=path.with_suffix(path.suffix+'.part')
 with urllib.request.urlopen(url,timeout=90) as source,temporary.open('wb') as out:shutil.copyfileobj(source,out,1024*1024)
 if digest(temporary)!=expected:raise ValueError('Download checksum mismatch: '+path.name)
 temporary.replace(path)

def extract(archive,folder,keep=lambda name:True):
 folder.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(archive) as z:
  for info in z.infolist():
   name=info.filename
   if not keep(name):continue
   target=folder/name
   if not target.resolve().is_relative_to(folder.resolve()):raise ValueError('Unsafe ZIP member')
   if info.is_dir():target.mkdir(parents=True,exist_ok=True);continue
   target.parent.mkdir(parents=True,exist_ok=True)
   with z.open(info) as source,target.open('wb') as out:shutil.copyfileobj(source,out,1024*1024)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--inputs',type=Path,required=True);a=parser.parse_args()
 if sys.platform!='win32' or sys.maxsize<2**32:parser.error('Build on 64-bit Windows.')
 inputs=a.inputs.resolve();inputs.mkdir(parents=True,exist_ok=True);out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 core=inputs/CORE_NAME;fetch(BASE_URL+CORE_NAME,core,CORE_SHA)
 base=inputs/'native-core';extract(core,base,lambda n:n.startswith(('_internal/bin/','_internal/haizflow/assets/','sources/ffmpeg/','licenses/')) or n in {'FFMPEG-MANIFEST.json','THIRD-PARTY-SOURCES.json'})
 build=out/'build';build.mkdir(exist_ok=True)
 paths=['qml','assets','translations'];datas=[(str(ROOT/'src/haizflow/desktop'/p),'haizflow/desktop/'+p) for p in paths]
 datas += [(str(ROOT/'src/haizflow/assets'),'haizflow/assets'),(str(base/'_internal/bin'),'bin')]
 spec=build/'AuraStudio.spec'
 spec.write_text(f'''from PyInstaller.utils.hooks import collect_submodules,collect_data_files,copy_metadata
hidden=collect_submodules('haizflow')+collect_submodules('yt_dlp')
datas={datas!r}+collect_data_files('certifi')+collect_data_files('playwright')+copy_metadata('playwright')+copy_metadata('haizflow')
a=Analysis([{str(ROOT/'haizflow_desktop.py')!r}],pathex=[{str(ROOT/'src')!r}],binaries=[],datas=datas,hiddenimports=hidden,excludes=['torch','torchaudio','torchvision','whisperx','pyannote','torchcodec','transformers','accelerate','llama_cpp','ctranslate2','faster_whisper','demucs','rapidocr','soundfile','av','scipy','sklearn','matplotlib','pandas','IPython','pytest','PySide6.QtWebEngineCore','PySide6.QtWebEngineQuick','PySide6.QtWebEngineWidgets'])
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='AuraStudio',console=False,icon={str(ROOT/'src/haizflow/desktop/assets/branding/haizflow.ico')!r})
coll=COLLECT(exe,a.binaries,a.datas,name='AuraStudio',strip=False,upx=False)
''',encoding='utf-8')
 subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--distpath',str(out/'dist'),'--workpath',str(build/'work'),str(spec)],check=True)
 package=out/'Aura Studio Windows';app=package/'app'
 if package.exists():shutil.rmtree(package)
 shutil.copytree(out/'dist/AuraStudio',app)
 for name in ['FFMPEG-MANIFEST.json','THIRD-PARTY-SOURCES.json']:shutil.copy2(base/name,app/name)
 shutil.copytree(base/'sources',app/'sources',dirs_exist_ok=True)
 shutil.copytree(base/'licenses',app/'licenses',dirs_exist_ok=True)
 shutil.copytree(ROOT/'licenses',app/'licenses',dirs_exist_ok=True)
 for name in ['NOTICE','THIRD_PARTY_NOTICES.md']:shutil.copy2(ROOT/name,app/name)
 shutil.copytree(base/'_internal/haizflow/assets',app/'_internal/haizflow/assets',dirs_exist_ok=True)
 (app/'BUILD-INFO.json').write_text(json.dumps({'application':'HaizFlow','version':'0.1.8','display_name':'Aura Studio','platform':'windows-x64','build':'private team build'}),encoding='utf-8')
 sys.path.insert(0,str(ROOT/'src'))
 from haizflow.update.state import provision
 provision(app)
 catalog=json.loads((ROOT/'runtime/resource-pack-manifest.json').read_text())
 shutil.copy2(ROOT/'runtime/resource-pack-manifest.json',app/'RESOURCE-PACKS.json')
 for pack_id in ['engine-cpu-py313','engine-vision-onnx']:
  record=catalog['packs'][pack_id];archive=inputs/(pack_id+'-'+record['version']+'.zip');fetch(record['url'],archive,record['sha256'])
  target=app/'runtime/engines'/pack_id/record['version'];extract(archive,target)
  for name in ['LICENSE','LICENSE.txt']:(target/name).unlink(missing_ok=True)
  shutil.copy2(ROOT/'NOTICE',target/'NOTICE')
  (target/'complete.json').write_text(json.dumps({'pack_id':pack_id,'version':record['version'],'protocol_version':1,'archive_sha256':record['sha256']}),encoding='utf-8')
 (package/'scripts').mkdir()
 shutil.copy2(ROOT/'scripts/Install-AuraStudio.ps1',package/'scripts/Install-AuraStudio.ps1')
 shutil.copy2(ROOT/'scripts/Cai-dat-Aura-Studio.cmd',package/'Cai-dat-Aura-Studio.cmd')
 (package/'Huong-dan.txt').write_text('Extract the entire ZIP, close Aura Studio, then run Cai-dat-Aura-Studio.cmd.\nOpen Settings > API Key and enter your own key. No API keys are included; Python is bundled.\nDownload Whisper/models and the Douyin browser from Settings when needed.\n',encoding='utf-8')
 print('Built Windows package:',package,flush=True)
if __name__=='__main__':main()
