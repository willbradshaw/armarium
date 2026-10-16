"""Check shipped view wiring and selections; rendering is tested in Obsidian."""

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2] / "vaults"
VAULTS = (ROOT / "starter", ROOT / "example")
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
        for vault in VAULTS:
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
        for folder in ["bases", "reference/views", ".obsidian/snippets"]:
            starter, example = ROOT / "starter" / folder, ROOT / "example" / folder
            self.assertEqual(
                {p.name for p in starter.iterdir()}, {p.name for p in example.iterdir()}
            )
            for path in starter.iterdir():
                self.assertEqual(path.read_bytes(), (example / path.name).read_bytes())

    def test_every_campaign_index_embeds_the_correct_status_views(self):
        for path in (
            path
            for vault in VAULTS
            for path in vault.glob("campaigns/*/reference/indexes/Clues.md")
        ):
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
        for vault in VAULTS:
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
        for path in (path for vault in VAULTS for path in vault.rglob("*.md")):
            with self.subTest(path=path):
                self.assertNotRegex(
                    path.read_text(), r"(?im)^\s*`{3,}dataview(?:js)?\b|`\s*="
                )


def type_fields(kind: str) -> dict[str, str | None]:
    """Map each field docs/type.md documents for a type to its subtype, or None."""
    docs = Path(__file__).resolve().parents[2] / "docs/type.md"
    section = docs.read_text().split(f"\n## {kind}\n", 1)[1].split("\n## ", 1)[0]
    return {
        field: subtype or None
        for names, subtype in re.findall(
            r"^\| ((?:`\w+`(?:, )?)+) \| (?:required|optional)(?: for (\w+))?",
            section,
            re.M,
        )
        for field in re.findall(r"`(\w+)`", names)
    }


def base(name: str) -> dict:
    return yaml.safe_load((ROOT / "starter/bases" / name).read_text())


def example_records(kind: str, subtype: str | None = None) -> list[Path]:
    """Find the example vault's records of a type, and optionally a subtype."""
    vault = ROOT / "example"
    return [
        path
        for path in vault.rglob("*.md")
        if path.relative_to(vault).parts[0] in {"content", "campaigns"}
        and (metadata := frontmatter(path)).get("type") == f"[[types/{kind}]]"
        and (subtype is None or metadata.get("subtype") == subtype)
    ]


class BrowsingBaseTests(unittest.TestCase):
    """Check every base in bases/ against its type and the example vault."""

    TYPES = {
        "Content.base": "Content",
        "Sessions.base": "Session",
        "Clues.base": "Clue",
    }
    CAMPAIGN = 'file.folder.split("/")[1]'

    @staticmethod
    def subtype(view: dict) -> str | None:
        """Return the Content subtype a table selects, or None."""
        match = re.fullmatch(r'subtype == "([A-Za-z]+)"', view.get("filters", ""))
        return match and match[1]

    def test_ships_one_base_per_browsed_type(self):
        self.assertEqual(
            {path.name for path in (ROOT / "starter/bases").iterdir()},
            set(self.TYPES),
        )

    def test_selects_records_by_type_outside_templates(self):
        for name, kind in self.TYPES.items():
            with self.subTest(base=name):
                self.assertEqual(
                    base(name)["filters"],
                    {
                        "and": [
                            'file.ext == "md"',
                            '!file.inFolder("reference")',
                            f'type == link("reference/types/{kind}")',
                        ]
                    },
                )
                self.assertTrue(example_records(kind))

    def test_columns_are_labelled_and_defined(self):
        for name in self.TYPES:
            data = base(name)
            formulas = {f"formula.{key}" for key in data.get("formulas", {})}
            used, sorted_by = set(), set()
            for view in data["views"]:
                self.assertEqual(view["type"], "table")
                for column in view["order"]:
                    with self.subTest(base=name, view=view["name"], column=column):
                        if column.startswith("formula."):
                            self.assertIn(column, formulas)
                        key = column if "." in column else f"note.{column}"
                        self.assertIn(key, data["properties"])
                        used.add(key)
                if "groupBy" in view:
                    used.add(view["groupBy"]["property"])
                sorted_by |= {sort["property"] for sort in view.get("sort", [])}
            with self.subTest(base=name):
                self.assertEqual(used, set(data["properties"]))
                # A formula only sorted by needs no label.
                self.assertLessEqual(formulas, used | sorted_by)

    def test_fields_are_documented_for_the_type_and_subtype(self):
        for name, kind in self.TYPES.items():
            fields = type_fields(kind)
            for view in base(name)["views"]:
                subtype = self.subtype(view)
                properties = view["order"] + [
                    sort["property"] for sort in view.get("sort", [])
                ]
                for field in (p for p in properties if "." not in p):
                    with self.subTest(base=name, view=view["name"], field=field):
                        self.assertIn(field, fields)
                        self.assertIn(fields[field], {None, subtype})

    def test_campaign_records_are_grouped_by_campaign_folder(self):
        for name in ("Sessions.base", "Clues.base"):
            data = base(name)
            with self.subTest(base=name):
                self.assertEqual(data["formulas"]["campaign"], self.CAMPAIGN)
                for view in data["views"]:
                    self.assertEqual(
                        view["groupBy"],
                        {"property": "formula.campaign", "direction": "ASC"},
                    )
                campaigns = {
                    path.relative_to(ROOT / "example").parts[1]
                    for path in example_records(self.TYPES[name])
                }
                self.assertGreater(len(campaigns), 1)


