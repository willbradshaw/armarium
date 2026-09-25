"""Check shipped view wiring and selections; rendering is tested in Obsidian."""

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2] / "vaults"
SELECTIONS = {"clues": "Clue", "locations": "Location", "npcs": "NPC"}


def frontmatter(path: Path) -> dict:
    """Read trusted repository fixtures, including untyped supporting records."""
    text = path.read_text()
    if not text.startswith("---\n"):
        return {}
    return yaml.safe_load(text[4:].split("\n---\n", 1)[0]) or {}


def resolve(vault: Path, link: str) -> Path:
    """Resolve a canonical fixture link by its unique path suffix."""
    target = link.removeprefix("[[").removesuffix("]]")
    matches = [
        path
        for path in vault.rglob("*.md")
        if path.relative_to(vault).with_suffix("").as_posix() == target
        or path.relative_to(vault).with_suffix("").as_posix().endswith("/" + target)
    ]
    if len(matches) != 1:
        raise AssertionError(f"{vault.name}: {link}: {matches}")
    return matches[0]


class ViewTests(unittest.TestCase):
    def test_all_base_embeds_resolve_in_each_vault(self):
        for vault in ROOT.iterdir():
            if not vault.is_dir():
                continue
            embedded = set()
            for path in vault.rglob("*.md"):
                for target, view in re.findall(
                    r"!\[\[([^\]#]+\.base)(?:#([^\]]+))?\]\]", path.read_text()
                ):
                    with self.subTest(path=path, target=target, view=view):
                        base = vault / target
                        self.assertTrue(base.is_file())
                        data = yaml.safe_load(base.read_text())
                        self.assertTrue(data["views"])
                        if view:
                            self.assertIn(
                                view, [item["name"] for item in data["views"]]
                            )
                        embedded.add(base)
            self.assertEqual(embedded, set((vault / "reference/views").glob("*.base")))

    def test_views_and_styling_are_mirrored(self):
        for folder in ["reference/views", ".obsidian/snippets"]:
            starter, example = ROOT / "starter" / folder, ROOT / "example" / folder
            self.assertEqual(
                {p.name for p in starter.iterdir()}, {p.name for p in example.iterdir()}
            )
            for path in starter.iterdir():
                self.assertEqual(path.read_bytes(), (example / path.name).read_bytes())

    def test_every_campaign_index_embeds_the_correct_status_views(self):
        for path in ROOT.glob("*/campaigns/*/reference/indexes/Clues.md"):
            with self.subTest(path=path):
                for heading in ["Active", "Closed"]:
                    section = (
                        path.read_text()
                        .split("## " + heading + "\n", 1)[1]
                        .split("\n## ", 1)[0]
                    )
                    self.assertEqual(
                        section.strip(),
                        f"![[reference/views/clue-index.base#{heading}]]",
                    )

    def test_preparation_selections_resolve_to_the_right_kind_and_campaign(self):
        vault = ROOT / "example"
        exercised = set()
        for campaign in (vault / "campaigns").iterdir():
            if not campaign.is_dir():
                continue
            for path in (campaign / "sessions").glob("*.md"):
                record = frontmatter(path)
                preparation = path.read_text().split("# Notes", 1)[0]
                for key, kind in SELECTIONS.items():
                    with self.subTest(session=path.name, selection=key):
                        self.assertIn(
                            f"![[reference/views/prepared-{key}.base]]", preparation
                        )
                        links = record[f"prepared_{key}"]
                        self.assertEqual(len(links), len(set(links)))
                        for link in links:
                            target = resolve(vault, link)
                            metadata = frontmatter(target)
                            if kind == "Clue":
                                self.assertEqual(metadata["type"], "[[types/Clue]]")
                                self.assertTrue(
                                    target.is_relative_to(campaign / "clues")
                                )
                            else:
                                self.assertEqual(metadata["type"], "[[types/Content]]")
                                self.assertEqual(metadata["subtype"], kind)
                                self.assertTrue(
                                    target.is_relative_to(vault / "content")
                                    or target.is_relative_to(campaign / "content")
                                )
                            exercised.add((campaign.name, key))
        self.assertEqual(
            exercised,
            {
                (p.name, key)
                for p in (vault / "campaigns").iterdir()
                if p.is_dir()
                for key in SELECTIONS
            },
        )

    def test_every_content_and_clue_uses_its_shared_view(self):
        for vault in ROOT.iterdir():
            for path in vault.rglob("*.md"):
                kind = frontmatter(path).get("type")
                if kind in {"[[types/Clue]]", "[[types/Content]]"}:
                    target = (
                        "clue-sessions" if kind == "[[types/Clue]]" else "content-clues"
                    )
                    self.assertEqual(
                        path.read_text().count(f"![[reference/views/{target}.base]]"),
                        1,
                        str(path),
                    )

    def test_shipped_vaults_have_no_dataview_expressions(self):
        for path in ROOT.rglob("*.md"):
            with self.subTest(path=path):
                self.assertNotRegex(
                    path.read_text(), r"(?im)^\s*`{3,}dataview(?:js)?\b|`\s*="
                )


if __name__ == "__main__":
    unittest.main()
