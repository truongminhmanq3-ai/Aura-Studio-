from pathlib import Path
import json,struct,plistlib
from macholib.MachO import MachO
import argparse
p=argparse.ArgumentParser();p.add_argument('app',type=Path);p.add_argument('--report',type=Path,required=True);args=p.parse_args()
app=args.app.resolve();rows=[];bad=[];external=[]
for p in app.rglob('*'):
 if not p.is_file() or p.is_symlink() or p.suffix=='.a':continue
 with p.open('rb') as f:magic=f.read(4)
 if magic not in {b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe'}:continue
 versions=[];architectures=[]
 for h in MachO(str(p)).headers:
  architectures.append(h.header.cputype)
  for lc,command,data in h.commands:
   value=getattr(command,'minos',None) if lc.cmd==0x32 else getattr(command,'version',None) if lc.cmd==0x24 else None
   if value:versions.append((value>>16,(value>>8)&255,value&255))
   if lc.cmd in {0xc,0x80000018,0x8000001f,0x80000023,0x20}:
    dep=data.split(b'\0',1)[0].decode()
    if dep.startswith('/') and not dep.startswith(('/System/Library/','/usr/lib/')):external.append((str(p.relative_to(app)),dep))
 if versions and max(versions)>(26,0,0):bad.append((str(p.relative_to(app)),max(versions)))
 assert 0x0100000c in architectures,('Not ARM64',str(p))
 rows.append({'file':str(p.relative_to(app)),'minimum_macos':'.'.join(map(str,max(versions))) if versions else 'not_declared'})
assert not bad,bad
assert not external,external
assert plistlib.loads((app/'Contents/Info.plist').read_bytes())['LSMinimumSystemVersion']=='26.0'
report={'target':'macOS26 ARM64','native_binaries_checked':len(rows),'higher_minimum_found':bad,'external_absolute_dependencies':external,'files':rows,'actual_runtime_test_environment':'macOS27.2; macOS26 execution has not been tested'}
args.report.write_text(json.dumps(report,indent=2)+'\n');print('PASS macOS26 minimum and ARM64 audit:',len(rows),'native binaries; no external absolute dependencies.',flush=True)
