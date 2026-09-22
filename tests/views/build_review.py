"""Build disposable copies with synthetic cases; never modifies committed vaults.

Run from repository root: python tests/views/build_review.py NEW_DIRECTORY
Requires PyYAML (tests/requirements-views.txt).
"""
from pathlib import Path
import json
import shutil
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
def read_note(path):
    text = path.read_text()
    _, frontmatter, body = text.split('---', 2)
    return text, yaml.safe_load(frontmatter), body.lstrip('\n')


def write(root, path, props, body):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('---\n' + yaml.safe_dump(props, sort_keys=False, allow_unicode=True, width=10000) + '---\n' + body)


def build(destination):
    destination.mkdir(exist_ok=False)
    for name in ['starter', 'example']:
        root = destination / ('armarium25-' + name)
        shutil.copytree(ROOT / 'vaults' / name, root)
        config = root / '.obsidian';config.mkdir(exist_ok=True)
        (config / 'core-plugins.json').write_text(json.dumps(['file-explorer', 'properties', 'backlink', 'outgoing-link', 'page-preview', 'bases']))
        (config / 'community-plugins.json').write_text('[]')
        (config / 'app.json').write_text(json.dumps({'defaultViewMode': 'preview', 'livePreview': False}))
        (config / 'types.json').write_text(json.dumps({'types': {'prepared_clues': 'multitext', 'prepared_npcs': 'multitext', 'prepared_locations': 'multitext', 'subjects': 'multitext', 'date': 'date', 'session_number': 'number'}}))
        if name == 'starter':
            continue
        _, _, content_body = read_note(root / 'reference/templates/Content.md')
        _, _, clue_body = read_note(root / 'reference/templates/Clue.md')
        _, _, session_body = read_note(root / 'reference/templates/Session.md')
        for path, subtype, summary in [
            ('content/Review/Signal Keeper.md', 'NPC', 'A keeper who follows [[content/Review/Quay|the quay]]. ' * 35 + 'LONG_TEXT_END'),
            ('content/Review/Visitors/Signal Keeper.md', 'NPC', 'A different keeper; duplicate basename.'),
            ('content/Review/Quay.md', 'Location', 'A quiet quay.\nA second line with [[content/Review/Signal Keeper|the keeper]].'),
            ('content/Review/Empty.md', 'NPC', 'No clues target this person.'),
            ('content/Review/Events Only.md', 'NPC', 'Never explicitly selected.'),
        ]:
            write(root, path, {'type': '[[types/Content]]', 'subtype': subtype, 'summary': summary, 'aliases': ['Review alias'], 'campaign_1': {'first_session': None, 'last_session': None}, 'campaign_2': {'first_session': None, 'last_session': None}}, content_body)
        for campaign in [1, 2]:
            cp = f'campaigns/campaign_{campaign}'
            if campaign == 2:
                write(root, cp + '/reference/Campaign.md', {'type': '[[types/Reference]]'}, 'Temporary synthetic campaign, no narrative.\n')
                shutil.copyfile(root / 'campaigns/campaign_1/reference/indexes/Clues.md', root / cp / 'reference/Clues.md')
                (root / cp / 'reference/indexes').mkdir()
                (root / cp / 'reference/Clues.md').rename(root / cp / 'reference/indexes/Clues.md')
            write(root, cp + '/content/Review/Local Keeper.md', {'type': '[[types/Content]]', 'subtype': 'NPC', 'summary': 'A campaign-specific keeper.'}, content_body)
            for i, status in enumerate(['Pending', 'Hinted', 'Revealed', 'Abandoned', 'Dormant', 'Superseded'], 9001):
                subject = 'content/Review/Visitors/Signal Keeper' if i == 9002 else 'content/Review/Signal Keeper'
                write(root, f'{cp}/clues/C-{campaign}-{i}.md', {'type': '[[types/Clue]]', 'status': f'[[{status}]]', 'text': f'Campaign {campaign} candidate {i}. [[content/Review/Quay|Quay]] ' + 'Unconfirmed long text. ' * 35 + 'CLUE_TEXT_END', 'subjects': [f'[[{subject}|Keeper alias]]'] + (['[[campaigns/campaign_1/content/Review/Local Keeper]]', '[[campaigns/campaign_2/content/Review/Local Keeper]]'] if i == 9001 else []), 'first_session': None, 'last_session': None}, clue_body)
            for number, date in [(901, '2026-01-02'), (902, '2026-01-01'), (903, '2026-01-01')]:
                props = {'type': '[[types/Session]]', 'campaign': f'[[{cp}/reference/Campaign]]', 'date': date, 'session_number': number, 'prepared_clues': [f'[[{cp}/clues/C-{campaign}-9002|Second]]', f'[[{cp}/clues/C-{campaign}-9001|First]]'], 'prepared_locations': ['[[content/Review/Quay]]'], 'prepared_npcs': ['[[content/Review/Visitors/Signal Keeper|Visitor]]', '[[content/Review/Signal Keeper|Keeper]]']}
                body = session_body.replace('## Events\n- N/A', '## Events\n- Met [[content/Review/Events Only]].\n- Mentioned [[campaigns/campaign_1/clues/C-1-9001]].')
                path = f'{cp}/sessions/S-{campaign}-{number}.md'
                write(root, path, props, body)
            write(root, cp + '/sessions/transcripts/Review Transcript.md', {'type': '[[types/Transcript]]', 'session': f'[[{cp}/sessions/S-{campaign}-901]]'}, f'[[{cp}/clues/C-{campaign}-9001]]\n')
            write(root, cp + '/sessions/transcripts/Nested Pretend Session.md', {'type': '[[types/Session]]', 'campaign': f'[[{cp}/reference/Campaign]]', 'date': '2020-01-01', 'session_number': 1}, f'[[{cp}/clues/C-{campaign}-9001]]\n')
    return destination


if __name__ == '__main__':
    print(build(Path(sys.argv[1]).resolve()))
