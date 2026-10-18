#!/usr/bin/env python3
"""Local relay coordination. check is read-only; no command stages or commits."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.relay'
ACTIVE = LOCAL / 'active'
TOOLS = ('codex', 'claude', 'gemini')


def stamp():
    return dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')


def git(*args):
    return subprocess.check_output(['git', '--no-optional-locks', '-C', str(ROOT), *args])


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def snapshot(agent, note):
    dest = LOCAL / 'snapshots' / stamp()
    dest.mkdir(parents=True)
    (dest / 'unstaged.patch').write_bytes(git('diff', '--binary'))
    (dest / 'staged.patch').write_bytes(git('diff', '--cached', '--binary'))
    untracked = [os.fsdecode(p) for p in git('ls-files', '--others', '--exclude-standard', '-z').split(b'\0') if p]
    for name in untracked:
        target = dest / 'untracked' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target, follow_symlinks=False)
    write_json(dest / 'state.json', dict(agent=agent, note=note, head=git('rev-parse', 'HEAD').decode().strip(),
                                       status=git('status', '--short').decode(), untracked=untracked))
    print('断点：', dest)
    return dest


def owner():
    return json.loads((ACTIVE / 'owner.json').read_text())


def check():
    print('项目：', ROOT)
    for args in [('status', '--short', '--branch'), ('log', '-5', '--oneline'),
                 ('diff', '--stat'), ('diff', '--cached', '--stat'),
                 ('ls-files', '--others', '--exclude-standard')]:
        print('\n' + 'git ' + ' '.join(args) + '\n' + git(*args).decode(), end='')
    print('\n远端名称：', git('remote').decode().strip() or '无（仅本地）')
    print('活动任务：', (ACTIVE / 'owner.json').read_text() if (ACTIVE / 'owner.json').exists()
          else '锁存在但元数据不完整，需人工确认前一写入者已停止' if ACTIVE.exists() else '无')
    for name in TOOLS:
        print(name + ':', shutil.which(name) or '未在 PATH 中发现')
    from verify import fingerprint
    path = LOCAL / 'latest-validation.json'
    if path.exists():
        report = json.loads(path.read_text())
        print('最近验证：', report['status'], report['run'])
        print('输入哈希一致：', report['fingerprint'] == fingerprint(ROOT))
    else:
        print('最近验证：尚无本地实跑报告')
    for name in ('PROJECT_STATE.md', 'TASKS.md'):
        print('\n--- docs/' + name + ' ---\n' + (ROOT / 'docs' / name).read_text())


def begin(agent, task):
    LOCAL.mkdir(exist_ok=True)
    try:
        ACTIVE.mkdir()
    except FileExistsError:
        raise SystemExit('已有写入者。先 check；确认前一工具已停止后用 recover，禁止抢占。')
    write_json(ACTIVE / 'owner.json', dict(agent=agent, task=task, since=stamp(),
                                         head=git('rev-parse', 'HEAD').decode().strip()))
    snapshot(agent, '开始 ' + task + '；继承修改见补丁和未跟踪文件副本')


def main():
    p = argparse.ArgumentParser(description='Dungeon Raid 本地接力；所有路径自动定位到本项目')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('check')
    v = sub.add_parser('verify'); v.add_argument('--full', action='store_true')
    for action in ('begin', 'recover', 'checkpoint', 'handoff', 'start'):
        s = sub.add_parser(action); s.add_argument('agent', choices=TOOLS)
        if action in ('begin', 'recover'): s.add_argument('task')
        if action in ('checkpoint', 'handoff'): s.add_argument('note')
        if action == 'recover': s.add_argument('--previous-stopped', action='store_true', required=True)
    a = p.parse_args()
    if a.command == 'check':
        check()
    elif a.command == 'verify':
        from verify import run
        return run(a.full)
    elif a.command == 'begin':
        begin(a.agent, a.task)
    elif a.command == 'recover':
        if ACTIVE.exists():
            snapshot(a.agent, '接管前保留现场：' + a.task)
            ACTIVE.rename(LOCAL / ('interrupted-' + stamp()))
        begin(a.agent, a.task)
    elif a.command in ('checkpoint', 'handoff'):
        if not ACTIVE.exists() or owner()['agent'] != a.agent:
            raise SystemExit('工具与当前写入者不一致；先 check，不改动锁。')
        dest = snapshot(a.agent, a.note)
        if a.command == 'handoff':
            ACTIVE.rename(dest / 'released-owner')
            print('已释放写入权。下一位先 check，再 begin。')
    elif a.command == 'start':
        if ACTIVE.exists():
            raise SystemExit('存在活动任务；先 check 并完成 handoff 或确认停止后 recover。')
        executable = shutil.which(a.agent)
        if not executable:
            raise SystemExit(a.agent + ' 未在 PATH 中发现。按 docs/RELAY.md 安装/登录后重试；未启动模型。')
        if not sys.stdin.isatty():
            raise SystemExit('请在本机交互式终端运行 start。只读检查使用 check。')
        check()
        prompt = ('继续 Dungeon Raid。先读 AGENTS.md 及 docs/ 的当前状态、任务、架构和证据，'
                  '执行 ./scripts/relay.sh check，检查全部继承差异，认领首个未完成任务后 begin ' + a.agent +
                  '。保留未提交修改，复用现有恢复源码。每个可验证单元更新文档、测试、原子提交并保存断点。'
                  '不创建远端或上传资源，不宣称完整游戏已完成。')
        args = [executable] + (['-i'] if a.agent == 'gemini' else []) + [prompt]
        return subprocess.call(args, cwd=ROOT)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, subprocess.CalledProcessError, ValueError) as e:
        sys.exit(str(e))
