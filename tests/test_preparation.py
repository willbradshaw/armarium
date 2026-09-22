"""Repository contracts; live behavior is checked in check_live_tables.mjs."""
import json
import re
from pathlib import Path
import subprocess
import unittest
import yaml
ROOT = Path(__file__).resolve().parents[1]

class VaultArtifactTests(unittest.TestCase):
    def test_base_columns_match_every_original_dataview_query(self):
        inventory = json.loads((ROOT / 'docs/views/inventory.json').read_text())
        for entry in inventory:
            if entry['replacement'] != 'Bases':
                continue
            vault = entry['file'].split('/')[1]
            base = yaml.safe_load((ROOT / 'vaults' / vault / entry['artifact']).read_text())
            original = re.findall(r'(file\.link|\w+)\s+as\s+"([^"]+)"', entry['original'])
            expected = [('file.name' if field == 'file.link' else 'note.' + field, label)
                        for field, label in original]
            self.assertTrue(expected, entry['file'])
            for view in base['views']:
                self.assertEqual(view['type'], 'table', entry['file'])
                fields = [field if '.' in field else 'note.' + field for field in view['order']]
                actual = [(base['formulas'][field.split('.', 1)[1]] if field.startswith('formula.') else field, base['properties'][field]['displayName']) for field in fields]
                self.assertEqual(actual, expected, entry['file'])

    def test_preparation_headers_match_original_tables(self):
        for vault in ['starter', 'example']:
            root = ROOT / 'vaults' / vault
            for p in [root / 'reference/templates/Session.md', *root.glob('campaigns/*/sessions/S-*.md')]:
                previous = subprocess.check_output(['git', 'show', '33e18f3:' + p.relative_to(ROOT).as_posix()], cwd=ROOT, text=True)
                for heading, kind in [('Secrets & Clues','clues'),('Locations','locations'),('Important NPCs','npcs')]:
                    pattern = r'## ' + re.escape(heading) + r'\n(.*?)(?=\n## )'
                    section = re.search(pattern, previous, re.S)[1]
                    row = re.search(r'^\|.*\|$', section, re.M)[0]
                    expected = [value.strip() for value in row.strip('|').split('|')]
                    current = re.search(pattern, p.read_text(), re.S)[1]
                    self.assertEqual(current.strip(), f'![[reference/views/prepared-{kind}.base]]')
                    base = yaml.safe_load((root / f'reference/views/prepared-{kind}.base').read_text())
                    view = base['views'][0]
                    self.assertEqual(view['type'], 'table')
                    actual = [base['properties'][f if '.' in f else 'note.'+f]['displayName'] for f in view['order']]
                    self.assertEqual(actual, expected, str(p))

    def test_no_runtime_queries_and_shared_reference_equal(self):
        for vault in ['starter', 'example']:
            for p in (ROOT / 'vaults' / vault).rglob('*.md'):
                text = p.read_text()
                self.assertNotRegex(text, r'```\s*dataview(?:js)?\b|`\s*=|armarium:prep:|Preparation snapshot|refresh_preparation|view_campaign')
        for p in (ROOT / 'vaults/starter/reference').rglob('*'):
            if p.is_file():
                other = ROOT / 'vaults/example/reference' / p.relative_to(ROOT / 'vaults/starter/reference')
                self.assertEqual(p.read_bytes(), other.read_bytes(), str(p))

    def test_notes_events_loot_and_clue_body_preserved(self):
        for p in (ROOT / 'vaults/example/campaigns/campaign_1/sessions').glob('*.md'):
            previous = subprocess.check_output(['git', 'show', '33e18f3:' + p.relative_to(ROOT).as_posix()], cwd=ROOT)
            self.assertEqual(previous.split(b'# Notes\n')[1], p.read_bytes().split(b'# Notes\n')[1])
        for p in (ROOT / 'vaults/example/campaigns/campaign_1/clues').glob('*.md'):
            body = p.read_text().split('---', 2)[2]
            self.assertEqual(body.strip(), '## Sessions\n\n![[reference/views/clue-sessions.base]]')


if __name__ == '__main__':
    unittest.main()
