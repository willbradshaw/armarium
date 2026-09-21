"""Build an original test vault and explicitly refresh bounded prep snapshots."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import time

import yaml

HERE = Path(__file__).resolve().parent
STARTER = HERE.parents[1] / "starter"
KINDS = {"clues": ("Clue", "text"), "locations": ("Location", "summary"), "npcs": ("NPC", "summary")}


def link(path, alias=None):
    return f"[[{path}{'|' + alias if alias else ''}]]"


def write_note(root, path, props, body):
    # Preserve the starter contract even when a fixture only supplies interesting values.
    if "type" in props:
        template = STARTER / "templates" / (canonical(props["type"]).split("/")[-1] + ".md")
        if template.exists():
            defaults, _ = read_note(template)
            if isinstance(defaults.get("aliases"), list):
                defaults["aliases"] = [a for a in defaults["aliases"] if a is not None]
            props = defaults | props
    target = root / (path + ".md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("---\n" + yaml.safe_dump(props, sort_keys=False, allow_unicode=True, width=100000) + "---\n" + body)


def read_note(path):
    text = path.read_text()
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise ValueError(f"Missing frontmatter: {path}")
    return yaml.safe_load(match[1]), text[match.end():]


def canonical(value):
    """Deliberately limited to vault-qualified wikilinks; never guess a basename."""
    match = re.fullmatch(r"\[\[([^|#\]]+)(?:\|[^\]]+)?\]\]", value)
    if not match:
        raise ValueError(f"Expected qualified page link: {value!r}")
    path = match[1].removesuffix(".md")
    if "/" not in path or any(p in (".", "..", "") for p in path.split("/")):
        raise ValueError(f"Expected vault-qualified path: {value!r}")
    return path


def marker(kind, payload=""):
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f"<!-- armarium:prep:{kind} sha256={digest} -->\n{payload}<!-- /armarium:prep:{kind} -->"


def cell(value):
    # Escaping the pipe also preserves aliased wikilinks inside Markdown tables.
    return str(value).replace("|", r"\|").replace("\r\n", "\n").replace("\n", "<br>")


def refresh(root, session):
    """All three regions validate before any write. No force/overwrite option."""
    path = root / (canonical(link(session)) + ".md")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Session escapes vault")
    original = path.read_text()
    props, _ = read_note(path)
    updated = original
    for kind, (type_name, field) in KINDS.items():
        pattern = rf"<!-- armarium:prep:{kind} sha256=([a-f0-9]{{64}}) -->\n(.*?)<!-- /armarium:prep:{kind} -->"
        matches = list(re.finditer(pattern, updated, re.S))
        if len(matches) != 1 or updated.count(f"<!-- armarium:prep:{kind}") != 1 or updated.count(f"<!-- /armarium:prep:{kind}") != 1:
            raise ValueError(f"Missing/duplicate/malformed {kind} ownership markers")
        match = matches[0]
        if hashlib.sha256(match[2].encode()).hexdigest() != match[1]:
            raise ValueError(f"Edited generated {kind} region; move edits outside markers before refresh")
        selections = props.get("prepared_" + kind, [])
        if not isinstance(selections, list):
            raise ValueError(f"prepared_{kind} must be a list")
        rows = []
        seen = set()
        for selected in selections:
            source = canonical(selected)
            if source in seen:
                raise ValueError(f"Duplicate selection: {source}")
            seen.add(source)
            target = root / (source + ".md")
            if not target.resolve().is_relative_to(root.resolve()):
                raise ValueError("Selection escapes vault")
            data, _ = read_note(target)
            if canonical(data["type"]) != "types/" + type_name:
                raise ValueError(f"Wrong type for {source}")
            if kind == "clues" and canonical(data["campaign"]) != canonical(props["campaign"]):
                raise ValueError(f"Cross-campaign prep Clue: {source}")
            rows.append(f"| {cell(selected)} | {cell(data.get(field, ''))} |")
        payload = "| Page | " + field.title() + " |\n| --- | --- |\n" + ("\n".join(rows) + "\n" if rows else "| — | No selections. |\n")
        updated = updated[:match.start()] + marker(kind, payload) + updated[match.end():]
    if path.read_text() != original:
        raise ValueError("Session changed during refresh; retry after reconciling edits")
    if updated != original:
        path.write_text(updated)
    return updated


def build(root, corpus=0):
    if root.exists():
        raise ValueError("Destination already exists; choose a new directory")
    shutil.copytree(STARTER, root, ignore=shutil.ignore_patterns(".obsidian", ".scratch", ".DS_Store", "__pycache__"))
    shutil.copytree(HERE / "bases", root / "bases")
    config = root / ".obsidian"
    config.mkdir()
    (config / "core-plugins.json").write_text(json.dumps(["file-explorer", "global-search", "backlink", "outgoing-link", "properties", "page-preview", "bases"]))
    (config / "community-plugins.json").write_text("[]")
    (config / "app.json").write_text(json.dumps({"defaultViewMode": "preview", "livePreview": False}))
    (config / "types.json").write_text(json.dumps({"types": {"date": "date", "session_number": "number", "prepared_npcs": "multitext", "prepared_locations": "multitext", "prepared_clues": "multitext", "subjects": "multitext"}}))
    for campaign in (1, 2):
        cp = f"campaign_{campaign}"
        write_note(root, cp + "/Campaign", {"type": link("types/Reference"), "aliases": [f"Lantern Test {campaign}"]}, f"Original synthetic campaign {campaign}.\n")
        write_note(root, cp + "/index/Clues", {"view_campaign": cp}, "## Active\n![[bases/clue-index.base#Active]]\n## Closed\n![[bases/clue-index.base#Closed]]\n")
    entities = [
        ("world/npcs/Mira", "NPC", ["Lantern Keeper"], "Mira maintains the flood lamps. She suspects [[world/locations/Quay|the old quay]] hides a second tide gauge. " * 8),
        ("world/npcs/Visitors/Mira", "NPC", ["Visiting Mira"], "A visiting glassblower, unrelated to the keeper."),
        ("world/npcs/Events Only", "NPC", [], "Met during Events; never deliberately prepared."),
        ("world/locations/Quay", "Location", ["Old Quay"], "A stone quay with a broken gauge.\nAt low tide, a brass ladder appears."),
        ("world/locations/Empty", "Location", [], "No Clues refer here."),
    ]
    entity_body = "## Notes\n- Original synthetic record.\n## Active Clues\nContext: `view_campaign` is a display choice, not ownership. Change it between campaign_1 and campaign_2.\n![[bases/entity-clues.base]]\n## Appearances\n- N/A\n"
    for path, typ, aliases, summary in entities:
        write_note(root, path, {"type": link("types/" + typ), "aliases": aliases, "summary": summary, "campaign_1": {"first_session": None, "last_session": None}, "campaign_2": {"first_session": None, "last_session": None}, "view_campaign": "campaign_1"}, entity_body)
    statuses = ["Pending", "Hinted", "Revealed", "Abandoned", "Dormant", "Superseded"]
    for campaign in (1, 2):
        for i, status in enumerate(statuses, 1):
            subjects = [link("world/npcs/Mira", "Lantern Keeper"), link("world/locations/Quay")]
            if i == 2:
                subjects = [link("world/npcs/Visitors/Mira", "Mira")]
            cp = f"campaign_{campaign}"
            write_note(root, f"{cp}/clues/C-{campaign}-{i:04d}", {"type": link("types/Clue"), "campaign": link(cp + "/Campaign"), "view_campaign": cp, "status": link("statuses/" + status), "text": f"Campaign {campaign}, candidate {i}: [[world/npcs/Mira|the keeper]] may have hidden the gauge. " + ("This is an unconfirmed lead, not world canon. " * 18 if i == 1 else "Unconfirmed."), "subjects": subjects, "first_session": None, "last_session": None}, "## Sessions\n![[bases/clue-sessions.base]]\n")
    session_template = (STARTER / "templates/Session.md").read_text().split("---\n", 2)[2]
    for campaign, number, date in [(1, 1, "2026-01-01"), (1, 2, "2026-01-01"), (1, 3, "2026-01-02"), (2, 1, "2026-01-01")]:
        cp = f"campaign_{campaign}"
        props = {"type": link("types/Session"), "campaign": link(cp + "/Campaign"), "view_campaign": cp, "date": date, "session_number": number, "prepared_npcs": [link("world/npcs/Visitors/Mira"), link("world/npcs/Mira", "Lantern Keeper")], "prepared_locations": [link("world/locations/Quay")], "prepared_clues": [link(f"{cp}/clues/C-{campaign}-0002"), link(f"{cp}/clues/C-{campaign}-0001")]}
        if number == 3:
            props.update({"prepared_npcs": [], "prepared_locations": [], "prepared_clues": []})
        body = session_template
        for heading, kind in [("Secrets & Clues", "clues"), ("Locations", "locations"), ("Important NPCs", "npcs")]:
            body = re.sub(rf"(## {re.escape(heading)}\n).*?(?=\n## )", lambda m: m[1] + f"![[bases/prepared-{kind}.base]]\n\nFallback snapshot (explicit refresh):\n" + marker(kind) + "\n", body, flags=re.S)
        body = body.replace("## Events\n- N/A", "## Events\n- Met [[world/npcs/Events Only]].\n- Discussed [[campaign_1/clues/C-1-0001]].")
        path = f"{cp}/sessions/S-{campaign}-{number:03d}"
        write_note(root, path, props, body)
        refresh(root, path)
    # Mostly empty Active Clues sections, with 10% having an associated active clue.
    for i in range(corpus):
        path = f"world/npcs/Corpus/N-{i:05d}"
        write_note(root, path, {"type": link("types/NPC"), "summary": f"Synthetic dock worker {i}.", "campaign_1": {"first_session": None, "last_session": None}, "campaign_2": {"first_session": None, "last_session": None}, "view_campaign": "campaign_1"}, entity_body)
        if i % 10 == 0:
            write_note(root, f"campaign_1/clues/C-1-{1000 + i // 10:04d}", {"type": link("types/Clue"), "campaign": link("campaign_1/Campaign"), "view_campaign": "campaign_1", "status": link("statuses/Pending"), "subjects": [link(path)], "text": f"Unconfirmed signal {i}."}, "## Sessions\n![[bases/clue-sessions.base]]\n")
    repeated = "# Repeated entity embeds\n" + "\n".join(f"![[world/npcs/Corpus/N-{i:05d}#Active Clues]]" for i in range(min(corpus, 30)))
    write_note(root, "Repeated", {"view_campaign": "campaign_1"}, repeated)
    write_note(root, "Start", {}, "# Bases prototype\nDataview is absent; core Bases is enabled.\n\n- [[campaign_1/index/Clues]]\n- [[campaign_2/index/Clues]]\n- [[world/npcs/Mira]]\n- [[world/npcs/Visitors/Mira]]\n- [[world/locations/Empty]]\n- [[campaign_1/clues/C-1-0001]]\n- [[campaign_1/sessions/S-1-001]]\n- [[campaign_1/sessions/S-1-003]]\n- [[Repeated]]\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("destination", type=Path)
    b.add_argument("--corpus", type=int, default=0)
    r = sub.add_parser("refresh")
    r.add_argument("vault", type=Path)
    r.add_argument("session", help="Vault-relative qualified path without .md")
    args = parser.parse_args()
    start = time.perf_counter()
    if args.command == "build":
        if not 0 <= args.corpus <= 90000:
            parser.error("--corpus must be between 0 and 90000 (four-digit Clue IDs)")
        build(args.destination, args.corpus)
    else:
        refresh(args.vault, args.session)
    print(f"{args.command}: {time.perf_counter() - start:.3f}s")


if __name__ == "__main__":
    main()
