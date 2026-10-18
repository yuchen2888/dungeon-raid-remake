#!/usr/bin/env python3
from pathlib import Path
import subprocess, concurrent.futures, re, sys, os, json
ROOT=Path(__file__).resolve().parent
platform=sys.argv[1] if len(sys.argv)>1 else 'ios'
sdkname='iphoneos' if platform=='ios' else 'macosx'
sdk=subprocess.check_output(['xcrun','--sdk',sdkname,'--show-sdk-path'],text=True).strip()
target='arm64-apple-ios16.0' if platform=='ios' else 'arm64-apple-ios16.0-macabi'
src=ROOT/'liveexec32-source';lc=src/'HostFrameworks/LC32';out=ROOT/('framework-'+platform);out.mkdir(exist_ok=True)
text=(lc/'Makefile').read_text();block=text.split('LiveExec32Shared_FILES =',1)[1].split('LiveExec32Shared_CFLAGS',1)[0]
files=[lc/x for x in block.replace('\\\n',' ').split()]
files += list((ROOT/'mini-gdbstub/src').rglob('*.c'))
files += [ROOT/'adapter'/x for x in ['raid_tci.cpp','lc32_tci.cpp','lc32_memory.cpp']]
files += [ROOT/'dynarmic-api/src/dynarmic/backend/arm64/exclusive_monitor.cpp']
flags=['-target',target,'-isysroot',sdk,'-O2','-g','-fPIC','-fblocks','-DDYNARMIC_MASTER','-DLC32_DEBUG_LOGS=0','-DRV32','-DLC32_UIKIT_COMPATIBILITY=1','-Wno-deprecated-declarations','-Wno-nullability-completeness','-Wno-c++11-narrowing','-Wno-incompatible-pointer-types','-DCONFIG_VERSION="TCI-experimental"','-DCONFIG_COMMIT="f919185-tci"','-DCONFIG_BRANCH="independent"','-DCONFIG_SHARED_FRAMEWORK_BUNDLE_ID="com.livecontainer.LiveExec32Shared"']
for p in [lc,src/'include',ROOT/'mini-gdbstub/include',ROOT/'dynarmic-api/src',ROOT/'adapter',ROOT/'unicorn-tci/unicorn-engine-sys-tci/include']:
 flags+=['-I',str(p)]
if platform!='ios':flags+=['-iframework',sdk+'/System/iOSSupport/System/Library/Frameworks','-isystem',sdk+'/System/iOSSupport/usr/include']
arc={'crash_exception.mm','LegacyFonts.mm','LegacyAlerts.mm','LegacyRotation.mm'}
def compile(item):
 i,p=item;obj=out/(str(i)+'-'+p.stem+'.o');log=out/(obj.name+'.log')
 cmd=['xcrun','clang++' if p.suffix in ['.cpp','.mm'] else 'clang',*flags]
 if p.suffix in ['.cpp','.mm']:cmd+=['-std=c++17']
 if p.suffix in ['.m','.mm']:cmd+=['-fmodules','-fcxx-modules','-fmodules-cache-path='+str(out/'ModuleCache'),'-include','Foundation/Foundation.h']
 if p.name in arc:cmd+=['-fobjc-arc']
 cmd+=['-c',str(p),'-o',str(obj)]
 signature=json.dumps(cmd)
 sig=obj.with_suffix('.command')
 if obj.exists() and sig.exists() and sig.read_text()==signature and obj.stat().st_mtime>p.stat().st_mtime:return obj,None
 with log.open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:return None,(str(p),log.read_text()[-5000:])
 sig.write_text(signature);return obj,None
objects=[];errors=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for obj,error in pool.map(compile,enumerate(files)):
  if error:errors.append(error)
  else:objects.append(obj)
(out/'compile-errors.json').write_text(json.dumps(errors,indent=2))
print(f'{len(objects)}/{len(files)} compiled; {len(errors)} errors',flush=True)
for p,e in errors[:6]:print(p+'\n'+e)
if errors:sys.exit(1)
framework=out/'LiveExec32Shared.framework';framework.mkdir(exist_ok=True)
frameworks='Accelerate AudioToolbox CFNetwork CoreFoundation CoreMedia CoreVideo Foundation GameKit IOKit ImageIO OpenAL OpenGLES QuartzCore Security UIKit SystemConfiguration CoreText CoreGraphics'.split()
cmd=['xcrun','clang++','-target',target,'-isysroot',sdk,'-dynamiclib','-install_name','@rpath/LiveExec32Shared.framework/LiveExec32Shared','-o',str(framework/'LiveExec32Shared'),*[str(x) for x in objects],str(ROOT/'build-ios/libunicorn.a' if platform=='ios' else ROOT/'build-catalyst/libunicorn.a'),'-Wl,-weak-lMobileGestalt']
if platform!='ios':cmd+=['-iframework',sdk+'/System/iOSSupport/System/Library/Frameworks','-L',sdk+'/System/iOSSupport/usr/lib']
for f in frameworks:cmd+=['-framework',f]
with (out/'link.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
print('Link result',r.returncode)
if r.returncode:print((out/'link.log').read_text()[-7000:]);sys.exit(r.returncode)
