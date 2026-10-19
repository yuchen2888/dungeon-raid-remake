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
    recovered_here={'__ZN4Game15ProcessVampiresEv':'T020-D:dr_process_vampires (recovered_encounters.cpp, verify_vampires)',
                    '__ZN4Game16InitialiseFlaresEv':'T020-H:dr_initialise_flares (recovered_attack_shield.cpp, verify_attack_flares)',
                    '__ZN4Game15DoCounterattackEv':'T020-J:dr_do_counterattack (recovered_attack_shield.cpp, verify_counterattack)'}
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
                    boundary='Partial instructions only; no phase animation, scheduler or game-over check'),
                    dict(start=hex(0x1487e),end_exclusive=hex(0x14938),size=0x14938-0x1487e,
                    original_bytes_sha256=hashlib.sha256(read(0x1487e,0x14938-0x1487e)).hexdigest(),
                    extra_blocks=[dict(start=hex(a),end_exclusive=hex(b),original_bytes_sha256=hashlib.sha256(read(a,b-a)).hexdigest())
                                  for a,b in ((0x14b56,0x14b5e),(0x14b9c,0x14bbe))],
                    native_function='dr_process_attack_weaken',source='recovered/recovered_attack_shield.cpp',
                    verify='recovered/verify_attack_weaken.py',
                    inputs=['R8=Game pointer; reached after shield wear on the phase-5 completion path',
                            'Game+0xbe6c weaken amount (producer not recovered)','tile type +0x9c, attack_flag +0x86, attack +0xa4'],
                    outputs=['attack=max(1,attack-weaken) for unattacked enemies with attack>1, column-major'],
                    boundary='Partial instructions only; continues at 0x14938 (Game+0xbe68 damage-all, not recovered)'),
                    dict(start=hex(0x14ae4),end_exclusive=hex(0x14b56),size=0x14b56-0x14ae4,
                    original_bytes_sha256=hashlib.sha256(read(0x14ae4,0x14b56-0x14ae4)).hexdigest(),
                    native_function='dr_process_attack_fade',source='recovered/recovered_attack_shield.cpp',
                    verify='recovered/verify_attack_fade.py',
                    inputs=['R8=Game pointer','Game+0xb8a8 phase','Game+0xb92b overlay quad vertex-0 alpha (phase timer)',
                            'Game+4 frame time','Game+0xbfba alternate quad flag','literal 0xc4610000 = -900.0'],
                    outputs=['alpha=trunc(alpha+dt*-900); below 0 -> 0 and phase 8','Quad::SetAlpha on overlay and Game+0xb8ac or +0xb98c'],
                    boundary='Partial instructions only; phase 8 is handled outside ProcessAttack'),
                    dict(start=hex(0x14126),end_exclusive=hex(0x141c6),size=0x141c6-0x14126,
                    original_bytes_sha256=hashlib.sha256(read(0x14126,0x141c6-0x14126)).hexdigest(),
                    native_function='dr_process_attack_fade_in',source='recovered/recovered_attack_shield.cpp',
                    verify='recovered/verify_attack_flares.py',
                    inputs=['R0=Game pointer (entry right after the prologue)','Game+0xb8a8 phase','Game+0xb92b overlay alpha','Game+4 frame time',
                            'literal 0x44480000 = 800.0'],
                    outputs=['alpha=trunc(alpha+dt*800); above 200: sound 14, phase 2, Game+0xbd90=0, +0xbd94=1.0f, InitialiseFlares, alpha 200',
                             'Quad::SetAlpha(overlay) and four Interface shadows -1'],
                    boundary='Partial instructions only; phases 2..4 not recovered'),
                    dict(start=hex(0x14938),end_exclusive=hex(0x14a14),size=0x14a14-0x14938,
                    original_bytes_sha256=hashlib.sha256(read(0x14938,0x14a14-0x14938)).hexdigest(),
                    extra_blocks=[dict(start=hex(a),end_exclusive=hex(b),original_bytes_sha256=hashlib.sha256(read(a,b-a)).hexdigest())
                                  for a,b in ((0x14b5e,0x14b9c),(0x14bbe,0x14be0))],
                    native_function='dr_process_attack_damage_all',source='recovered/recovered_attack_shield.cpp',
                    verify='recovered/verify_attack_all.py',
                    inputs=['R8=Game pointer; reached at 0x14938 after the weakening segment','Game+0xbe68 damage-all amount (producer not recovered)',
                            'tile type +0x9c, attack_flag +0x86, enemy type +0x24c'],
                    outputs=['matched_counts[0..4] cleared','AttackSkull(amount,false) per unattacked enemy, column-major',
                             'MoveMatchedTiles, then every attack_flag cleared; continues at 0x14ae4'],
                    callbacks=['Game::AttackSkull via recovered dr_path_attack_skull (integration adapter in recovered_path.cpp)',
                               'Game::MoveMatchedTiles via recovered dr_move_matched_tiles'],
                    boundary='Partial instructions only; full chain verified on shared state'),
                    dict(start=hex(0x141c6),end_exclusive=hex(0x143ca),size=0x143ca-0x141c6,
                    original_bytes_sha256=hashlib.sha256(read(0x141c6,0x143ca-0x141c6)).hexdigest(),
                    native_function='dr_process_attack_flares',source='recovered/recovered_attack_shield.cpp',
                    verify='recovered/verify_attack_flare_phases.py',
                    inputs=['R8=Game pointer; phases 2..4','Game+0xbd90/+0xbd94 timers (MatchState shake fields)','Game+4 frame time',
                            'Game+0xbd58/+0xbd54/+0xbd38/+0x15520 label animation','Game+0xbd80 flare list, +0xbd8c count','Game+0xbfba counterattack flag'],
                    outputs=['timer A += dt, timer B += dt*-4.5; below 0.5 in phase 2: phase 3 (counterattack) or 4 (labels)',
                             'below 0: timer B 0, flare count 0','flare alpha/scale','phase 3: progress += 3dt; above 1 with flares done: phase 7 + DoCounterattack'],
                    callbacks=['Game::DoCounterattack via recovered dr_do_counterattack'],
                    boundary='Partial instructions only; phase-4 work after 0x143ca not included'),
                    dict(start=hex(0x143ca),end_exclusive=hex(0x1457c),size=0x1457c-0x143ca,
                    original_bytes_sha256=hashlib.sha256(read(0x143ca,0x1457c-0x143ca)).hexdigest(),
                    native_function='dr_process_attack_phase4',source='recovered/recovered_attack_shield.cpp',
                    verify='recovered/verify_attack_phase4.py',
                    inputs=['flares-done flag [sp,#0x2c] from the shared part (returned by dr_process_attack_flares)','Game+0xbd58 progress, Game+4 frame time',
                            'Game+0xbda4 armour','Game+0xbd30/+0xbd34/+0xbd38','RNG stream 0'],
                    outputs=['progress += 8dt; above 1 with flares done: phase 5 (armour > 0) or 6 with motion parameters bd5c/bd60/bd78',
                             'Rand(0.4, 1.0 or 0.8, stream 0) -> bd7c; bd64/bd68 copies; bd6c=0, bd70=1; HelpMenu',
                             'bd74 = bd38; Quad 0xb8ac and two labels get alpha u8(u32(progress*255))'],
                    boundary='Partial instructions only; phase 5/6 animation from 0x1457c not included'),
                    dict(start=hex(0x1457c),end_exclusive=hex(0x146ce),size=0x146ce-0x1457c,
                    original_bytes_sha256=hashlib.sha256(read(0x1457c,0x146ce-0x1457c)).hexdigest(),
                    native_function='dr_process_attack_label_motion',source='recovered/recovered_attack_shield.cpp',
                    verify='recovered/verify_attack_label_motion.py',
                    inputs=['phases 5/6','Game+0xbd70 speed, +0xbd6c progress, +0xbd64/+0xbd68 from, +0xbd5c/+0xbd60 to, +0xbd7c arc, +0xbd74/+0xbd78 alphas',
                            'Game+4 frame time','literals 20, 0.5, 0.25, 5.0 (powf), 0.05'],
                    outputs=['speed += 20dt; progress += speed*dt, capped at 1 (completed -> 0x146ce, else 0x14ae4)',
                             'label positions via Interpolate(vector) minus arc on x (phase 5) or y (phase 6)',
                             'damage-label alpha = Interpolate(bd78, bd74, powf(t,5)), copied to +0x15520'],
                    callbacks=['Interpolate(vector), Interpolate(float), Sqr: math helpers reproduced inline and executed as original code in the test',
                               'powf: platform library (host C powf in both test sides)'],
                    boundary='Partial instructions only; completion block at 0x146ce not included')],
                limits=['Direct bl/blx plus external b.w only; no indirect call graph',
                        'Presentation categories still require validation when their real implementations are connected',
                        'DoCounterattack (T020-J) and ProcessVampires (T020-D) are recovered whole functions; the phase segments still reach them through ordered callbacks'])


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
