#!/usr/bin/env python3
from pathlib import Path
import argparse, shutil, subprocess, plistlib, json, os, zipfile
R=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--platform',choices=['ios','catalyst'],default='ios');p.add_argument('--headless',action='store_true');a=p.parse_args()
platform=a.platform;catalyst=platform=='catalyst';out=R/'apps'/platform;app=out/('DungeonRaidHost.app' if catalyst else 'Payload/DungeonRaid.app')
base=a.base/('host-build/catalyst/DungeonRaidHost.app' if catalyst else 'host-build/ios/Payload/DungeonRaid.app')
if app.exists():shutil.rmtree(app)
shutil.copytree(base,app,symlinks=True)
fw=app/('Contents/Frameworks' if catalyst else 'Frameworks')/'LiveExec32Shared.framework'
shutil.copy2(R/'framework-ios/LiveExec32Shared.framework/LiveExec32Shared',fw/'LiveExec32Shared')
if catalyst:
 src=fw/'LiveExec32Shared';tmp=fw/'converted'
 subprocess.run(['xcrun','vtool','-arch','arm64','-set-build-version','6','16.0','27.0','-replace','-output',str(tmp),str(src)],check=True)
 tmp.replace(src);src.chmod(0o755)
info=app/('Contents/Info.plist' if catalyst else 'Info.plist');d=plistlib.loads(info.read_bytes());d['CFBundleVersion']='5';d['CFBundleDisplayName']='Dungeon Raid';info.write_bytes(plistlib.dumps(d))
for f in [app/'embedded.mobileprovision',app/'_CodeSignature',app/'Contents/_CodeSignature']:
 if f.is_dir():shutil.rmtree(f)
 elif f.exists():f.unlink()
sdk='macosx' if catalyst else 'iphoneos';sdkroot=subprocess.check_output(['xcrun','--sdk',sdk,'--show-sdk-path'],text=True).strip()
target='arm64-apple-ios16.0-macabi' if catalyst else 'arm64-apple-ios16.0'
exe=app/('Contents/MacOS/DungeonRaidHost' if catalyst else 'DungeonRaidHost')
args=['xcrun','--sdk',sdk,'clang','-target',target,'-fobjc-arc','-Wall','-Wextra','-Werror','-Wl,-export_dynamic','-Wl,-rpath,'+('@executable_path/../Frameworks' if catalyst else '@executable_path/Frameworks')]
if catalyst:args+=['-iframework',sdkroot+'/System/iOSSupport/System/Library/Frameworks']
for name in ['UIKit','Foundation','CoreGraphics']:args+=['-framework',name]
if a.headless:args+=['-DRAID_HEADLESS_VERIFY=1']
args += [str(R/'runtime/liveexec32/host-main.m'),str(R/'runtime/liveexec32/host-lifecycle.m'),'-o',str(exe)]
subprocess.run(args,check=True)
for framework in sorted((fw.parent).glob('*.framework')):subprocess.run(['codesign','--force','--sign','-',str(framework)],check=True)
subprocess.run(['codesign','--force','--sign','-',str(app)],check=True)
subprocess.run(['codesign','--verify','--strict','--deep',str(app)],check=True)
report={'app':str(app),'platform':platform,'backend':'Unicorn TCI','jit_required':False,'device_tested':False,'signed_for_device':False,'headless_diagnostic':a.headless,'catalyst_note':'iOS framework Mach-O platform converted for diagnostic compatibility, not native Catalyst build' if catalyst else None}
(out/'package-report.json').write_text(json.dumps(report,indent=2))
if not catalyst:
 ipa=R/'DungeonRaid-independent-experimental-unsigned.ipa'
 subprocess.run(['/usr/bin/zip','-q','-y','-r',str(ipa),'Payload'],cwd=out,check=True)
 print(ipa)
print(app)
