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
    # Whole functions recovered during T020 (not in inventory46 or T010).
    recovered_here={'__ZN4Game15ProcessVampiresEv':'T020-D:dr_process_vampires (recovered_encounters.cpp, verify_vampires)'}
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
        elif target in recovered_here:category=recovered_here[target]
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
                additional_recovered_partials=[dict(start=hex(0x14790),end_exclusive=hex(0x147e4),size=0x147e4-0x14790,
                    original_bytes_sha256=hashlib.sha256(read(0x14790,0x147e4-0x14790)).hexdigest(),
                    native_function='dr_process_attack_armour_absorb',source='recovered/recovered_attack_shield.cpp',
                    verify='recovered/verify_attack_absorb.py',
                    inputs=['R8=Game pointer; entry R4=Game+0xbe84, R5=Game+0xbda4, R6=0.5f from preceding phase-5 code',
                            'Game+0xbe84 incoming damage (InitialiseFlares attacker sum)','Game+0xbda4 armour',
                            'Game+0xb8a8 phase','Game+0x1553c enemy-type-9 damage label value'],
                    outputs=['R10=min(incoming,armour) consumed by shield wear','Game+0xbe84=incoming-armour (may be <=0)',
                             'phase 7 and enemy-9 label flush when nothing gets through'],
                    boundary='Partial instructions only; chained with shield wear as contiguous [0x14790,0x1487e) in the test'),
                    dict(start=hex(0x14a14),end_exclusive=hex(0x14ae4),size=0x14ae4-0x14a14,
                    original_bytes_sha256=hashlib.sha256(read(0x14a14,0x14ae4-0x14a14)).hexdigest(),
                    native_function='dr_process_attack_health_damage',source='recovered/recovered_attack_shield.cpp',
                    verify='recovered/verify_attack_health.py',
                    inputs=['R8=Game pointer; entered from 0x146d8 when the phase-5/6 label animation completes in phase 6',
                            'Game+0xbe84 remaining damage after armour','Game+0x1553c enemy-type-9 damage',
                            'Game+0x15540 poison','Game+0xbd98 health','Game+0x5994 UI health'],
                    outputs=['poison=max(enemy9,poison)','enemy9 label flush','health=max(0,health-remaining)','phase 7'],
                    callbacks=['Game::ProcessVampires 0xdaf8 (recovered as dr_process_vampires in T020-D; caller runs it on the Vampires event; only vampire tile health)'],
                    boundary='Partial instructions only; no phase animation, scheduler or game-over check')],
                limits=['Direct bl/blx plus external b.w only; no indirect call graph',
                        'Presentation categories still require validation when their real implementations are connected',
                        'DoCounterattack remains an unrecovered gameplay dependency; ProcessVampires recovered in T020-D but the health segment still reaches it through an ordered callback'])


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
