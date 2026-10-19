#!/usr/bin/env python3
"""Build fresh copies and run existing verification without replacing old evidence."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def inputs(root):
    files = [p for p in (root / 'recovered').iterdir()
             if p.suffix in ('.cpp', '.hpp', '.py', '.sh', '.bin')]
    files += [root / n for n in ('DungeonRaid-original', 'armv7-disassembly.txt',
              'runtime/liveexec32/original-progression-verification.json',
              'recovered/crossing_boundary_paths.json', 'tools/unicorn/lib/libunicorn.2.dylib')]
    files += list((root / 'tools/unicorn').rglob('*.py'))
    return sorted(files)


def fingerprint(root):
    h = hashlib.sha256()
    for path in inputs(root):
        h.update(str(path.relative_to(root)).encode())
        h.update(hashlib.sha256(path.read_bytes()).digest() if path.is_file() else b'MISSING')
    return h.hexdigest()


def run(full=False):
    local = ROOT / '.relay'
    dest = local / 'runs' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    work = dest / 'work'; work.mkdir(parents=True)
    report = dict(status='running', run=str(dest), full=full, fingerprint=fingerprint(ROOT), steps=[])

    def save():
        text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
        (dest / 'result.json').write_text(text)
        temp = local / ('validation-' + dest.name + '.tmp')
        temp.write_text(text); temp.replace(local / 'latest-validation.json')

    save()
    try:
        for path in inputs(ROOT):
            target = work / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        env = dict(os.environ, RAID_UNICORN_TCI='1', PYTHONDONTWRITEBYTECODE='1')
        jobs = [('build', ['sh', 'recovered/build.sh']),
                ('stroke_demo', ['sh', 'recovered/run_stroke_demo.sh']),
                ('rewards_demo', ['sh', 'recovered/run_rewards_demo.sh'])]
        names = [p.stem for p in sorted((work / 'recovered').glob('verify_*.py'))] if full else [
            'verify_refill', 'verify_generation', 'verify_encounters', 'verify_refill_integration', 'verify_attack_shield', 'verify_attack_absorb', 'verify_attack_health', 'verify_vampires', 'verify_attack_vampires', 'verify_attack_weaken', 'verify_attack_fade', 'verify_attack_flares', 'verify_attack_all', 'verify_counterattack']
        jobs += [(name, [sys.executable, 'recovered/' + name + '.py']) for name in names]
        for name, command in jobs:
            start = time.monotonic()
            log = dest / (name + '.log')
            step = dict(name=name, command=command, log=str(log), status='running')
            report['steps'].append(step); save()
            print('运行：', name, flush=True)
            with log.open('wb') as stream:
                try:
                    code = subprocess.run(command, cwd=work, env=env, stdout=stream,
                                          stderr=subprocess.STDOUT, timeout=600).returncode
                except subprocess.TimeoutExpired:
                    code = 124
            step.update(status='passed' if code == 0 else 'failed', exit_code=code,
                        seconds=round(time.monotonic() - start, 2)); save()
            print(name, step['status'], step['seconds'], '秒', flush=True)
            if name == 'build' and code:
                break
        report['status'] = 'passed' if all(s['status'] == 'passed' for s in report['steps']) else 'failed'
        report['inputs_unchanged'] = report['fingerprint'] == fingerprint(ROOT)
        if not report['inputs_unchanged']:
            report['status'] = 'invalid-inputs-changed'
    except (OSError, KeyboardInterrupt) as e:
        report.update(status='interrupted' if isinstance(e, KeyboardInterrupt) else 'blocked', error=str(e))
    save()
    print('结果：', report['status'], dest / 'result.json', flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(run('--full' in sys.argv[1:]))
