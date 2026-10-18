#!/usr/bin/env python3
"""Offline rebuild. Requires Xcode and CMake 3.31+; never signs with private keys."""
from pathlib import Path
import argparse,subprocess,os,shutil
R=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--cmake',default=shutil.which('cmake'));p.add_argument('--mac-tests',action='store_true');a=p.parse_args()
if not a.cmake:p.error('Provide --cmake /absolute/path/to/cmake')
env=os.environ.copy();env.update(ARCHFLAGS='-arch arm64',PKG_CONFIG='/usr/bin/false')
# This Unicorn tree uses bundled glib and does not query external packages.
platform='macos' if a.mac_tests else 'ios';build=R/('build-'+platform)
args=[a.cmake,'-S',str(R/'unicorn-tci/unicorn-engine-sys-tci'),'-B',str(build),'-DUNICORN_INTERPRETER=ON','-DUNICORN_ARCH=arm','-DUNICORN_BUILD_TESTS=OFF','-DCMAKE_BUILD_TYPE=Release']
if platform=='ios':args+=['-DCMAKE_SYSTEM_NAME=iOS','-DCMAKE_OSX_SYSROOT=iphoneos','-DCMAKE_OSX_DEPLOYMENT_TARGET=16.0','-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY']
subprocess.run(args,env=env,check=True);subprocess.run([a.cmake,'--build',str(build),'--target','unicorn_archive','--parallel','4'],check=True)
if a.mac_tests:
 includes=['-I'+str(R/x) for x in ['adapter','dynarmic-api/src','liveexec32-source/HostFrameworks/LC32','unicorn-tci/unicorn-engine-sys-tci/include']]
 common=['xcrun','clang++','-std=c++17','-O2','-DDYNARMIC_MASTER',*includes,str(R/'adapter/raid_tci.cpp')]
 subprocess.run(['xcrun','clang','-dynamiclib',str(R/'tests/noexec_guard.c'),'-o',str(R/'noexec_guard.dylib')],check=True)
 for name,files in [('adapter-test',['tests/adapter_test.cpp']),('lc32-adapter-test',['adapter/lc32_tci.cpp','tests/lc32_adapter_test.cpp','liveexec32-source/HostFrameworks/LC32/arm_dynarmic_cp15.cpp'])]:
  subprocess.run([*common,*[str(R/x) for x in files],str(build/'libunicorn.a'),'-o',str(R/name)],check=True)
  subprocess.run([str(R/name)],env={**env,'DYLD_INSERT_LIBRARIES':str(R/'noexec_guard.dylib')},check=True)
else:
 subprocess.run(['python3',str(R/'build-framework.py'),'ios'],check=True)
 dest=R/'runtime/liveexec32/host-build/ios/Payload/DungeonRaid.app/Frameworks/LiveExec32Shared.framework'
 shutil.copy2(R/'framework-ios/LiveExec32Shared.framework/LiveExec32Shared',dest/'LiveExec32Shared')
 subprocess.run(['codesign','--force','--sign','-',str(dest)],check=True)
 subprocess.run(['python3',str(R/'runtime/liveexec32/prepare-xcode-signing.py')],check=True)
 print('Open',R/'runtime/liveexec32/signing-project/DungeonRaidSigning.xcodeproj')
