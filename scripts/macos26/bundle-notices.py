#!/usr/bin/env python3
"""Bundle the pinned native component notices, recipes and source mapping, then reseal."""
import argparse,json,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--app',type=Path,required=True);p.add_argument('--source-manifest',type=Path,required=True);p.add_argument('--llama-source',type=Path,required=True);a=p.parse_args()
manifest=Path(__file__).resolve().parents[2]/'runtime/macos26-native-manifest.json'
records=json.loads(manifest.read_text())['bottles'];out=a.app/'Contents/Resources/licenses/macos26-native';out.mkdir(parents=True,exist_ok=True)
for name,row in records.items():
 keg=a.cache/'kegs'/name.replace('@','-');dest=out/name.replace('@','-');dest.mkdir(exist_ok=True)
 for path in keg.rglob('*'):
  if not path.is_file() or path.is_symlink():continue
  relative=path.relative_to(keg);low='/'.join(relative.parts[2:]).lower()
  if any(word in low for word in ['license','copying','copyright','notice','sbom']) or '/.brew/' in '/'+str(relative):
   target=dest/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
for relative in ['LICENSE.md','vendor/llama.cpp/LICENSE']:
 source=a.llama_source/relative;dest=out/'llama-cpp-python'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
shutil.copy2(a.source_manifest,out/'source-manifest.json');shutil.copy2(manifest,out/'native-manifest.json')
(out/'README.md').write_text('Native macOS 26 runtime: third-party notices and exact bottle recipes.\nSources are in Aura-Studio-macOS26-NativeSources.zip plus Aura-Studio-macOS-ThirdPartySources.zip; source-manifest.json maps each component to its archive.\nSRT was rebuilt from the verified upstream archive described in native-manifest.json, not the historical bottle source.\nllama-cpp-python/llama.cpp and SRT are built using Apple SDK26.5, deployment26.0; scripts/macos26/build-native.sh contains the build settings.\n')
subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(a.app.resolve())],check=True,capture_output=True)
subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(a.app.resolve())],check=True,capture_output=True)
print('Notices bundled and signature verified:',len(records),'native components plus llama source notices')
