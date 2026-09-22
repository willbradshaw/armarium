"""Deterministic contracts; these do not substitute for Obsidian rendering tests."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

from tools.refresh_preparation import refresh, read_note, marker, cell

ROOT = Path(__file__).resolve().parents[1]
SESSION = 'campaigns/campaign_1/sessions/S-1-001.md'
CLUE = 'campaigns/campaign_1/clues/C-1-0001.md'
NPC = 'content/Captain Mara Vey.md'


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='armarium views ')
        self.addCleanup(self.temp.cleanup)
        self.vault = Path(self.temp.name) / 'vault'
        shutil.copytree(ROOT / 'vaults/example', self.vault)

    def edit(self, path, **values):
        p = self.vault / path
        _, props, body = read_note(p)
        props.update(values)
        p.write_text('---\n' + yaml.safe_dump(props, sort_keys=False, allow_unicode=True) + '---\n' + body)

    def snapshot(self):
        return {str(p.relative_to(self.vault)): p.read_bytes() for p in self.vault.rglob('*') if p.is_file()}

    def test_committed_snapshots_current_and_idempotent(self):
        before = self.snapshot()
        for p in (self.vault / 'campaigns/campaign_1/sessions').glob('S-*.md'):
            self.assertFalse(refresh(self.vault, p.relative_to(self.vault).as_posix(), check=True))
            self.assertFalse(refresh(self.vault, p.relative_to(self.vault).as_posix()))
        self.assertEqual(before, self.snapshot())

    def test_source_changes_stale_check_and_refresh_preserves_events(self):
        self.edit(CLUE, text='Changed [[Port Briselle|the port]].\nSecond line | literal pipe.')
        self.edit(NPC, summary='Changed canonical NPC summary.')
        before = self.snapshot()
        self.assertTrue(refresh(self.vault, SESSION, check=True))
        self.assertEqual(before, self.snapshot())
        self.assertTrue(refresh(self.vault, SESSION))
        text = (self.vault / SESSION).read_text()
        self.assertIn('[[content/Port Briselle\\|the port]]', text)
        self.assertIn('<br>Second line \\| literal pipe.', text)
        self.assertIn('Changed canonical NPC summary.', text)
        self.assertEqual(before[SESSION].split(b'# Notes\n')[1], text.encode().split(b'# Notes\n')[1])
        self.assertFalse(refresh(self.vault, SESSION))

    def test_add_remove_order_and_events_only_not_selected(self):
        self.edit(SESSION, prepared_clues=['[[C-1-0002|second]]', '[[C-1-0001|first]]'], prepared_npcs=[])
        before = self.snapshot()
        refresh(self.vault, SESSION)
        body = (self.vault / SESSION).read_text()
        prep = body.split('# Notes')[0]
        self.assertLess(prep.index('\\|second]]'), prep.index('\\|first]]'))
        npc_region = prep.split('<!-- armarium:prep:npcs')[1].split('<!-- /armarium:prep:npcs')[0]
        self.assertIn('No selections.', npc_region)
        self.assertNotIn('Captain Mara', npc_region)
        self.assertNotIn('Orlan Countinghouse', prep.split('<!-- armarium:prep:clues')[1].split('<!-- /armarium:prep:clues')[0])
        self.assertEqual(before.keys(), self.snapshot().keys())
        self.assertEqual(before[SESSION].split(b'# Notes\n')[1], body.encode().split(b'# Notes\n')[1])

    def test_existing_escaped_pipes_do_not_break_generated_tables(self):
        self.assertEqual(cell(r'plain | escaped \| slash \\|'), r'plain \| escaped \| slash \\\|')

    def test_carry_forward_from_template(self):
        destination = 'campaigns/campaign_1/sessions/S-1-004.md'
        shutil.copyfile(self.vault / 'reference/templates/Session.md', self.vault / destination)
        self.edit(destination, session_number=4, prepared_clues=['[[C-1-0001]]'], prepared_locations=[], prepared_npcs=['[[Captain Mara Vey]]'])
        old = (self.vault / SESSION).read_bytes()
        refresh(self.vault, destination)
        self.assertEqual(old, (self.vault / SESSION).read_bytes())
        text = (self.vault / destination).read_text()
        self.assertIn('The [[campaigns/campaign_1/content/Brass Harbor Seal', text)
        self.assertIn('## Events\n- N/A', text)

    def test_conflicts_fail_without_partial_write(self):
        for kind in ['clues', 'locations', 'npcs']:
            with self.subTest(kind=kind):
                path = self.vault / SESSION
                original = path.read_bytes()
                path.write_text(path.read_text().replace(f'<!-- /armarium:prep:{kind}', f'Hand edit\n<!-- /armarium:prep:{kind}'))
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, 'Edited generated'):
                    refresh(self.vault, SESSION)
                self.assertEqual(before, self.snapshot())
                path.write_bytes(original)

    def test_duplicate_basenames_and_display_alias(self):
        other = self.vault / 'content/visitors/Captain Mara Vey.md'
        other.parent.mkdir();shutil.copyfile(self.vault / NPC, other)
        self.edit(SESSION, prepared_npcs=['[[Captain Mara Vey]]'])
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            refresh(self.vault, SESSION)
        self.assertEqual(before, self.snapshot())
        self.edit(SESSION, prepared_npcs=['[[content/Captain Mara Vey.md|Captain]]'])
        refresh(self.vault, SESSION)
        self.assertIn('[[content/Captain Mara Vey\\|Captain]]', (self.vault / SESSION).read_text())

    def test_yaml_alias_is_not_target_identity(self):
        self.edit(NPC, aliases=['The Pilot'])
        self.edit(SESSION, prepared_npcs=['[[The Pilot]]'])
        with self.assertRaisesRegex(ValueError, 'Missing or ambiguous'):
            refresh(self.vault, SESSION)

    def test_all_statuses_remain_explicitly_preparable(self):
        for status in ['Pending', 'Hinted', 'Revealed', 'Abandoned', 'Dormant', 'Superseded']:
            self.edit(CLUE, status=f'[[{status}]]')
            self.assertFalse(refresh(self.vault, SESSION))

    def test_wrong_kind_cross_campaign_and_duplicate_fail(self):
        for field, value, error in [
            ('prepared_npcs', ['[[Port Briselle]]'], 'Expected NPC'),
            ('prepared_clues', ['[[Captain Mara Vey]]'], 'Wrong type'),
            ('prepared_clues', ['[[C-1-0001]]', '[[campaigns/campaign_1/clues/C-1-0001]]'], 'Duplicate selection'),
            ('prepared_clues', None, 'must be a list'),
        ]:
            with self.subTest(field=field, value=value):
                original = (self.vault / SESSION).read_bytes()
                self.edit(SESSION, **{field: value})
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, error):
                    refresh(self.vault, SESSION)
                self.assertEqual(before, self.snapshot())
                (self.vault / SESSION).write_bytes(original)
        other = self.vault / 'campaigns/campaign_2/clues/C-2-0001.md'
        other.parent.mkdir(parents=True);shutil.copyfile(self.vault / CLUE, other)
        self.edit(SESSION, prepared_clues=['[[C-2-0001]]'])
        with self.assertRaisesRegex(ValueError, 'Cross-campaign'):
            refresh(self.vault, SESSION)

    def test_duplicate_yaml_and_missing_canonical_field_fail(self):
        self.edit(NPC, summary=['not a string'])
        with self.assertRaisesRegex(ValueError, 'canonical summary'):
            refresh(self.vault, SESSION)
        p = self.vault / NPC
        p.write_text(p.read_text().replace('---\n', '---\nsummary: duplicate\n', 1))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            refresh(self.vault, SESSION)

    def test_user_notes_outside_regions_preserved(self):
        p = self.vault / SESSION
        text = p.read_text().replace('## Scene notes\n', '## Scene notes\n\nKeep **my** exact wording.\n')
        p.write_text(text)
        self.edit(CLUE, text='Updated.')
        refresh(self.vault, SESSION)
        self.assertEqual(text.split('## Scene notes\n')[1], p.read_text().split('## Scene notes\n')[1])

    def test_marker_duplicates_or_in_notes_fail(self):
        p = self.vault / SESSION
        original = p.read_text()
        for edit in [original + '\n' + marker('npcs', ''), original.replace('# Preparation\n', '# Notes\n', 1)]:
            p.write_text(edit)
            with self.assertRaises(ValueError):
                refresh(self.vault, SESSION)
            self.assertEqual(p.read_text(), edit)

    def test_symlink_and_traversal_rejected(self):
        (self.vault / NPC).unlink()
        (self.vault / NPC).symlink_to(ROOT / 'vaults/example' / NPC)
        with self.assertRaisesRegex(ValueError, 'Missing or ambiguous'):
            refresh(self.vault, SESSION)
        with self.assertRaisesRegex(ValueError, 'vault-relative'):
            refresh(self.vault, '../elsewhere.md')

    def test_check_cli_from_unrelated_directory(self):
        self.edit(CLUE, text='Changed.')
        before = self.snapshot()
        result = subprocess.run([sys.executable, str(ROOT / 'tools/refresh_preparation.py'), str(self.vault), SESSION, '--check'], cwd=self.temp.name, text=True, capture_output=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('STALE', result.stdout)
        self.assertEqual(before, self.snapshot())


class VaultArtifactTests(unittest.TestCase):
    def test_no_runtime_queries_and_shared_reference_equal(self):
        for vault in ['starter', 'example']:
            for p in (ROOT / 'vaults' / vault).rglob('*.md'):
                text = p.read_text()
                self.assertNotRegex(text, r'```\s*dataview(?:js)?\b|`\s*=')
        for p in (ROOT / 'vaults/starter/reference').rglob('*'):
            if p.is_file():
                other = ROOT / 'vaults/example/reference' / p.relative_to(ROOT / 'vaults/starter/reference')
                self.assertEqual(p.read_bytes(), other.read_bytes(), str(p))

    def test_notes_events_loot_and_clue_body_preserved(self):
        for p in (ROOT / 'vaults/example/campaigns/campaign_1/sessions').glob('*.md'):
            previous = subprocess.check_output(['git', 'show', '33e18f3:' + p.relative_to(ROOT).as_posix()], cwd=ROOT)
            self.assertEqual(previous.split(b'# Notes\n')[1], p.read_bytes().split(b'# Notes\n')[1])
        for p in (ROOT / 'vaults/example/campaigns/campaign_1/clues').glob('*.md'):
            _, _, body = read_note(p)
            self.assertEqual(body.strip(), '## Sessions\n\n![[reference/views/clue-sessions.base]]')


if __name__ == '__main__':
    unittest.main()
