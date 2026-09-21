"""Deterministic fixture/fallback checks. These are NOT Bases rendering tests."""
import tempfile
from pathlib import Path
import unittest

import yaml

from prototype import HERE, build, canonical, link, read_note, refresh, write_note


class PrototypeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "vault"
        build(self.root)
        self.session = "campaign_1/sessions/S-1-001"

    def change(self, path, **values):
        props, body = read_note(self.root / (path + ".md"))
        props.update(values)
        write_note(self.root, path, props, body)

    def test_original_contract(self):
        for status in (self.root / "statuses").glob("*.md"):
            self.assertEqual(canonical(read_note(status)[0]["applies_to"]), "types/Clue")
        props, body = read_note(self.root / (self.session + ".md"))
        for heading in ["# Preparation", "## Starting scene", "## Other scenes", "## Secrets & Clues", "## Locations", "## Important NPCs", "## Scene notes", "## Encounters", "## Prepared rewards", "# Notes", "## Preamble", "## Events", "## Rewards", "### Loot"]:
            self.assertIn(heading, body)
        self.assertEqual(props["prepared_npcs"][0], link("world/npcs/Visitors/Mira"))
        self.assertNotIn("Events Only", str(props["prepared_npcs"]))
        self.assertTrue({"aliases", "players_absent", "in_game_start_date", "in_game_end_date"} <= props.keys())
        self.assertNotIn(None, props["aliases"])
        self.assertEqual(read_note(self.root / "campaign_1/Campaign.md")[0]["type"], link("types/Reference"))
        npc, _ = read_note(self.root / "world/npcs/Mira.md")
        self.assertTrue({"stats", "birth_year"} <= npc.keys())
        for base in (HERE / "bases").glob("*.base"):
            self.assertIn("views", yaml.safe_load(base.read_text()))

    def test_refresh_order_alias_long_text_and_idempotence(self):
        result = refresh(self.root, self.session)
        self.assertLess(result.index("| [[world/npcs/Visitors/Mira]]"), result.index(r"| [[world/npcs/Mira\|Lantern Keeper]]"))
        self.assertIn(r"[[world/locations/Quay\|the old quay]]", result)
        self.assertIn("<br>At low tide", result)
        self.assertEqual(result, refresh(self.root, self.session))
        self.change("world/npcs/Mira", summary="Updated summary")
        self.assertIn("Updated summary", refresh(self.root, self.session))

    def test_remove_add_carry_forward_preserves_events_and_sources(self):
        path = self.root / (self.session + ".md")
        events = path.read_text().split("# Notes\n", 1)[1]
        source = (self.root / "world/npcs/Mira.md").read_bytes()
        self.change(self.session, prepared_npcs=[])
        self.assertIn("No selections.", refresh(self.root, self.session))
        self.change(self.session, prepared_npcs=[link("world/npcs/Mira")])
        props, body = read_note(path)
        carried = "campaign_1/sessions/S-1-004"
        target, target_body = read_note(self.root / "campaign_1/sessions/S-1-003.md")
        for key in ("prepared_npcs", "prepared_locations", "prepared_clues"):
            target[key] = props[key]
        target["session_number"] = 4
        write_note(self.root, carried, target, target_body)
        self.assertIn("| [[world/npcs/Mira]]", refresh(self.root, carried))
        self.assertEqual(events, refresh(self.root, self.session).split("# Notes\n", 1)[1])
        self.assertEqual(source, (self.root / "world/npcs/Mira.md").read_bytes())

    def test_conflicts_fail_without_partial_write(self):
        path = self.root / (self.session + ".md")
        path.write_text(path.read_text().replace("A visiting glassblower", "Hand-edited glassblower"))
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Edited generated npcs"):
            refresh(self.root, self.session)
        self.assertEqual(before, path.read_bytes())

    def test_invalid_selections_fail_without_write(self):
        for selection in [link("campaign_2/clues/C-2-0001"), link("world/npcs/Mira"), link("../escape"), link("Mira")]:
            self.change(self.session, prepared_clues=[selection])
            before = (self.root / (self.session + ".md")).read_bytes()
            with self.assertRaises(ValueError):
                refresh(self.root, self.session)
            self.assertEqual(before, (self.root / (self.session + ".md")).read_bytes())

    def test_duplicate_and_missing_markers_refused(self):
        self.change(self.session, prepared_npcs=[link("world/npcs/Mira"), link("world/npcs/Mira", "Alias")])
        with self.assertRaisesRegex(ValueError, "Duplicate selection"):
            refresh(self.root, self.session)
        path = self.root / (self.session + ".md")
        path.write_text(path.read_text().replace("armarium:prep:clues", "removed:clues"))
        with self.assertRaisesRegex(ValueError, "markers"):
            refresh(self.root, self.session)

    def test_build_never_overwrites(self):
        with self.assertRaisesRegex(ValueError, "already exists"):
            build(self.root)

    def test_corpus_preserves_record_identity_and_state_defaults(self):
        root = Path(self.temp.name) / "corpus"
        build(root, corpus=20)
        self.assertTrue((root / "campaign_1/clues/C-1-1000.md").exists())
        self.assertTrue((root / "campaign_1/clues/C-1-1001.md").exists())
        self.assertEqual(len(list((root / "world/npcs/Corpus").glob("*.md"))), 20)
        npc, _ = read_note(root / "world/npcs/Corpus/N-00001.md")
        self.assertEqual(npc["campaign_2"], {"first_session": None, "last_session": None})
        clue, _ = read_note(root / "campaign_1/clues/C-1-1000.md")
        self.assertTrue({"first_session", "last_session"} <= clue.keys())


if __name__ == "__main__":
    unittest.main()
