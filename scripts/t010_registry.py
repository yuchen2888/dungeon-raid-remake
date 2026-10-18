#!/usr/bin/env python3
"""T010: address-backed registry for the refill / generation / encounters modules.

Read-only with respect to original inputs and recovered/. It only writes the
output JSON (default docs/T010_REGISTRY.json); `--check` writes nothing and
fails if the committed registry differs from a fresh extraction.

Every hand-written claim below (callback -> original symbol, native state ->
original offset) is asserted against a literal snippet in the verify script
that exercises it, so the registry cannot silently drift from the tests.
Static callees include only direct bl/blx/b.w targets named with __Z (C++).
Numeric-address platform stubs and indirect calls are excluded. This is not
a CFG or proof of execution order.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import struct
import sys

ROOT = Path(__file__).resolve().parent.parent
REC = ROOT / 'recovered'
OUT = ROOT / 'docs' / 'T010_REGISTRY.json'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def armv7_slice(path):
    raw = path.read_bytes()
    magic, count = struct.unpack_from('>II', raw)
    assert magic == 0xcafebabe
    for i in range(count):
        cpu, subtype, offset, size, _ = struct.unpack_from('>5I', raw, 8 + i * 20)
        if cpu == 12 and subtype & 0xffffff == 9:
            data = raw[offset:offset + size]
            break
    else:
        raise ValueError('ARMv7 slice missing')
    header = struct.unpack_from('<7I', data)
    assert header[0] == 0xfeedface
    cursor, segments = 28, []
    for _ in range(header[4]):
        cmd, size = struct.unpack_from('<II', data, cursor)
        if cmd == 1:
            segments.append(struct.unpack_from('<II16s8I', data, cursor)[3:7])
        cursor += size
    def read(va, n):
        for start, _, off, sz in segments:
            if start <= va and va + n <= start + sz:
                return data[off + va - start:off + va - start + n]
        raise ValueError(f'not file backed: {va:#x}+{n}')
    return sha(raw), read

def disassembly():
    text = (ROOT / 'armv7-disassembly.txt').read_text()
    parts = re.split(r'(?m)^(\S+):\n', text)
    blocks = []
    for i in range(1, len(parts), 2):
        symbol, body = parts[i:i + 2]
        lines = re.findall(r'(?m)^\s*([0-9a-f]+):\t([0-9a-f]{2}(?: [0-9a-f]{2})*)\t', body)
        if lines:
            start = int(lines[0][0], 16)
            end = int(lines[-1][0], 16) + len(lines[-1][1].split())
            blocks.append(dict(symbol=symbol, start=start, end=end, body=body))
    blocks.sort(key=lambda b: b['start'])
    for a, b in zip(blocks, blocks[1:]):
        a['next_start'] = b['start']
    return {b['start']: b for b in blocks}, {b['symbol']: b for b in blocks}

# module, original symbol, native function, verify script containing the address literal.
FUNCTIONS = [
    ('refill', '__ZN4Game12PositionTileER4Tileiib', 'dr_position_tile', 'verify_refill.py'),
    ('refill', '__ZN4Game16MoveMatchedTilesEv', 'dr_move_matched_tiles', 'verify_refill.py'),
    ('refill', '__ZN4Tile7ProcessEf', 'dr_process_falling_tile', 'verify_refill.py'),
    ('refill', '__ZN4Game9SwapTilesEiiii', 'dr_swap_tiles', 'verify_encounters.py'),
    ('generation', '__ZN4Tile13GenerateStatsEii', 'dr_generate_stats', 'verify_generation.py'),
    ('generation', '__ZN4Tile7SetTypeE8TileTypeii', 'dr_set_tile_type', 'verify_generation.py'),
    ('generation', '__ZN4Tile7PromoteEiib', 'dr_promote_tile', 'verify_generation.py'),
    ('generation', '__ZN4Game13RandomiseTileER4Tile', 'dr_randomise_tile', 'verify_generation.py'),
    ('generation', '__ZN4Tile9MakeArrowEv', 'dr_make_arrow', 'verify_generation.py'),
    ('generation', '__ZN4Tile14MakeManaPotionEv', 'dr_make_mana_potion', 'verify_generation.py'),
    ('generation', '__ZN4Tile10MakeBrokenEv', 'dr_make_broken', 'verify_generation.py'),
    ('generation', '__ZN4Tile12UpdateValuesEv', 'dr_update_generated_values', 'verify_generation.py'),
    ('generation', '__ZN4Game15IsTimeToPromoteEv', 'dr_time_to_promote', 'verify_generation.py'),
    ('generation', '__ZN4Game18SetTimeToPromotionEi', 'dr_set_time_to_promotion', 'verify_generation.py'),
    ('generation', '__ZN4Game10GetTotalXPEv', 'dr_generation_total_xp', 'verify_generation.py'),
    ('encounters', '__ZN4Game4StabEP4Tile', 'dr_stab', 'verify_encounters.py'),
    ('encounters', '__ZN4Game8JumpDownEP4Tile', 'dr_jump_down', 'verify_encounters.py'),
]

# Partial range: Game::Process falling-list loop. Header comment gives
# 0x173c8..0x173ff; the integration test enters at 0x173c9 (Thumb) and stops
# at 0x17400 or at the token subsection 0x1744c.
PARTIAL = dict(module='refill', original_symbol='__ZN4Game7ProcessEv', native_function='dr_process_falling_list',
               start=0x173c8, end=0x17400, verify='verify_refill_integration.py',
               snippets=['emu_start(0x173c9', '[0x17400,0x1744c]'],
               header_snippet='0x173c8..0x173ff')

# Hook event -> original callee, with the verify-script literal that maps it.
HOOKS = {
    'refill': ('RefillHooks.event', 'verify_refill.py', [
        ('Swap', '__ZSt4swapI4TileEvRT_S2_', "'swap'", 'extra per-tile state swap; std::swap of 608-byte Tile done natively'),
        ('AppendMoving', 'moving list push (Game+0xb3f8)', 'GAME+0xb3f8', 'caller owns moving-list container'),
        ('Randomise', '__ZN4Game13RandomiseTileER4Tile', "'randomise'", 'recovered: caller should invoke dr_randomise_tile'),
        ('Stab', '__ZN4Game4StabEP4Tile', "'stab'", 'recovered: caller should invoke dr_stab, pointer order via std::set'),
    ]),
    'generation': ('GenerationHooks.event', 'verify_generation.py', [
        ('Random', '__Z5RandIii8RandType', '0x1bca0', 'trace only; value comes from recovered dr_random_int'),
        ('Colour', '__ZN4Quad9SetColourERK9GLcolour4', "'colour'", 'render'),
        ('UV', '__ZN4Quad5SetUVEffff', "'uv'", 'render'),
        ('Text', '__ZN4Tile10UpdateTextEbbb', "'text'", 'render, not recovered'),
        ('Countdown', '__ZN4Tile15UpdateCountdownEv', "'countdown'", 'UI countdown text/label placement only; no gameplay countdown mutation; not recovered'),
        ('EnemyUV', '__ZN4Tile13UpdateEnemyUVEv', "'enemy_uv'", 'render'),
        ('Sound', '__ZN4Game10QueueSoundE5Sound', "'sound'", 'audio'),
        ('Achievement', '__ZN4Game16QueueAchievementE11Achievementf', "'achievement'", 'platform'),
        ('ShieldValue', '__ZN9Interface17UpdateShieldValueEv', "'shield'", 'UI'),
        ('ShieldShatter', '__ZN4Game21InialiseShieldShatterEv', "'shatter'", 'UI effect'),
        ('JumpDown', '__ZN4Game8JumpDownEP4Tile', "'jump'", 'recovered: caller should invoke dr_jump_down'),
    ]),
    'encounters': ('EncounterHooks.event (+ .refill for SwapTiles)', 'verify_encounters.py', [
        ('Sound', '__ZN4Game10QueueSoundE5Sound', "'sound'", 'audio'),
        ('Label', '__ZN4Game14AddSimpleLabelE15SimpleLabelTypeRK8GLfloat2iif', "'label'", 'UI'),
        ('HealthBar', '__ZN9Interface15UpdateHealthBarER4Quadi', "'health'", 'UI'),
        ('PoisonPosition', '__ZN9Interface17GetPoisonPositionEv', "'poison'", 'UI query; test returns fixed (.1,.1)'),
        ('CheckEndGame', '__ZN4Game12CheckEndGameEv', "'end'", 'NOT recovered; test forces return 0 -> game-over path unverified'),
        ('Flare', '__ZN4Game8AddFlareE9FlareType8GLfloat2RK9GLcolour4', "'flare'", 'render'),
    ]),
}

# Native state -> original location; snippet must appear in the named file.
STATE = {
    'refill': [
        ('RefillState.falling[].target/moving/speed/acceleration', 'Tile fields used by Tile::Process', 'verify_refill.py', '0x3d1d0'),
        ('board tiles (SelectionState.tiles, 608-byte Tile swap)', 'Tile[36]', 'verify_refill.py', 'mem_read(r[0],608)'),
        ('resting_position table', 'Game+0xb400 (8-byte stride)', 'verify_refill.py', 'GAME+0xb400+8*i'),
        ('moving list (caller-owned)', 'Game+0xb3f8', 'verify_refill.py', 'GAME+0xb3f8'),
    ],
    'generation': [
        ('GenerationState.time_to_promotion', 'Game+0x14af0', 'verify_generation.py', 'time_to_promotion=0x14af0'),
        ('GenerationState.generated_count', 'Game+0x165c0', 'verify_generation.py', 'generated_count=0x165c0'),
        ('GenerationState.generated_enemies', 'Game+0x165c4', 'verify_generation.py', 'generated_enemies=0x165c4'),
        ('GenerationState.promotion_enabled', 'Game+0x14af4', 'verify_generation.py', 'promotion_enabled=0x14af4'),
        ('GenerationState.one_health', 'Game+0x14af5', 'verify_generation.py', 'one_health=0x14af5'),
        ('GenerationState.force_coins', 'Game+0x14af6', 'verify_generation.py', 'force_coins=0x14af6'),
        ('GenerationState.inhibit_force_coins', 'Game+0x15563', 'verify_generation.py', 'inhibit_force_coins=0x15563'),
        ('GenerationState.filter_enabled/filter_swords', 'Game+0xbfb8/+0xbfb9', 'verify_generation.py', 'filter_enabled=0xbfb8,filter_swords=0xbfb9'),
        ('GeneratedTile.variant', 'Tile+0x22c', 'verify_generation.py', "base+0x22c"),
        ('GeneratedTile.max_health', 'Tile+0xb0', 'verify_generation.py', "base+0xb0"),
        ('GeneratedTile.label_offset', 'Tile+0xb4', 'verify_generation.py', "base+0xb4"),
        ('GeneratedTile.flag_224', 'Tile+0x224', 'verify_generation.py', "base+0x224"),
        ('PreviewState.armour_current / ResourceState.ui_armour', 'Game+0xbda4 / Game+0x59c0', 'verify_generation.py', 'GAME+0xbda4'),
        ('RNG seeds (6 streams)', '0x1eac20', 'verify_generation.py', '0x1eac20'),
    ],
    'encounters': [
        ('ResourceState.health', 'Game+0xbd98', 'verify_encounters.py', 'GAME+0xbd98'),
        ('ResourceState.ui_health', 'Game+0x5994', 'verify_encounters.py', 'GAME+0x5994'),
        ('MatchState.shake_progress_bd90/shake_scale_bd94', 'Game+0xbd90/+0xbd94', 'verify_encounters.py', 'GAME+0xbd90'),
        ('JumpDown column read', 'Tile+0x74', 'verify_encounters.py', 'r[1]+0x74'),
    ],
}

# Callees with no recovered function of their own: replaced inline or by
# native containers. Snippet must appear in the module source.
INLINE = {
    '__ZN14CharacterClass8HavePerkE8PerkType': ('generation', 'bool perk(', 'inline perk scan over MatchState.perks'),
    '__ZN4Game20GetSpecialEnemyCountEv': ('generation', 'v.rule.enemy_type)++n', 'inline count in dr_promote_tile (achievement when >2)'),
    '__ZNSt3setIP4TileSt4lessIS1_ESaIS1_EE6insertERKS1_': ('refill', 'bool stab[36]', 'std::set<Tile*> -> index-ordered bool array (tiles contiguous, so pointer order)'),
    '__ZNSt8_Rb_treeIP4TileS1_St9_IdentityIS1_ESt4lessIS1_ESaIS1_EE13_Rb_tree_implIS5_Lb0EEC2ERKSaISt13_Rb_tree_nodeIS1_EERKS5_': ('refill', 'bool stab[36]', 'std::set construction'),
    '__ZNSt8_Rb_treeIP4TileS1_St9_IdentityIS1_ESt4lessIS1_ESaIS1_EE8_M_eraseEPSt13_Rb_tree_nodeIS1_E': ('refill', 'bool stab[36]', 'std::set destruction'),
    '__ZNSt4listIP4TileSaIS1_EE9push_backERKS1_': ('refill', 'RefillEventKind::AppendMoving', 'moving list push_back -> AppendMoving hook'),
}

REPORTS = {'refill': 'refill_verification.json', 'generation': 'generation_verification.json',
           'encounters': 'encounters_verification.json', 'integration': 'refill_integration_verification.json'}

def latest_run(pinned=None):
    runs = sorted((ROOT / '.relay' / 'runs').glob('*/result.json'))
    if pinned:
        runs = [r for r in runs if r.parent.name == pinned]
    for path in reversed(runs):
        result = json.loads(path.read_text())
        if result.get('status') == 'passed' and result.get('full'):
            return path.parent, result
    return None, None

def build(pinned_run=None):
    exe_sha, read = armv7_slice(ROOT / 'DungeonRaid-original')
    by_addr, by_sym = disassembly()
    inventory = json.loads((ROOT / 'reverse-engineering' / 'inventory.json').read_text())
    old = {int(f['address'], 16): f for f in inventory['recovered_flows']}
    old_native = {f['native_function'] for f in inventory['recovered_flows']}
    scripts = {p.name: p.read_text() for p in REC.glob('verify_*.py')}
    sources = {m: (REC / f'recovered_{m}.cpp') for m in ('refill', 'generation', 'encounters')}
    mine = {sym for _, sym, _, _ in FUNCTIONS}
    hook_syms = {sym for _, _, items in HOOKS.values() for _, sym, _, _ in items}
    problems = []

    functions = []
    for module, symbol, native, verify in FUNCTIONS:
        b = by_sym[symbol]
        size = b['end'] - b['start']
        evidence = ROOT / 'reverse-engineering' / 'evidence' / (symbol + '.asm')
        src = sources[module].read_text()
        callees = sorted({m[1] for m in re.finditer(r'\t(?:bl|blx|b\.w)\t(__Z\S+)', b['body'])} - {symbol})
        def classify(c):
            if c in mine: return 'T010'
            if by_sym.get(c) and by_sym[c]['start'] in old: return 'inventory46:' + old[by_sym[c]['start']]['native_function']
            if c in hook_syms: return 'hook'
            if c in INLINE: return 'native-inline'
            return 'unmodelled'
        record = dict(
            module=module, original_symbol=symbol, address=hex(b['start']), size=size,
            original_bytes_sha256=sha(read(b['start'], size)),
            contiguous_with_next_symbol=b.get('next_start') == b['end'],
            native_function=native, source=str(sources[module].relative_to(ROOT)),
            native_defined=bool(re.search(r'\b' + native + r'\s*\(', src)),
            evidence_asm=evidence.exists() and evidence.read_text() == symbol + ':\n' + b['body'],
            verify_script='recovered/' + verify,
            verify_references_address=bool(re.search(rf'0x{b["start"]:x}\b', scripts[verify])),
            in_inventory46=b['start'] in old,
            static_callees=[dict(symbol=c, status=classify(c)) for c in callees])
        if not record['native_defined']: problems.append(f'{native} missing in {record["source"]}')
        if not record['verify_references_address']: problems.append(f'{verify} lacks {record["address"]}')
        if record['in_inventory46'] or native in old_native: problems.append(f'{symbol} already in inventory46')
        functions.append(record)

    p = PARTIAL
    owner = [b for b in by_addr.values() if b['start'] <= p['start'] < b['end']]
    assert len(owner) == 1 and owner[0]['symbol'] == p['original_symbol'], owner
    for s in p['snippets']:
        if s not in scripts[p['verify']]: problems.append(f'{p["verify"]} lacks {s}')
    if p['header_snippet'] not in (REC / 'recovered_refill.hpp').read_text(): problems.append('refill header range')
    for r in inventory['partial_functions']:
        for rng in r.get('ranges', []):
            a = int(rng['address'], 16)
            if a < p['end'] and p['start'] < a + rng['size']: problems.append('partial range overlaps inventory46')
    partial = dict(module=p['module'], original_symbol=p['original_symbol'], native_function=p['native_function'],
                   address=hex(p['start']), size=p['end'] - p['start'],
                   original_bytes_sha256=sha(read(p['start'], p['end'] - p['start'])),
                   verify_script='recovered/' + p['verify'], status='partial: falling-list subsection only, not Game::Process')

    hooks = {}
    for module, (struct_name, verify, items) in HOOKS.items():
        rows = []
        for event, symbol, snippet, note in items:
            if snippet not in scripts[verify]: problems.append(f'{verify} lacks hook literal {snippet}')
            if symbol.startswith('__Z') and symbol not in by_sym: problems.append(f'no symbol {symbol}')
            rows.append(dict(event=event, original_callee=symbol,
                             original_address=hex(by_sym[symbol]['start']) if symbol in by_sym else None,
                             recovered=symbol in mine or (symbol in by_sym and by_sym[symbol]['start'] in old),
                             note=note))
        hooks[module] = dict(hook=struct_name, verify_script='recovered/' + verify, events=rows)

    state = {}
    for module, items in STATE.items():
        rows = []
        for native, original, verify, snippet in items:
            if snippet not in scripts[verify]: problems.append(f'{verify} lacks state literal {snippet}')
            rows.append(dict(native=native, original=original, verify_script='recovered/' + verify))
        state[module] = rows

    reports = {}
    run_dir, run = latest_run(pinned_run)
    for key, name in REPORTS.items():
        hist = json.loads((REC / name).read_text())
        entry = dict(historical=dict(path='recovered/' + name, status=hist.get('status'),
                                     counts={k: v for k, v in hist.items() if isinstance(v, (int, dict)) and k != 'status'}))
        if run_dir:
            fresh = run_dir / 'work' / 'recovered' / name
            if fresh.exists():
                f = json.loads(fresh.read_text())
                entry['latest_full_run'] = dict(run=run_dir.name, fingerprint=run['fingerprint'], status=f.get('status'),
                                                matches_historical_counts=all(f.get(k) == v for k, v in entry['historical']['counts'].items()))
        reports[key] = entry

    inline = []
    for symbol, (module, snippet, note) in INLINE.items():
        if snippet not in sources[module].read_text(): problems.append(f'{module} source lacks {snippet}')
        inline.append(dict(original_callee=symbol, original_address=hex(by_sym[symbol]['start']),
                           replaced_in=str(sources[module].relative_to(ROOT)), note=note))
    unmodelled = sorted({c['symbol'] for f in functions for c in f['static_callees'] if c['status'] == 'unmodelled'})
    return dict(
        task='T010', scope='refill/generation/encounters only; read-only extraction from original ARMv7 slice and disassembly',
        executable_sha256=exe_sha,
        counting=dict(inventory46_flows=len(inventory['recovered_flows']), new_full_functions=len(functions),
                      new_partial_ranges=1, overlap_with_inventory46=sum(f['in_inventory46'] for f in functions),
                      note='Separate list; do not add to 46 as a completion percentage. Overlapping test scenarios are not summed.'),
        functions=functions, partial_ranges=[partial], hooks=hooks, state=state, reports=reports,
        native_inline_callees=inline, unmodelled_static_callees=unmodelled,
        boundaries=['No full ProcessAttack 0x14118 / EndOfTurn 0x13574 / Game::Process',
                    'CheckEndGame not recovered; encounters test forces it to return 0',
                    'Static callees include direct __Z C++ symbols only; numeric-address platform stubs and indirect calls excluded; not proof of executed branches'],
        problems=problems)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='compare with committed registry, write nothing')
    ap.add_argument('--out', type=Path, default=OUT)
    args = ap.parse_args()
    pinned = None
    if args.check and args.out.exists():
        # Compare against the same full run the committed registry recorded.
        old = json.loads(args.out.read_text())
        pinned = next((r['latest_full_run']['run'] for r in old['reports'].values() if 'latest_full_run' in r), None)
    data = build(pinned)
    text = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    if data['problems']:
        print('\n'.join(data['problems']), file=sys.stderr)
    if args.check:
        same = args.out.exists() and args.out.read_text() == text
        print(json.dumps(dict(matches=same, problems=len(data['problems']), functions=len(data['functions']))))
        return 0 if same and not data['problems'] else 1
    args.out.write_text(text)
    print(json.dumps(dict(out=str(args.out), functions=len(data['functions']),
                          problems=len(data['problems']), unmodelled=len(data['unmodelled_static_callees']))))
    return 1 if data['problems'] else 0

if __name__ == '__main__':
    sys.exit(main())
