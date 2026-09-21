"""Exercise edits with views open in a disposable prototype vault; restore records."""
import argparse
import json
from pathlib import Path

from observe import Observer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    o = Observer(args.vault)
    root = Path(o.js("JSON.stringify(app.vault.adapter.basePath)"))
    if not root.name.startswith("armarium-bases-") or not (root / "Start.md").exists():
        parser.error("Use a disposable armarium-bases-* fixture")
    paths = ["world/npcs/Mira.md", "campaign_1/clues/C-1-0001.md", "campaign_1/sessions/S-1-001.md", "campaign_1/sessions/S-1-002.md"]
    originals = {p: (root / p).read_text() for p in paths}
    results = []

    def observe(label, embed, expected=None, absent=None):
        capture = o.capture(embed)
        passed = all(x in capture["text"] for x in (expected or [])) and all(x not in capture["text"] for x in (absent or []))
        results.append({"label": label, "pass": passed, "expected": expected, "absent": absent, "capture": capture})
        args.output.write_text(json.dumps(results, indent=2) + "\n")

    try:
        o.open("world/npcs/Mira.md")
        observe("qualified alias matches keeper, excludes visiting duplicate", "bases/entity-clues.base", ["C-1-0001"], ["C-1-0002", "C-2-"])
        o.set_property(paths[0], "view_campaign", "campaign_2")
        observe("change shared entity display context without ownership", "bases/entity-clues.base", ["C-2-0001"], ["C-1-"])
        o.set_property(paths[0], "view_campaign", "campaign_1")
        o.set_property(paths[1], "subjects", ["[[world/npcs/Visitors/Mira|Lantern Keeper]]"])
        observe("alias label cannot impersonate canonical subject", "bases/entity-clues.base", ["0 results"], ["C-1-0001"])
        o.set_property(paths[1], "subjects", ["[[world/npcs/Mira|Renamed display]]"])
        observe("subject restored with different display alias", "bases/entity-clues.base", ["C-1-0001"])
        for state in ["Hinted", "Revealed", "Abandoned", "Dormant", "Superseded", "Pending"]:
            o.set_property(paths[1], "status", f"[[statuses/{state}]]")
            active = state in ("Pending", "Hinted")
            observe("open entity status -> " + state, "bases/entity-clues.base", ["C-1-0001"] if active else ["0 results"], [] if active else ["C-1-0001"])
        o.open(paths[2])
        o.set_property(paths[1], "text", "TEXT-EDIT-OBSERVED [[world/locations/Quay|quay]]")
        observe("source Clue text edited while prep open", "bases/prepared-clues.base", ["TEXT-EDIT-OBSERVED"])
        o.set_property(paths[0], "summary", "SUMMARY-EDIT-OBSERVED [[world/locations/Quay|quay]]")
        observe("source summary edited while prep open", "bases/prepared-npcs.base", ["SUMMARY-EDIT-OBSERVED"], ["Events Only"])
        o.set_property(paths[2], "prepared_npcs", [])
        observe("remove all prep without changing Events", "bases/prepared-npcs.base", ["0 results"])
        o.set_property(paths[2], "prepared_npcs", ["[[world/npcs/Mira]]", "[[world/npcs/Visitors/Mira]]"])
        observe("add and reorder prep", "bases/prepared-npcs.base", ["2 results", "SUMMARY-EDIT-OBSERVED"], ["Events Only"])
        # Carry only deliberate selection lists into a different session. Events are untouched.
        for prop in ["prepared_npcs", "prepared_locations", "prepared_clues"]:
            value = o.js(f"JSON.stringify(app.metadataCache.getFileCache(app.vault.getAbstractFileByPath({json.dumps(paths[2])})).frontmatter[{json.dumps(prop)}])")
            o.set_property(paths[3], prop, value)
        o.open(paths[3])
        observe("carried selections render on next session", "bases/prepared-npcs.base", ["2 results", "SUMMARY-EDIT-OBSERVED"])
        for p in paths[2:]:
            results.append({"label": "Events preserved: " + p, "pass": (root / p).read_text().split("# Notes\n", 1)[1] == originals[p].split("# Notes\n", 1)[1]})
    finally:
        for p, content in originals.items():
            o.js("(async()=>{await app.vault.modify(app.vault.getAbstractFileByPath(" + json.dumps(p) + ")," + json.dumps(content) + ");return JSON.stringify(true);})()")
        args.output.write_text(json.dumps(results, indent=2) + "\n")
    if not all(r["pass"] for r in results):
        raise SystemExit("Some observations failed; see evidence (do not treat as success)")


if __name__ == "__main__":
    main()