class ContentBaseTests(unittest.TestCase):
    """Check bases/Content.base's tables against the core subtypes."""

    BASE = base("Content.base")
    SUBTYPES = {"NPC", "PC", "Location", "Faction", "Object", "Lore", "Date", "Gear"}

    def test_opens_on_all_content(self):
        first = self.BASE["views"][0]
        self.assertEqual(first["name"], "All")
        self.assertNotIn("filters", first)
        self.assertIn("subtype", first["order"])

    def test_each_core_subtype_has_one_table(self):
        subtypes = [BrowsingBaseTests.subtype(view) for view in self.BASE["views"][1:]]
        self.assertCountEqual(subtypes, self.SUBTYPES)
        for subtype in self.SUBTYPES:
            with self.subTest(subtype=subtype):
                self.assertTrue(example_records("Content", subtype))

    def test_scope_names_the_campaign_or_shared(self):
        self.assertEqual(
            self.BASE["formulas"]["scope"],
            f'if(file.inFolder("campaigns"), {BrowsingBaseTests.CAMPAIGN}, "shared")',
        )


class SessionsBaseTests(unittest.TestCase):
    """Check bases/Sessions.base's one table of Sessions."""

    (VIEW,) = base("Sessions.base")["views"]

    def test_sorts_newest_first(self):
        self.assertEqual(
            self.VIEW["sort"], [{"property": "session_number", "direction": "DESC"}]
        )

    def test_shows_every_prepared_list(self):
        prepared = {field for field in type_fields("Session") if "prepared" in field}
        self.assertEqual(len(prepared), 3)
        self.assertLessEqual(prepared, set(self.VIEW["order"]))

    def test_transcript_is_the_linking_transcript(self):
        self.assertEqual(
            base("Sessions.base")["formulas"]["transcript"],
            "file.backlinks.filter(value.asFile().properties.type"
            ' == link("reference/types/Transcript"))',
        )


class CluesBaseTests(unittest.TestCase):
    """Check bases/Clues.base agrees with the campaign clue index."""

    def test_opens_on_all_clues(self):
        self.assertNotIn("filters", base("Clues.base")["views"][0])

    def test_sorts_by_status_then_id(self):
        statuses = [
            path.stem
            for path in (ROOT / "starter/reference/statuses").glob("*.md")
            if "Clue" in path.read_text()
        ]
        order = re.findall(
            r'link\("reference/statuses/(\w+)"\)',
            base("Clues.base")["formulas"]["status_order"],
        )
        self.assertEqual(
            order,
            ["Pending", "Hinted", "Revealed", "Dormant", "Abandoned", "Superseded"],
        )
        self.assertCountEqual(order, statuses)
        for view in base("Clues.base")["views"]:
            with self.subTest(view=view["name"]):
                self.assertEqual(
                    [sort["property"] for sort in view["sort"]],
                    ["formula.status_order", "file.name"],
                )

    def test_active_table_matches_the_index(self):
        index = yaml.safe_load(
            (ROOT / "starter/reference/views/clue-index.base").read_text()
        )
        active = {view["name"]: view for view in base("Clues.base")["views"]}["Active"]
        self.assertEqual(
            active["filters"],
            {view["name"]: view for view in index["views"]}["Active"]["filters"],
        )


if __name__ == "__main__":
    unittest.main()
