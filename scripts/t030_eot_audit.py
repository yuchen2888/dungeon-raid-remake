#!/usr/bin/env python3
"""Read-only Game::EndOfTurn call inventory (T030); only --out writes the chosen JSON.

Lists every direct bl/blx (and external b.w) call site of EndOfTurn 0x13574
with its target, size and recovery status, and expands Tile::ActivateAbility
one level (enemy ability functions). Static call sites only: not a CFG and
not proof of which branches execute.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
sys.dont_write_bytecode=True
from t010_registry import ROOT, armv7_slice, disassembly

# Whole functions recovered during T020 (also listed in T020_ATTACK_CALLS.json).
T020={'__ZN4Game15ProcessVampiresEv':'dr_process_vampires','__ZN4Tile9AddHealthEi':'dr_tile_add_health',
      '__ZN4Game16InitialiseFlaresEv':'dr_initialise_flares','__ZN4Game15DoCounterattackEv':'dr_do_counterattack',
      '__ZN4Game13ProcessAttackEv':'dr_process_attack'}
# Whole functions recovered during T030.
T030={'__ZN4Game12MimicDefenceEP4Tile':'dr_mimic_defence','__ZN4Game9ResurrectEP4Tile':'dr_resurrect',
      '__ZN4Game15ProcessCripplesEv':'dr_process_cripples','__ZN4Tile18SetFlameVisibilityEbib':'dr_set_flame_visibility',
      '__ZN4Game12CheckEndGameEv':'dr_check_end_game+dr_game_over','__ZN4Game8GetScoreEv':'dr_get_score',
      '__ZN4Game12GetTotalGoldEv':'dr_total_gold','__ZN4Game10GetTotalUPEv':'dr_total_up',
      '__ZN5Skill10DeactivateEv':'inline in dr_end_turn_begin (SkillSlots.active)'}
PRESENTATION=('Quad','SimpleLabel','Interface','HelpMenu','Arrow','ScoreScreen','GameOverScreen')
PRESENTATION_GAME={'__ZN4Game10QueueSoundE5Sound','__ZN4Game16QueueAchievementE11Achievementf',
    '__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif','__ZN4Game12AddParticlesEP4Tile12ParticleType',
    '__ZN4Game8AddFlareE9FlareType8GLfloat2RK9GLcolour4','__ZN4Tile10UpdateTextEbbb',
    # Tile::SetFlameVisibility is NOT listed: it sets flaming, adds flame damage and clears freeze.
    # Display-only per T010 review / names: countdown text and enemy sprite UVs.
    '__ZN4Tile15UpdateCountdownEv','__ZN4Tile13UpdateEnemyUVEv'}

def build():
    executable_sha,read=armv7_slice(ROOT/'DungeonRaid-original')
    by_addr,by_sym=disassembly()
    old=json.loads((ROOT/'reverse-engineering/inventory.json').read_text())
    known={f['original_symbol']:'inventory46:'+f['native_function'] for f in old['recovered_flows']}
    t010=json.loads((ROOT/'docs/T010_REGISTRY.json').read_text())
    known.update({f['original_symbol']:'T010:'+f['native_function'] for f in t010['functions']})
    known.update({k:'T020:'+v for k,v in T020.items()})
    known.update({k:'T030:'+v for k,v in T030.items()})
    def classify(symbol):
        if symbol in known:return known[symbol]
        cls=re.match(r'__ZN(\d+)',symbol)
        owner=symbol[len(cls.group(0)):len(cls.group(0))+int(cls.group(1))] if cls else ''
        if symbol in PRESENTATION_GAME or owner in PRESENTATION:return 'presentation-boundary'
        return 'unrecovered'
    def calls_of(block,skip_internal=True):
        out=[]
        for line in block['body'].splitlines():
            m=re.match(r'^\s*([0-9a-f]+):\t[^\t]+\t(bl|blx|b\.w)\t(\S+)(.*)',line)
            if not m:continue
            site,op,target=int(m[1],16),m[2],m[3]
            address=by_sym[target]['start'] if target in by_sym else int(target,16)
            if op=='b.w' and block['start']<=address<block['end']:continue
            stub=re.search(r'symbol stub for: (\S+)',m[4]);label=stub[1] if stub else target
            size=by_sym[target]['end']-by_sym[target]['start'] if target in by_sym else None
            out.append(dict(site=hex(site),instruction=op,target=label,target_address=hex(address),size=size,
                            category='platform-library-boundary' if stub else classify(target)))
        return out
    block=by_sym['__ZN4Game9EndOfTurnEv']
    calls=calls_of(block)
    ability=by_sym['__ZN4Tile15ActivateAbilityEv']
    abilities=[]
    for c in calls_of(ability):
        if c['target']==ability['symbol']:continue
        abilities.append(c)
    unrecovered=sorted({(c['target'],c['size']) for c in calls+abilities if c['category']=='unrecovered'},key=lambda t:(t[1] or 0))
    return dict(task='T030',executable_sha256=executable_sha,original_symbol=block['symbol'],address=hex(block['start']),
                size=block['end']-block['start'],original_bytes_sha256=hashlib.sha256(read(block['start'],block['end']-block['start'])).hexdigest(),
                call_sites=calls,unique_targets=len({c['target'] for c in calls}),
                activate_ability=dict(address=hex(ability['start']),size=ability['end']-ability['start'],call_sites=abilities),
                unrecovered_by_size=[dict(symbol=s,size=n) for s,n in unrecovered],
                recovered_segments=[dict(start='0x13710',end_exclusive='0x13910',extra=['0x13d64..0x13d88 loop head'],
                    native_function='dr_end_turn_burn_freeze',verify='recovered/verify_turn_burn.py',
                    original_bytes_sha256=hashlib.sha256(read(0x13710,0x13910-0x13710)+read(0x13d64,0x13d88-0x13d64)).hexdigest()),
                    dict(start='0x13910',end_exclusive='0x13a1c',extra=[],native_function='dr_end_turn_regen_poison',
                    verify='recovered/verify_turn_regen.py',callbacks=['Game::CheckEndGame (not recovered; ordered callback)'],
                    original_bytes_sha256=hashlib.sha256(read(0x13910,0x13a1c-0x13910)).hexdigest()),
                    dict(start='0x10b18',end_exclusive='0x10c04',extra=[],native_function='dr_check_end_game',
                    verify='recovered/verify_check_end_game.py',status='decision/revive part; with T030-F dr_game_over (verify_game_over.py) the whole function',
                    callbacks=['game_over(win) -> dr_game_over [0x10c04,0x10dd6)'],
                    original_bytes_sha256=hashlib.sha256(read(0x10b18,0x10c04-0x10b18)).hexdigest()),
                    dict(start='0x13574',end_exclusive='0x13710',extra=[],native_function='dr_end_turn_begin',
                    verify='recovered/verify_turn_begin.py',callbacks=['check_end_game -> dr_check_end_game (whole function)'],
                    original_bytes_sha256=hashlib.sha256(read(0x13574,0x13710-0x13574)).hexdigest())],
                limits=['Direct bl/blx plus external b.w only; no indirect call graph','ActivateAbility expanded one level only',
                        'presentation-boundary is a naming heuristic (Quad/SimpleLabel/Interface/HelpMenu/Arrow/score screens and known Game presentation calls)'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--check',action='store_true')
    a=p.parse_args();data=build();text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    if a.check:
        same=a.out is not None and a.out.exists() and a.out.read_text()==text
        print(json.dumps(dict(matches=same,call_sites=len(data['call_sites']),unique_targets=data['unique_targets'],
                              unrecovered=len(data['unrecovered_by_size']))))
        return 0 if same else 1
    if a.out:a.out.write_text(text)
    else:print(text,end='')
    return 0

if __name__=='__main__':raise SystemExit(main())
