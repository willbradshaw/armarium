"""File-level acceptance checks; these do not verify Obsidian rendering."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import create_vault

ROOT = Path(__file__).resolve().parents[1]


def snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}


class StarterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='armarium-test-')
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.vault = self.parent / 'A new setting'

    def test_fresh_cli_install_is_exact_copy_and_can_move(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'scripts/create_vault.py'), str(self.vault)],
            cwd=self.parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snapshot(create_vault.STARTER), snapshot(self.vault))
        moved = self.parent / 'Moved setting'
        self.vault.rename(moved)
        self.assertEqual(snapshot(create_vault.STARTER), snapshot(moved))
        for path in moved.rglob('*.md'):
            text = path.read_text()
            self.assertNotIn('{{', text)
            self.assertNotIn(str(ROOT), text)
            for target in re.findall(r'\[\[([^\]\n]+)\]\]', text):
                self.assertTrue((moved / (target + '.md')).is_file(), (path, target))
        json.loads((moved / '.obsidian/app.json').read_text())

    def test_existing_paths_and_customizations_are_preserved(self):
        self.vault.mkdir()
        with self.assertRaises(ValueError):
            create_vault.install(self.vault)
        self.assertEqual(list(self.vault.iterdir()), [])
        (self.vault / 'NPC.md').write_text('My edited template')
        before = snapshot(self.vault)
        with self.assertRaises(ValueError):
            create_vault.install(self.vault)
        self.assertEqual(before, snapshot(self.vault))
        file = self.parent / 'file'
        file.write_text('Keep')
        with self.assertRaises(ValueError):
            create_vault.install(file)
        self.assertEqual(file.read_text(), 'Keep')
        link = self.parent / 'link'
        link.symlink_to(self.parent / 'missing')
        with self.assertRaises(ValueError):
            create_vault.install(link)
        self.assertTrue(link.is_symlink())

    def test_invalid_destination_creates_nothing(self):
        for path in [ROOT / 'should-not-be-created', self.parent / 'missing' / 'vault']:
            with self.assertRaises(ValueError):
                create_vault.install(path)
            self.assertFalse(path.exists())
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_competing_creation_is_not_overwritten(self):
        original = shutil.copytree
        def compete(source, target):
            target.mkdir()
            (target / 'keep').write_text('Keep')
            return original(source, target)
        with patch.object(create_vault.shutil, 'copytree', side_effect=compete):
            with self.assertRaises(FileExistsError):
                create_vault.install(self.vault)
        self.assertEqual(snapshot(self.vault), {Path('keep'): b'Keep'})

    def test_source_symlink_is_rejected_before_install(self):
        source = self.parent / 'source'
        source.mkdir()
        (source / 'link').symlink_to(self.parent / 'missing')
        with patch.object(create_vault, 'STARTER', source):
            with self.assertRaises(ValueError):
                create_vault.install(self.vault)
        self.assertFalse(self.vault.exists())

    @unittest.skipUnless(shutil.which('git'), 'Git required')
    def test_independent_git_repository(self):
        create_vault.install(self.vault)
        subprocess.run(['git', 'init', '-q', str(self.vault)], check=True)
        (self.vault / '.scratch/draft.md').write_text('Draft')
        (self.vault / 'assets/map.txt').write_text('Map')
        for path, expected in [('.scratch/draft.md', 0), ('assets/map.txt', 1)]:
            result = subprocess.run(['git', '-C', str(self.vault), 'check-ignore', '-q', path])
            self.assertEqual(result.returncode, expected)


if __name__ == '__main__':
    unittest.main()
