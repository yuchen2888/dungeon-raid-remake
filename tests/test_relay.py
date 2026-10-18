"""Exercise dirty-worktree preservation and interrupted relay recovery in a temp repo."""
import hashlib
import json
import os
from pathlib import Path
import pty
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]


class RelaySafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for d in ('scripts', 'docs', 'recovered'):
            (self.root / d).mkdir()
        for name in ('relay.py', 'verify.py'):
            shutil.copy2(PROJECT / 'scripts' / name, self.root / 'scripts' / name)
        for name in ('PROJECT_STATE.md', 'TASKS.md'):
            (self.root / 'docs' / name).write_text('test state\n')
        (self.root / '.gitignore').write_text('.relay/\n__pycache__/\n')
        (self.root / 'sample.txt').write_bytes(b'original\n')
        self.git('init', '-q')
        self.git('add', '--', '.gitignore', 'sample.txt', 'docs', 'scripts')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@local.invalid', 'commit', '-qm', 'baseline')
        (self.root / 'sample.txt').write_bytes(b'staged\n')
        self.git('add', '--', 'sample.txt')
        (self.root / 'sample.txt').write_bytes(b'staged\nunstaged\x00\xff')
        (self.root / 'new.txt').write_bytes(b'untracked\x00\xff')

    def git(self, *args):
        return subprocess.check_output(['git', '--no-optional-locks', '-C', str(self.root), *args])

    def relay(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(self.root / 'scripts/relay.py'), *args],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def dirty(self):
        return (self.git('diff', '--binary'), self.git('diff', '--cached', '--binary'),
                (self.root / 'new.txt').read_bytes())

    def test_claim_conflict_and_handoff_preserve_dirty_files(self):
        before = self.dirty()
        self.relay('begin', 'codex', 'T001')
        self.relay('begin', 'claude', 'T002', ok=False)
        self.relay('handoff', 'claude', 'wrong owner', ok=False)
        self.relay('checkpoint', 'codex', 'saved')
        self.relay('handoff', 'codex', 'done')
        self.assertEqual(before, self.dirty())
        self.assertFalse((self.root / '.relay/active').exists())
        for path in (self.root / '.relay/snapshots').iterdir():
            self.assertEqual((path / 'untracked/new.txt').read_bytes(), before[2])
            self.assertEqual((path / 'staged.patch').read_bytes(), before[1])

    def test_recovery_requires_explicit_stop_and_keeps_previous_owner(self):
        self.relay('begin', 'codex', 'T001')
        before = self.dirty()
        self.relay('recover', 'gemini', 'T001', ok=False)
        self.relay('recover', 'gemini', 'T001', '--previous-stopped')
        self.assertEqual(before, self.dirty())
        previous = next((self.root / '.relay').glob('interrupted-*'))
        self.assertEqual(json.loads((previous / 'owner.json').read_text())['agent'], 'codex')
        self.assertEqual(json.loads((self.root / '.relay/active/owner.json').read_text())['agent'], 'gemini')

    def test_check_has_no_filesystem_side_effects(self):
        def hashes():
            return {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.root.rglob('*') if p.is_file()}
        before = hashes()
        self.relay('check')
        self.assertEqual(before, hashes())

    def test_launcher_uses_same_directory_and_interactive_arguments(self):
        # Local dummy executables only: no AI session, network or account used.
        bindir = self.root / 'bin'; bindir.mkdir()
        for agent in ('codex', 'claude', 'gemini'):
            executable = bindir / agent
            executable.write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "$@" > launch.txt\n')
            executable.chmod(0o755)
        env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ.get('PATH', ''))
        for agent in ('codex', 'claude', 'gemini'):
            master, slave = pty.openpty()
            try:
                result = subprocess.run([sys.executable, str(self.root / 'scripts/relay.py'), 'start', agent],
                                        stdin=slave, capture_output=True, text=True, env=env)
            finally:
                os.close(master); os.close(slave)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            args = (self.root / 'launch.txt').read_text().splitlines()
            self.assertEqual(Path(args[0]).resolve(), self.root.resolve())
            self.assertEqual(len(args), 3 if agent == 'gemini' else 2)
            if agent == 'gemini': self.assertEqual(args[1], '-i')
            self.assertIn('begin ' + agent, args[-1])


if __name__ == '__main__':
    unittest.main()
