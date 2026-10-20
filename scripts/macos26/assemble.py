#!/usr/bin/env python3
"""Replace the platform runtime of an existing arm64 Aura bundle; preserve application code."""
import argparse,json,os,plistlib,shutil,subprocess,sys
from pathlib import Path
from macholib.MachO import MachO
p=argparse.ArgumentParser();p.add_argument('--base-app',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--llama-build',type=Path,required=True);p.add_argument('--srt-build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--manifest',type=Path,default=Path(__file__).resolve().parents[2]/'runtime/macos26-native-manifest.json');a=p.parse_args()
repo=Path(__file__).resolve().parents[2];manifest=json.loads(a.manifest.read_text());app=a.output.resolve();framework=app/'Contents/Frameworks'
if app.exists():raise SystemExit('Output already exists; choose a new bundle path.')
app.parent.mkdir(parents=True,exist_ok=True)
subprocess.run(['/bin/cp','-cR',str(a.base_app.resolve()),str(app)],check=True)
old={framework/n for n in manifest['remove_from_frameworks']};resolved={n.resolve() for n in old}
for path in list(framework.iterdir()):
 if path.is_symlink() and path.resolve() in resolved:path.unlink()
for path in old:
 if path.is_file() or path.is_symlink():path.unlink()
def relocate(target,changes):
 args=['/usr/bin/install_name_tool']
 if target.suffix=='.dylib':args+=['-id','@rpath/'+target.name]
 for source,dest in changes:args+=['-change',source,dest]
 if len(args)>1:subprocess.run(args+[str(target)],check=True,capture_output=True)
for dest,row in manifest['native_closure'].items():
 source=a.cache/'kegs'/row['formula'].replace('@','-')/row['source'];target=framework/dest
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target,follow_symlinks=True)
 relocate(target,[(source,'@loader_path/'+os.path.relpath(framework/name,target.parent)) for source,name in row['dependencies']])
def replace_local(source,target,library_dir):
 shutil.copy2(source,target,follow_symlinks=True);changes=[]
 for header in MachO(str(target)).headers:
  for lc,command,data in header.commands:
   if lc.cmd in {0xc,0x80000018,0x8000001f,0x80000023,0x20}:
    dep=data.split(b'\0',1)[0].decode()
    if dep.startswith(('/usr/lib/','/System/Library/')):continue
    local=library_dir/Path(dep).name
    if not local.is_file():raise RuntimeError('Missing local dependency: '+dep)
    changes.append((dep,'@loader_path/'+os.path.relpath(local,target.parent)))
 relocate(target,sorted(set(changes)))
# Rebuilt SRT is used because the upstream tag archive no longer matches the historical bottle source hash.
replace_local(a.srt_build/'libsrt.1.5.7.dylib',framework/'libsrt.1.5.dylib',framework)
llama=app/'Contents/Resources/engines/engine-cpu-py313/1/_internal/llama_cpp/lib'
for path in llama.glob('*.dylib'):path.unlink()
libs=list((a.llama_build/'bin').glob('*.dylib'))+list((a.llama_build/'vendor/llama.cpp/tools/mtmd').glob('*.dylib'))
for source in libs:shutil.copy2(source,llama/source.name,follow_symlinks=True)
for source in libs:replace_local(source,llama/source.name,llama)
info=app/'Contents/Info.plist';data=plistlib.loads(info.read_bytes());data['LSMinimumSystemVersion']='26.0';info.write_bytes(plistlib.dumps(data))
info=app/'Contents/Resources/BUILD-INFO.json';data=json.loads(info.read_text());data.update(minimum_macos='26.0',build='macOS 26 compatibility build; manual API entry');info.write_text(json.dumps(data,indent=2)+'\n')
shutil.copy2(a.manifest,app/'Contents/Resources/MACOS26-RUNTIME.json')
for path in (app/'Contents/Resources').rglob('*'):
 if path.is_symlink() and not path.exists():path.unlink()
subprocess.run(['/usr/bin/codesign','--force','--deep','--preserve-metadata=entitlements','--sign','-',str(app)],check=True,capture_output=True)
sys.path.insert(0,str(repo/'src'))
from haizflow.services.douyin_component import write_inventory,file_digest
browser=app/'Contents/Resources/mac-browser';write_inventory(browser);marker=browser/'complete.json';data=json.loads(marker.read_text());data['browser_inventory_sha256']=file_digest(browser/'browser-files.json');marker.write_text(json.dumps(data,indent=2)+'\n')
subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(app)],check=True,capture_output=True)
subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app)],check=True,capture_output=True)
print('Signed macOS 26 bundle:',app)
