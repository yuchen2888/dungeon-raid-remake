#!/usr/bin/env python3
"""Read-only turn-scheduling call inventory (T040); only --out writes the chosen JSON.

Lists every direct bl/blx (and external b.w) call site of Game::Process 0x1717c,
Game::ProcessInput 0x16638 and Game::InitNewGame 0x15c50 with target, size and recovery
status (T010/T020/T030 registries, presentation boundary, platform library), plus the
segments of these functions recovered so far. Static call sites only: not a CFG.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
sys.dont_write_bytecode=True
from t010_registry import ROOT, armv7_slice, disassembly
import t030_eot_audit as t030

FUNCTIONS=['__ZN4Game7ProcessEv','__ZN4Game12ProcessInputEv','__ZN4Game11InitNewGameEv']
# Whole functions recovered outside the T010/T020/T030 call registries.
EXTRA={'__ZN4Game9EndOfTurnEv':'T030:dr_end_of_turn','__ZN4Game11UpdateStatsEv':'T030:dr_update_stats',
       '__ZN4Game14CountAttackersEv':'T040:dr_count_attackers','__ZN4Game16AddRevengeHealthEv':'T040:dr_add_revenge_health',
       '__ZN4Item12IncreaseStatE11UpgradeType':'T040:dr_item_increase_stat',
       '__ZN4Game22CalculateTilePositionsEv':'T040:dr_calculate_tile_positions',
       '__ZN14CharacterClass8HavePerkE8PerkType':'T040:have_perk in recovered_schedule (MatchState.perks of the active class)',
       '__Z11InterpolateRK8GLfloat2S1_f':'T040:interpolate in dr_process_damage_labels','__Z11Interpolatefff':'T040:interpolate in dr_process_damage_labels',
       '__Z3Sqrf':'T040:inline in dr_process_damage_labels',
       '__ZN4Game20ProcessShieldShatterEv':'T040:in dr_process_board_effects',
       '__ZN4Tile14SetSpecialTypeE15SpecialTileType':'T040:dr_set_special_type','__ZN4Game10ShapeshiftEv':'T040:dr_shapeshift','__ZN4Game7HealingEv':'T040:dr_healing',
       '__ZN4Game10UpdateTimeEv':'T040:platform time event of dr_process_frame','__ZN4Game12CalculateFPSEv':'T040:platform time event of dr_process_frame','__ZN4Tile14ProcessEffectsEf':'T040:in dr_process_board_effects',
       '__ZN4Game12ProcessInputEv':'T040:partial (dr_input_gate, stroke, release units; see recovered_segments)'}
SEGMENTS=[
    dict(function='__ZN4Game12ProcessInputEv',start='0x16638',end_exclusive='0x16748',native='dr_input_gate (recovered_schedule)',
         verify='recovered/verify_input_gate.py',task='T040-B'),
    dict(function='__ZN4Game12ProcessInputEv',start='0x16748',end_exclusive='0x1674e',native='dr_reset_rune_preview / in dr_input_gate',
         verify='recovered/verify_input_gate.py',task='T040-B'),
    dict(function='__ZN4Game12ProcessInputEv',start='0x16890',end_exclusive='0x16c1c',native='dr_release_path (recovered_schedule)',
         verify='recovered/verify_release.py',task='T040-C'),
    dict(function='__ZN4Game12ProcessInputEv',start='0x16c1c',end_exclusive='0x16d88',extra=['0x170b4..0x170ca','0x170de..0x170e6'],
         native='dr_release_class_scroll (recovered_schedule)',verify='recovered/verify_release.py',task='T040-C2b'),
    dict(function='__ZN4Game12ProcessInputEv',start='0x16d88',end_exclusive='0x16e10',native='dr_release_clear (recovered_schedule)',
         verify='recovered/verify_release.py',task='T040-C'),
    dict(function='__ZN4Game11InitNewGameEv',start='0x15c50',end_exclusive='0x164c0',native='dr_init_new_game (recovered_schedule)',
         verify='recovered/verify_new_game.py',task='T040-E'),
    dict(function='__ZN4Game7ProcessEv',start='0x176fc',end_exclusive='0x17cda',extra=['0x17d74..0x17da4'],
         native='dr_process_damage_labels (recovered_schedule)',verify='recovered/verify_damage_labels.py',task='T040-D1'),
    dict(function='__ZN4Game7ProcessEv',start='0x1733a',end_exclusive='0x173c8',extra=['0x17d22..0x17d32','0x17d32..0x17d56'],
         native='dr_process_board_effects (recovered_schedule)',verify='recovered/verify_board_effects.py',task='T040-D2a'),
    dict(function='__ZN4Game7ProcessEv',start='0x17400',end_exclusive='0x1744c',native='dr_reset_round_counters (recovered_schedule)',
         verify='recovered/verify_frame_parts.py',task='T040-D2b'),
    dict(function='__ZN4Game7ProcessEv',start='0x17570',end_exclusive='0x176fc',extra=['0x17d64..0x17d74'],
         native='dr_process_flare_fade + dr_process_damage_label (recovered_schedule)',verify='recovered/verify_frame_parts.py',task='T040-D2b'),
    dict(function='__ZN4Game7ProcessEv',start='0x1717c',end_exclusive='0x17db8',
         native='dr_process_frame (schedule; verified steps through GameFrameHooks)',verify='recovered/verify_frame.py',task='T040-D3'),
    dict(function='__ZN4Game12ProcessInputEv',start='0x16638',end_exclusive='0x1717c',
         native='dr_process_input (schedule; gate, stroke, release, scroll units composed)',verify='recovered/verify_process_input.py',task='T040-C3a'),
    dict(function='__ZN4Game7ProcessEv',start='0x173c8',end_exclusive='0x17400',native='moving-list subsection (recovered_refill)',
         verify='recovered/verify_refill_integration.py',task='earlier'),
    dict(function='__ZN4Game7ProcessEv',start='0x1744c',end_exclusive='0x174da',extra=['0x17d56..0x17d62'],
         native='dr_process_reward_tokens (recovered_motion)',verify='recovered/verify_motion.py',task='earlier')]

def build():
    executable_sha,read=armv7_slice(ROOT/'DungeonRaid-original')
    by_addr,by_sym=disassembly()
    old=json.loads((ROOT/'reverse-engineering/inventory.json').read_text())
    known={f['original_symbol']:'inventory46:'+f['native_function'] for f in old['recovered_flows']}
    t010=json.loads((ROOT/'docs/T010_REGISTRY.json').read_text())
    known.update({f['original_symbol']:'T010:'+f['native_function'] for f in t010['functions']})
    known.update({k:'T020:'+v for k,v in t030.T020.items()})
    known.update({k:'T030:'+v for k,v in t030.T030.items()})
    known.update(EXTRA)
    def classify(symbol):
        if symbol in known:return known[symbol]
        cls=re.match(r'__ZN(\d+)',symbol)
        owner=symbol[len(cls.group(0)):len(cls.group(0))+int(cls.group(1))] if cls else ''
        if symbol in t030.PRESENTATION_GAME or owner in t030.PRESENTATION+('SimpleLabel','Particles','Tooltip','Label',
                'MainMenu','NameScreen','IntroScreen','UnlockMenu','HelpMenu'):return 'presentation-boundary'
        return 'unrecovered'
    out={}
    for name in FUNCTIONS:
        block=by_sym[name];calls=[]
        for line in block['body'].splitlines():
            m=re.match(r'^\s*([0-9a-f]+):\t[^\t]+\t(bl|blx|b\.w)\t(\S+)(.*)',line)
            if not m:continue
            site,op,target=int(m[1],16),m[2],m[3]
            address=by_sym[target]['start'] if target in by_sym else int(target,16)
            if op=='b.w' and block['start']<=address<block['end']:continue
            stub=re.search(r'symbol stub for: (\S+)',m[4]);label=stub[1] if stub else target
            size=by_sym[target]['end']-by_sym[target]['start'] if target in by_sym else None
            calls.append(dict(site=hex(site),instruction=op,target=label,target_address=hex(address),size=size,
                              category='platform-library-boundary' if stub or not target.startswith('__') else classify(target)))
        unrecovered=sorted({(c['target'],c['size']) for c in calls if c['category']=='unrecovered'},key=lambda t:(t[1] or 0,t[0]))
        out[name]=dict(address=hex(block['start']),size=block['end']-block['start'],
                       original_bytes_sha256=hashlib.sha256(read(block['start'],block['end']-block['start'])).hexdigest(),
                       call_sites=calls,unrecovered_by_size=[dict(symbol=s,size=n) for s,n in unrecovered])
    for s in SEGMENTS:
        a,b=int(s['start'],16),int(s['end_exclusive'],16);s['original_bytes_sha256']=hashlib.sha256(read(a,b-a)).hexdigest()
    return dict(task='T040',executable_sha256=executable_sha,functions=out,recovered_segments=SEGMENTS,
                limits=['Direct bl/blx plus external b.w only; no indirect call graph',
                        'presentation-boundary is a naming heuristic (UI classes, labels, particles, menus)'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--check',action='store_true')
    a=p.parse_args();data=build();text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    if a.check:
        same=a.out is not None and a.out.exists() and a.out.read_text()==text
        print(json.dumps(dict(matches=same,**{k.replace('__ZN4Game',''):dict(calls=len(v['call_sites']),unrecovered=len(v['unrecovered_by_size']))
                                             for k,v in data['functions'].items()})))
        return 0 if same else 1
    if a.out:a.out.write_text(text)
    else:print(text,end='')
    return 0

if __name__=='__main__':raise SystemExit(main())
