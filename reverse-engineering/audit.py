#!/usr/bin/env python3
"""Inventory existing reconstruction and extract address-backed evidence.

Only reads original inputs. No emulator, device connection or gameplay changes.
Call edges are static call sites, NOT proof of execution order or branch coverage.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

def sha(data):
    return hashlib.sha256(data).hexdigest()

class Image:
    def __init__(self, path):
        self.original = path.read_bytes()
        magic, count = struct.unpack_from('>II', self.original)
        assert magic == 0xcafebabe
        for i in range(count):
            cpu, subtype, offset, size, _ = struct.unpack_from('>5I', self.original, 8 + i * 20)
            if cpu == 12 and subtype & 0xffffff == 9:
                self.data = self.original[offset:offset + size]
                break
        else:
            raise ValueError('ARMv7 slice missing')
        header = struct.unpack_from('<7I', self.data)
        assert header[0] == 0xfeedface
        cursor = 28
        self.segments = []
        for _ in range(header[4]):
            cmd, size = struct.unpack_from('<II', self.data, cursor)
            if cmd == 1:
                fields = struct.unpack_from('<II16s8I', self.data, cursor)
                self.segments.append(fields[3:7])
            cursor += size

    def read(self, va, count):
        for start, _, offset, size in self.segments:
            if start <= va and va + count <= start + size:
                return self.data[offset + va - start:offset + va - start + count]
        raise ValueError(f'Not file backed: {va:#x}, {count}')

def write_json(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', type=Path, required=True,
                        help='Original investigation directory containing symbols/assets')
    args = parser.parse_args()
    image = Image(ROOT / 'DungeonRaid-original')
    source = (ROOT / 'armv7-disassembly.txt').read_text()
    parts = re.split(r'(?m)^(\S+):\n', source)
    blocks = []
    for i in range(1, len(parts), 2):
        symbol, body = parts[i:i+2]
        match = re.search(r'^\s*([0-9a-f]+):', body, re.M)
        if match:
            blocks.append(dict(symbol=symbol, address=int(match[1],16), body=body))
    by_address = {b['address']: b for b in blocks}
    by_symbol = {b['symbol']: b for b in blocks}
    recovered = ROOT / 'recovered'
    entries = []

    def entry(module, address, size, digest, native):
        address = int(address, 16) if isinstance(address, str) else address
        assert sha(image.read(address, size)) == digest, (module, hex(address))
        native_source = recovered / f'recovered_{module}.cpp'
        assert re.search(r'\b' + native + r'\s*\(', native_source.read_text())
        entries.append(dict(module=module, original_symbol=by_address[address]['symbol'],
                            address=hex(address), evidence_bytes=size,
                            original_bytes_sha256=digest, bytes_match_original=True,
                            native_function=native, source=str(native_source.relative_to(ROOT)),
                            source_sha256=sha(native_source.read_bytes()),
                            integration='not connected to standalone native game'))

    combat = json.loads((recovered / 'verification.json').read_text())
    for name, item in combat['original_functions'].items():
        entry('combat', item['virtual_address'], item['extracted_bytes'], item['sha256'], 'dr_' + name)
    native_names = {
        'rules': ['dr_can_match','dr_damage_type','dr_nearest_unmatched','dr_enemy_count','dr_have_flaw','dr_mortal_enemy'],
        'input': ['dr_touch_start','dr_touch_drag','dr_touch_end','dr_touch_interrupted','dr_tile_at','dr_is_selected'],
        'battle': ['dr_attack_skull','dr_make_phylactery','dr_set_freeze','dr_get_rewards'],
    }
    for module, names in native_names.items():
        records = json.loads((recovered / f'{module}_provenance.json').read_text())
        assert len(records) == len(names)
        for record, native in zip(records, names):
            entry(module, record['address'], record['size'], record['sha256'], native)
    record = json.loads((recovered / 'round_provenance.json').read_text())
    entry('round', record['address'], record['size'], record['sha256'], 'dr_match_path')
    records = json.loads((recovered / 'progression_provenance.json').read_text())
    assert records['source_executable_sha256'] == sha(image.original)
    for record in records['functions']:
        entry('progression', record['original_address'], record['bytes_with_literal_pool'],
              record['sha256'], record['native_function'])
    record = json.loads((recovered / 'selection_provenance.json').read_text())
    entry('selection', record['original_address'], record['bytes_including_literal_pool'],
          record['sha256'], 'dr_process_tile_selection')
    record = record['additional_recovered_flow']
    entry('selection', record['address'], record['bytes_including_literal_pool'],
          record['sha256'], record['native_function'])
    assert len(entries) == 33
    existing_count = len(entries)
    random_provenance = recovered / 'random_provenance.json'
    if random_provenance.exists():
        for record in json.loads(random_provenance.read_text())['functions']:
            entry('random', record['address'], record['size'], record['sha256'], record['native_function'])
    preview_provenance = recovered / 'preview_provenance.json'
    if preview_provenance.exists():
        record = json.loads(preview_provenance.read_text())
        entry('preview', record['address'], record['size'], record['sha256'], 'dr_preview_resources')
    rune_provenance = recovered / 'rune_provenance.json'
    if rune_provenance.exists():
        record = json.loads(rune_provenance.read_text())
        entry('rune', record['address'], record['size'], record['sha256'], 'dr_process_rune')
    for module,native in [('match','dr_match_tile'),('tokens','dr_enqueue_token'),('resources','dr_add_resource')]:
        provenance = recovered / f'{module}_provenance.json'
        if provenance.exists():
            record = json.loads(provenance.read_text())
            entry(module,record['address'],record['size'],record['sha256'],native)
    motion_provenance = recovered / 'motion_provenance.json'
    if motion_provenance.exists():
        for record in json.loads(motion_provenance.read_text())['functions']:
            entry(record['module'],record['address'],record['size'],record['sha256'],record['native_function'])
    partial = []
    stroke_provenance = recovered / 'stroke_provenance.json'
    if stroke_provenance.exists():
        record = json.loads(stroke_provenance.read_text())
        assert sha(image.read(int(record['address'],16),record['size'])) == record['sha256']
        partial.append(record)
    release_provenance = recovered / 'release_prefix_provenance.json'
    if release_provenance.exists():
        record = json.loads(release_provenance.read_text())
        assert sha(image.read(int(record['address'],16),record['size'])) == record['sha256']
        partial.append(record)
    token_loop_provenance = recovered / 'token_loop_provenance.json'
    if token_loop_provenance.exists():
        record = json.loads(token_loop_provenance.read_text())
        for r in record['ranges']:
            assert sha(image.read(int(r['address'],16),r['size'])) == r['sha256']
        partial.append(record)
    reports = {p.name:json.loads(p.read_text()) for p in sorted(recovered.glob('*verification*.json'))}
    write_json('inventory.json', dict(source_sha256=sha(image.original),
               scope='Existing source plus historical test reports; no gameplay tests rerun by audit',
               previous_flow_count=existing_count, recovered_flows=entries,
               partial_functions=partial, historical_reports=reports,
               integration_modules=[dict(source='recovered/recovered_path.cpp',
                   source_sha256=sha((recovered/'recovered_path.cpp').read_bytes()),
                   scope='New shared-state adapter; no additional original flow count')] if (recovered/'recovered_path.cpp').exists() else []))

    prefixes = ('__ZN4Game', '__ZN4Tile', '__ZN5Token', '__ZN5Skill', '__ZN14CharacterClass')
    edges = []
    for block in blocks:
        if not block['symbol'].startswith(prefixes):
            continue
        for line in block['body'].splitlines():
            m = re.match(r'\s*([0-9a-f]+):.*\t(bl|blx|b\.w)\t(\S+)(?: @ (.*))?', line)
            if m and m[3].startswith('__Z'):
                edges.append(dict(caller=block['symbol'], site='0x'+m[1],
                                  instruction=m[2], callee=m[3], label=m[4]))
    write_json('static-call-sites.json', dict(scope='Direct named calls only; excludes indirect calls, not a complete CFG', edges=edges))
    targets = ['12ProcessInputEv','7ProcessEv','9EndOfTurnEv','13ProcessAttackEv',
               '9MatchTileEP4Tile8TileType','11AddResourceE8TileType9TokenTypei',
               '11InitNewGameEv','13RandomiseTileER4Tile','16MoveMatchedTilesEv',
               '12PositionTileER4Tileiib','14CountAttackersEv','11ProcessRuneEb','22ProcessResourceShadowsEv',
               '8AddTokenEP4Tile8TileTypebPK8GLfloat2']
    selected = ['__ZN4Game'+name for name in targets]
    selected += ['__ZN5Token7ProcessEf','__ZN5Token18InitialiseFromTileEP4Tile8TileTypePK8GLfloat29TokenType',
                 '__ZN4Tile13GenerateStatsEii','__ZN4Tile7SetTypeE8TileTypeii',
                 '__Z9RandUnitFRj','__Z5RandIii8RandType','__Z4Randff8RandType',
                 '__Z11SetRandSeedj8RandType','__Z11GetRandSeed8RandType','__Z14FlushRandSeedsv']
    evidence = HERE / 'evidence'
    evidence.mkdir(exist_ok=True)
    for symbol in selected:
        b = by_symbol[symbol]
        (evidence / (symbol+'.asm')).write_text(symbol+':\n'+b['body'])
    assets = []
    for path in sorted((args.reference / 'decoded-assets').glob('*.png')):
        data = path.read_bytes()
        assert data[:8] == b'\x89PNG\r\n\x1a\n'
        assets.append(dict(name=path.name, width=struct.unpack_from('>I',data,16)[0],
                           height=struct.unpack_from('>I',data,20)[0], sha256=sha(data)))
    fonts = []
    for path in sorted((args.reference / 'original-assets').glob('*.fnt')):
        ids = [int(n) for n in re.findall(r'(?m)^char\s+id=(-?\d+)',path.read_text())]
        fonts.append(dict(name=path.name,glyph_count=len(ids),max_id=max(ids),
                          cjk_glyph_count=sum(0x3400<=n<=0x9fff for n in ids)))
    write_json('assets.json', dict(images=assets, fonts=fonts,
               note='Image dimensions are whole atlas dimensions, not individual tile resolution.'))

    # Getter strides and PC-relative literal locations read from original Thumb code.
    # Each base address is independently checked against the original symbol table.
    tables = [
        ('skill.name','_g_skillNames',0x2ab68,0x2ab78,0x2ab70,18,40),
        ('skill.description','_g_skillDescriptions',0x2ab7c,0x2ab8c,0x2ab84,120,40),
        ('enemy.name','_g_enemyNames',0x3d348,0x3d35c,0x3d354,13,33),
        ('enemy.description','_g_enemyText',0x3d360,0x3d374,0x3d36c,150,33),
    ]
    for key,symbol,va,stride in [
        ('class.name','_g_classNames',0x111650,32),('race.name','_g_raceNames',0x111660,32),
        ('perk.name','_g_perkNames',0x111670,32),('flaw.name','_g_flawNames',0x111680,32),
        ('perk.description','_g_perkDescriptions',0x111690,128),
        ('flaw.description','_g_flawDescriptions',0x1116a0,128),
        ('race.bonus_name','_g_racialBonusNames',0x1116b0,128),
        ('race.bonus_description','_g_racialBonusDescriptions',0x1116c0,256),
        ('race.enemy_description','_g_mortalEnemyDescriptions',0x1116d0,256),
        ('class.unlock_description','_g_classUnlockDescriptions',0x1116e0,256)]:
        tables.append((key,symbol,va,va+12,va+4,stride,10))
    symbols = {m[2]:int(m[1],16) for m in re.finditer(
        r'(?m)^([0-9a-f]{8}) \w (\S+)$',(args.reference/'symbols.txt').read_text())}
    strings, table_evidence = [], []
    for key,symbol,getter,literal,add_pc,stride,count in tables:
        base = add_pc + 4 + struct.unpack('<I',image.read(literal,4))[0]
        assert base == symbols[symbol], (symbol,hex(base),hex(symbols[symbol]))
        raw = image.read(base,stride*count)
        for i in range(count):
            record = raw[i*stride:(i+1)*stride]
            assert b'\0' in record
            value = record.split(b'\0',1)[0].decode('utf-8')
            strings.append(dict(key=f'{key}.{i:02d}',en=value,zh_Hans=None,
                                original_address=hex(base+i*stride),table=symbol,index=i))
        table_evidence.append(dict(key=key,symbol=symbol,address=hex(base),getter=hex(getter),
                                   stride=stride,count=count,bytes_sha256=sha(raw)))
    write_json('localization-source.json', dict(scope='14 named fixed-width tables only; menus, help, intro and dynamic format strings incomplete',
               original_sha256=sha(image.original), translation_status='not translated',
               tables=table_evidence,strings=strings))
    print(json.dumps(dict(recovered_flows=len(entries),hash_checks='passed',
                         direct_call_sites=len(edges),extracted_strings=len(strings),
                         tables=len(tables),fonts=fonts),ensure_ascii=False))

if __name__ == '__main__':
    main()
