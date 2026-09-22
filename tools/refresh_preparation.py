"""Bounded preparation refresh; temporary entry point pending package issue #24.

Usage: python tools/refresh_preparation.py VAULT SESSION [--check]
Requires PyYAML. No discovery of selections from body links; no bulk refresh.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile

import yaml

KINDS = {"clues": (None, "text"), "locations": ("Location", "summary"), "npcs": ("NPC", "summary")}
HEADERS = {"clues": "| ID | Text |", "locations": "| Location | Description |", "npcs": "| Name | Summary |"}
LINK = re.compile(r"\[\[([^\[\]\n]+)\]\]")
EXCLUDED = {".git", ".obsidian", ".scratch", "__pycache__", ".venv"}


class UniqueLoader(yaml.SafeLoader):
    pass


def mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ValueError(f"Duplicate or non-string YAML key: {key!r}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def read_note(path):
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
    if not match:
        raise ValueError(f"Missing frontmatter: {path}")
    data = yaml.load(match[1], Loader=UniqueLoader)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return raw, data, text[match.end():]


class Sources:
    """Resolve canonical file targets, never YAML aliases or guessed basenames."""
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        self.paths = []
        self.reads = {}
        for directory, dirs, files in os.walk(self.root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and not (Path(directory) / d).is_symlink())
            for name in sorted(files):
                path = Path(directory) / name
                if not path.is_symlink():
                    self.paths.append(path.relative_to(self.root).as_posix())

    def resolve(self, value, source=""):
        match = LINK.fullmatch(value) if isinstance(value, str) else None
        if not match:
            raise ValueError(f"Expected a wikilink, got {value!r}")
        target = match[1].replace(r"\|", "|").split("|", 1)[0].split("#", 1)[0]
        if not target:
            if source:
                return source
            raise ValueError("Selection must name a file")
        if target.startswith("/") or any(part in ("", ".", "..") for part in target.split("/")):
            raise ValueError(f"Expected vault-relative target: {target}")
        # Explicit extensions (including .base/assets) retain their identity.
        candidates = [target] if Path(target).suffix else [target + ".md", target]
        exact = [p for p in self.paths if p in candidates]
        matches = exact or [p for p in self.paths if any(p.endswith('/' + c) for c in candidates)]
        if len(matches) != 1:
            raise ValueError(f"Missing or ambiguous target: {target}")
        return matches[0]

    def read(self, path):
        target = self.root / path
        if target.is_symlink() or target.resolve() != target or not target.is_file():
            raise ValueError(f"Source changed or is a symlink: {path}")
        raw, props, body = read_note(target)
        self.reads[path] = raw
        return props, body

    def qualify(self, value, source=""):
        def replace(match):
            parts = match[1].replace(r"\|", "|").split("|", 1)
            anchor = '#' + parts[0].split('#', 1)[1] if '#' in parts[0] else ''
            path = self.resolve(match[0], source)
            target = path.removesuffix('.md') + anchor
            label = parts[1] if len(parts) == 2 else parts[0] or Path(source).stem
            return f"[[{target}|{label}]]"
        return LINK.sub(replace, value)


def marker(kind, payload):
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f"<!-- armarium:prep:{kind} sha256={digest} -->\n{payload}<!-- /armarium:prep:{kind} -->"


def cell(value):
    escaped = re.sub(r'(\\*)\|', lambda m: m[1] + ('\\' if len(m[1]) % 2 == 0 else '') + '|', value)
    return escaped.replace('\r\n', '\n').replace('\n', '<br>')


def refresh(root, session, *, check=False):
    sources = Sources(root)
    # SESSION is a vault-relative file path, not a wikilink or suffix search.
    if not re.fullmatch(r"campaigns/campaign_\d+/sessions/S-\d+-\d+\.md", session):
        raise ValueError("Session must be a vault-relative campaigns/campaign_N/sessions/S-N-NNN.md path")
    if session not in sources.paths:
        raise ValueError(f"Missing Session: {session}")
    props, body = sources.read(session)
    original = sources.reads[session]
    updated = original.decode('utf-8')
    if sources.resolve(props.get('type')) != 'reference/types/Session.md':
        raise ValueError("Target is not a Session")
    campaign = session.split('/')[1]
    number = campaign.removeprefix('campaign_')
    if not Path(session).name.startswith(f'S-{number}-'):
        raise ValueError("Session filename disagrees with containing campaign")
    if sources.resolve(props.get('campaign')) != f'campaigns/{campaign}/reference/Campaign.md':
        raise ValueError("Session campaign disagrees with containing folder")
    if body.count('# Preparation\n') != 1 or body.count('# Notes\n') != 1:
        raise ValueError("Expected one Preparation and one Notes section (LF newlines)")
    prep_start = updated.index('# Preparation\n')
    prep_end = updated.index('# Notes\n')
    if prep_end < prep_start:
        raise ValueError("Notes must follow Preparation")
    replacements = []
    for kind, (subtype, field) in KINDS.items():
        pattern = rf"<!-- armarium:prep:{kind} sha256=([a-f0-9]{{64}}) -->\n(.*?)<!-- /armarium:prep:{kind} -->"
        matches = list(re.finditer(pattern, updated, re.S))
        if len(matches) != 1 or updated.count(f'<!-- armarium:prep:{kind}') != 1 or updated.count(f'<!-- /armarium:prep:{kind}') != 1:
            raise ValueError(f"Missing/duplicate/malformed {kind} ownership markers")
        match = matches[0]
        if not prep_start < match.start() < match.end() < prep_end:
            raise ValueError(f"{kind} region must be inside Preparation, before Notes")
        if hashlib.sha256(match[2].encode()).hexdigest() != match[1]:
            raise ValueError(f"Edited generated {kind} region; move edits to Scene notes and restore generated text before refresh")
        selections = props.get('prepared_' + kind)
        if not isinstance(selections, list):
            raise ValueError(f"prepared_{kind} must be a list (use [] for none)")
        rows, seen = [], set()
        for selected in selections:
            path = sources.resolve(selected)
            if path in seen:
                raise ValueError(f"Duplicate selection: {path}")
            seen.add(path)
            data, _ = sources.read(path)
            expected_type = 'Clue' if kind == 'clues' else 'Content'
            if sources.resolve(data.get('type')) != f'reference/types/{expected_type}.md':
                raise ValueError(f"Wrong type for prepared_{kind}: {path}")
            if subtype and data.get('subtype') != subtype:
                raise ValueError(f"Expected {subtype}: {path}")
            if kind == 'clues' and str(Path(path).parent) != f'campaigns/{campaign}/clues':
                raise ValueError(f"Cross-campaign Clue: {path}")
            if kind != 'clues' and not (path.startswith('content/') or path.startswith(f'campaigns/{campaign}/content/')):
                raise ValueError(f"Content is not shared or in this campaign: {path}")
            if field not in data or data[field] is not None and not isinstance(data[field], str):
                raise ValueError(f"Expected canonical {field} text: {path}")
            text = sources.qualify(data[field] or '', path)
            if '<!-- armarium:prep:' in text or '<!-- /armarium:prep:' in text:
                raise ValueError("Source text contains reserved ownership markers")
            rows.append(f'| {cell(sources.qualify(selected))} | {cell(text)} |')
        payload = '> Preparation snapshot: refresh after source or selection edits; see [[reference/views/README|view instructions]].\n\n'
        payload += HEADERS[kind] + '\n| --- | --- |\n'
        payload += '\n'.join(rows) + '\n' if rows else '| — | No selections. |\n'
        replacements.append((match.start(), match.end(), marker(kind, payload)))
    for start, end, replacement in sorted(replacements, reverse=True):
        updated = updated[:start] + replacement + updated[end:]
    result = updated.encode('utf-8')
    for path, content in sources.reads.items():
        target = sources.root / path
        if target.is_symlink() or target.resolve() != target or target.read_bytes() != content:
            raise ValueError(f"File changed during refresh: {path}; retry after reconciling edits")
    if result != original and not check:
        path = sources.root / session
        fd, temporary = tempfile.mkstemp(prefix='.prep-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(result)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
            if path.read_bytes() != original:
                raise ValueError("Session changed during refresh; retry")
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return result != original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('vault', type=Path)
    parser.add_argument('session')
    parser.add_argument('--check', action='store_true', help='Read only; exit 1 when refresh is needed')
    args = parser.parse_args()
    try:
        changed = refresh(args.vault, args.session, check=args.check)
    except (ValueError, OSError, yaml.YAMLError) as error:
        parser.exit(2, f'Preparation not refreshed: {error}\n')
    print(('STALE' if args.check else 'Refreshed') if changed else 'Current')
    return 1 if args.check and changed else 0


if __name__ == '__main__':
    raise SystemExit(main())
