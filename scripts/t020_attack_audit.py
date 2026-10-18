#!/usr/bin/env python3
"""Read-only ProcessAttack call inventory; only --out writes the chosen JSON."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
sys.dont_write_bytecode=True
from t010_registry import ROOT, armv7_slice, disassembly


def build():
    executable_sha,read=armv7_slice(ROOT/'DungeonRaid-original')
    _,by_sym=disassembly();block=by_sym['__ZN4Game13ProcessAttackEv']
    old=json.loads((ROOT/'reverse-engineering/inventory.json').read_text())
    known={int(f['address'],16):'inventory46:'+f['native_function'] for f in old['recovered_flows']}
    t010=json.loads((ROOT/'docs/T010_REGISTRY.json').read_text())
    known.update({int(f['address'],16):'T010:'+f['native_function'] for f in t010['functions']})
    gameplay={'__ZN4Game15DoCounterattackEv','__ZN4Game15ProcessVampiresEv'}
    helpers={'__Z11InterpolateRK8GLfloat2S1_f','__Z11Interpolatefff','__Z3Sqrf'}
    calls=[]
    for line in block['body'].splitlines():
        m=re.match(r'^\s*([0-9a-f]+):\t[^\t]+\t(bl|blx|b\.w)\t(\S+)(.*)',line)
        if not m:continue
        site,op,target,comment=int(m[1],16),m[2],m[3],m[4]
        address=by_sym[target]['start'] if target in by_sym else int(target,16)
        if op=='b.w' and block['start']<=address<block['end']:continue
        stub=re.search(r'symbol stub for: (\S+)',comment)
        label=target if not stub else stub[1]
        if address in known:category=known[address]
        elif target=='__Z4Randff8RandType':category='existing-source:dr_random_float (verify_motion)'
        elif target in gameplay:category='unrecovered-gameplay'
        elif target in helpers:category='math-helper; not registered as recovered function'
        elif stub:category='platform-library-boundary'
        else:category='presentation-or-achievement-boundary; not a recovered gameplay implementation'
        calls.append(dict(site=hex(site),instruction=op,target=label,target_address=hex(address),category=category))
    start,end=0x147e4,0x1487e
    return dict(task='T020',executable_sha256=executable_sha,
                original_symbol=block['symbol'],address=hex(block['start']),size=block['end']-block['start'],
                original_bytes_sha256=hashlib.sha256(read(block['start'],block['end']-block['start'])).hexdigest(),
                call_sites=calls,unique_targets=len({c['target'] for c in calls}),
                recovered_partial=dict(start=hex(start),end_exclusive=hex(end),size=end-start,
                    original_bytes_sha256=hashlib.sha256(read(start,end-start)).hexdigest(),
                    native_function='dr_process_attack_shield_wear',source='recovered/recovered_attack_shield.cpp',
                    verify='recovered/verify_attack_shield.py',
                    inputs=['R8=Game pointer','R10=previous min(incoming damage,current armour)',
                            'Game+0xbdc8 signed loss threshold','Game+0xbda4 armour','Game+0x59c0 UI armour',
                            'existing board and six RNG streams at 0x1eac20'],
                    boundary='Partial instructions only; not full ProcessAttack or new complete-function count'),
                limits=['Direct bl/blx plus external b.w only; no indirect call graph',
                        'Presentation categories still require validation when their real implementations are connected',
                        'DoCounterattack and ProcessVampires remain gameplay dependencies; phase/health logic not implemented here'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--check',action='store_true')
    a=p.parse_args();data=build();text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    if a.check:
        same=a.out is not None and a.out.exists() and a.out.read_text()==text
        print(json.dumps(dict(matches=same,call_sites=len(data['call_sites']),unique_targets=data['unique_targets'])))
        return 0 if same else 1
    if a.out:a.out.write_text(text)
    else:print(text,end='')
    return 0


if __name__=='__main__':raise SystemExit(main())
