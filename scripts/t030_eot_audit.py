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
      '__ZN5Skill10DeactivateEv':'inline in dr_end_turn_begin (SkillSlots.active)',
      '__ZN4Tile15ActivateAbilityEv':'dr_activate_ability (unrecovered abilities via TurnHooks.ability)',
      '__ZN4Game12RunAwayEnemyEP4Tile':'dr_run_away_enemy','__ZN4Game12ExplodeEnemyEP4Tile':'dr_explode_enemy',
      '__ZN4Game13TeleportEnemyEv':'dr_teleport_enemy','__ZN4Game11LowerSkullsEP4Tile':'dr_lower_skulls',
      '__ZN4Game6FleeUpEP4Tile':'dr_flee_up','__ZN4Game11IgniteTilesEP4Tile':'dr_ignite_tiles',
      '__ZN4Game10StabAttackEP4Tile':'dr_stab_attack','__ZN4Game19ConvertSwordToSkullEP4Tile':'dr_convert_sword_to_skull',
      '__ZN4Game14MakeAcidPotionEP4Tile':'dr_make_acid_potion','__ZN4Game11FreezeTilesEP4Tile':'dr_freeze_tiles',
      '__ZN4Game22BreakRandomShieldSwordEP4Tile':'dr_break_random_shield_sword',
      '__ZN4Game18ConvertRandomTilesEP4Tile':'dr_convert_random_tiles','__ZN4Game9JumpEnemyEP4Tile':'dr_jump_enemy',
      '__ZN4Game13AttractSkullsEP4Tile':'dr_attract_skulls','__ZN4Game20AttractShieldsSwordsEP4Tile':'dr_attract_shields_swords',
      '__ZN4Game11HealOrBlessEP4Tile':'dr_heal_or_bless (incl. the std::set overload)',
      '__ZN4Game10ThrowSkullEP4Tile':'dr_throw_skull (token via dr_token_queue_push)',
      '__ZN4Game9StealGoldEP4Tile':'dr_steal_gold (incl. the std::set overload; Token::SetTargetTile via dr_token_set_target_tile)',
      '__ZN4Game14DestroyUpgradeEP4Tile':'dr_destroy_upgrade (recovered_stats; wired via TurnHooks.ability(28))'}
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
    unrecovered=sorted({(c['target'],c['size']) for c in calls+abilities if c['category']=='unrecovered'},key=lambda t:(t[1] or 0,t[0]))
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
                    original_bytes_sha256=hashlib.sha256(read(0x13574,0x13710-0x13574)).hexdigest()),
                    dict(start='0x13a1c',end_exclusive='0x13af2',extra=['0x13d88..0x13daa loop head'],native_function='dr_end_turn_poison_enemies',
                    verify='recovered/verify_turn_poison.py',callbacks=['match_tile -> dr_match_tile'],
                    original_bytes_sha256=hashlib.sha256(read(0x13a1c,0x13af2-0x13a1c)+read(0x13d88,0x13daa-0x13d88)).hexdigest()),
                    dict(start='0x13b3c',end_exclusive='0x13cda',extra=['0x13d12..0x13d64 attack_flag clear and help loop tail','0x13dc8..0x13e04 help loop heads'],
                    native_function='dr_end_turn_finish',verify='recovered/verify_turn_finish.py',
                    callbacks=['check_end_game -> dr_check_end_game (whole function, twice)','move_matched_tiles -> dr_move_matched_tiles',
                               'HelpMenu::Initialise and Game::SerialiseState are events (boundaries)'],
                    original_bytes_sha256=hashlib.sha256(read(0x13b3c,0x13cda-0x13b3c)+read(0x13d12,0x13d64-0x13d12)+read(0x13dc8,0x13e04-0x13dc8)).hexdigest()),
                    dict(start='0x13cda',end_exclusive='0x13d12',extra=['0x13af2..0x13b3c ProcessCripples and ability loop','0x13daa..0x13dc8 loop head'],
                    native_function='dr_end_turn_abilities',verify='recovered/verify_turn_abilities.py',
                    callbacks=['ActivateAbility -> dr_activate_ability (verify_activate_ability.py)','19 unrecovered ability functions via TurnHooks.ability'],
                    original_bytes_sha256=hashlib.sha256(read(0x13cda,0x13d12-0x13cda)+read(0x13af2,0x13b3c-0x13af2)+read(0x13daa,0x13dc8-0x13daa)).hexdigest()),
                    dict(start=hex(block['start']),end_exclusive=hex(block['end']),extra=[],native_function='dr_end_of_turn',verify='recovered/verify_end_of_turn.py',
                    status='whole function: composition of the segments above, differential from entry to return',
                    callbacks=['19 unrecovered ability functions via TurnHooks.ability','Game::SerialiseState event (save format not recovered)'],
                    original_bytes_sha256=hashlib.sha256(read(block['start'],block['end']-block['start'])).hexdigest())],
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
