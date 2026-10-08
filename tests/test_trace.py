"""Tracing lists resolved links to one record with their locations."""

from pathlib import Path
from unittest.mock import patch

import pytest

from armarium.index import VaultIndex
from armarium.lib import record_files
from armarium.parse import Body
from armarium.trace import (
    Reference,
    _final_segment,
    _frontmatter_text,
    _locate,
    _mentions,
    _references,
    _sharing,
    _spelling,
    _spellings,
    trace_outbound,
    trace_record,
)

SESSION = """---
type: "[[Session]]"
prepared_locations: ["[[Quay Nine]]", "[[Port Briselle]]"]
---
Opening at [[quay nine]].
# Preparation
## Locations
![[content/Quay Nine]]
# Notes
## Events
The crew met at [[Quay Nine|the quay]] and again at [[Quay Nine#Notes]].
- Sailed for [[Port Briselle]].
### Aftermath
`[[Quay Nine.md]]`
"""


def write(root: Path, relative: str, text: str = "") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault with spaces"
    for directory in ("reference/types", "campaigns"):
        (root / directory).mkdir(parents=True)
    write(
        root,
        "content/Quay Nine.md",
        "---\naliases: [The Ninth]\n---\n## Notes\nSee [[Quay Nine]] and [[#Notes]].\n",
    )
    write(root, "content/Port Briselle.md", "---\naliases: [The Ninth Port]\n---\n")
    write(root, "campaigns/campaign_1/sessions/S-1-001.md", SESSION)
    write(
        root,
        "content/Shoal Chart.md",
        '---\ncampaign_1:\n  held_by: ["[[Mara]]", "[[Quay Nine]]"]\n'
        'found: "[[Quay Nine]] or [[Quay Nine]]"\n---\n'
        "A chart of [[Quay Ninety]] and [[Quay Nine]] [[Quay Nine]].\n",
    )
    write(root, "content/Mara.md", "Quay Nine without a link, and [[Quay Nine\n")
    write(root, "assets/Quay Nine.png", "image")
    return root


class TestReferenceText:
    @pytest.mark.parametrize(
        ("reference", "expected"),
        [
            (Reference("content/Mara.md", "Notes > Events", 12), "Notes > Events\t12"),
            (Reference("content/Mara.md", "", 3), "\t3"),
            (
                Reference("content/Mara.md", "campaign_1.held_by", 0),
                "campaign_1.held_by\t",
            ),
        ],
    )
    def test_tab_separated(self, reference: Reference, expected: str) -> None:
        assert reference.text == f"content/Mara.md\t{expected}"


class TestSpellings:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("Quay Nine.md", {"quay nine.md", "quay nine"}),
            ("Café.MD", {"café.md", "café"}),
            ("Cafe\u0301.md", {"café.md", "café"}),
            ("Quay Nine.md.md", {"quay nine.md.md", "quay nine.md"}),
            ("Map.PNG", {"map.png"}),
            ("README", {"readme"}),
        ],
    )
    def test_names(self, name: str, expected: set[str]) -> None:
        assert _spellings(Path("content") / name) == expected


class TestSharing:
    FILES = [
        Path("content/Mara.md"),
        Path("notes/MARA.md"),
        Path("assets/Mara"),
        Path("assets/Mara.png"),
        Path("content/Mara.md.md"),
        Path("content/Quay Nine.md"),
    ]

    @pytest.mark.parametrize(
        ("spellings", "expected"),
        [
            ({"mara.md", "mara"}, [0, 1, 2, 4]),
            ({"mara.png"}, [3]),
            ({"mara.md.md", "mara.md"}, [0, 1, 4]),
            ({"quay nine"}, [5]),
            ({"gull"}, []),
            (set(), []),
        ],
    )
    def test_files_with_a_spelling(
        self, spellings: set[str], expected: list[int]
    ) -> None:
        assert _sharing(self.FILES, spellings) == [self.FILES[i] for i in expected]

    def test_no_files(self) -> None:
        assert _sharing([], {"mara"}) == []


class TestFinalSegment:
    @pytest.mark.parametrize(
        ("target", "expected"),
        [
            ("Quay Nine", "quay nine"),
            ("content/Quay Nine.md", "quay nine.md"),
            ("/content/CAFÉ", "café"),
            ("campaigns/campaign_1/content/Cafe\u0301", "café"),
            ("", ""),
            ("content/", ""),
        ],
    )
    def test_segment(self, target: str, expected: str) -> None:
        assert _final_segment(target) == expected


class TestLocate:
    @pytest.mark.parametrize(
        "relative",
        ["content/Quay Nine.md", "assets/Quay Nine.png", "content/.Hidden.md"],
    )
    @pytest.mark.parametrize("form", ["vault", "vault_absolute", "cwd", "absolute"])
    def test_finds_file_and_vault(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch, relative: str, form: str
    ) -> None:
        write(vault, "content/.Hidden.md")
        root = vault.resolve()
        if form == "vault":
            monkeypatch.chdir(vault.parent)
            located = _locate(Path(relative), vault)
        elif form == "vault_absolute":
            located = _locate(vault / relative, vault)
        elif form == "cwd":
            monkeypatch.chdir(vault / "content")
            located = _locate(Path("..") / relative, None)
        else:
            located = _locate(vault / relative, None)
        assert located == (root, root / relative)

    def test_vault_relative_path_ignores_the_working_directory(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(vault / "content")
        with pytest.raises(ValueError, match="does not exist"):
            _locate(Path("Quay Nine.md"), vault)
        assert _locate(Path("Quay Nine.md"), None)[1].name == "Quay Nine.md"

    @pytest.mark.parametrize(
        ("relative", "message"),
        [
            (
                "content/Gull.md",
                "content/Gull.md does not exist; give a file path, which armarium "
                "find lists for a name$",
            ),
            ("content", "content is a directory, not a file$"),
            ("", "is a directory, not a file$"),
            ("content/Linked.md", "content/Linked.md is a symlink$"),
            ("content/Dangling.md", "content/Dangling.md is a symlink$"),
        ],
    )
    @pytest.mark.parametrize("explicit", [False, True])
    def test_rejects_what_is_not_a_file(
        self, vault: Path, relative: str, message: str, explicit: bool
    ) -> None:
        (vault / "content/Linked.md").symlink_to(vault / "content/Quay Nine.md")
        (vault / "content/Dangling.md").symlink_to(vault / "content/Missing.md")
        with pytest.raises(ValueError, match=message):
            if explicit:
                _locate(Path(relative), vault)
            else:
                _locate(vault / relative, None)

    def test_rejects_file_outside_any_vault(self, tmp_path: Path) -> None:
        outside = write(tmp_path, "Loose.md")
        with pytest.raises(ValueError, match="cannot infer vault"):
            _locate(outside, None)

    @pytest.mark.parametrize("escape", ["absolute", "relative"])
    def test_rejects_file_outside_the_given_vault(
        self, vault: Path, tmp_path: Path, escape: str
    ) -> None:
        outside = write(tmp_path, "Loose.md")
        path = outside if escape == "absolute" else Path("../Loose.md")
        with pytest.raises(ValueError, match="inside the selected vault"):
            _locate(path, vault)

    @pytest.mark.parametrize("kind", ["missing", "inside", "plain"])
    def test_rejects_vault_that_is_not_a_vault_root(
        self, vault: Path, tmp_path: Path, kind: str
    ) -> None:
        given = {
            "missing": tmp_path / "nowhere",
            "inside": vault / "content",
            "plain": tmp_path,
        }[kind]
        with pytest.raises(ValueError):
            _locate(Path("content/Quay Nine.md"), given)


class TestSpelling:
    @pytest.mark.parametrize(
        ("needle", "text", "expected"),
        [
            ("quay nine", "[[quay nine]]", True),
            ("quay nine", "[[ quay nine ]]", True),
            ("quay nine", "[[content/quay nine.md]]", True),
            ("quay nine", "[[/content/quay nine#notes]]", True),
            ("quay nine", "[[quay nine|the quay]]", True),
            ("quay nine", "| [[quay nine\\|the quay]] |", True),
            ("quay nine", "quay nine", False),
            ("quay nine", "[[old quay nine]]", True),
            ("quay nine", "[[quay nine", False),
            ("quay nine", "[[quay ninety]]", False),
            ("quay nine", "[[quay nine/pier]]", False),
            ("quay nine", "[[pier|quay nine]]", True),
            ("quay nine", "[[quay nine.png]]", False),
            ("c++ (draft)", "[[c++ (draft)]]", True),
            ("map.png", "![[assets/map.png]]", True),
        ],
    )
    def test_text_pattern(self, needle: str, text: str, expected: bool) -> None:
        pattern, ascii_bytes = _spelling(needle)
        assert bool(pattern.search(text)) is expected
        assert ascii_bytes is not None
        assert bool(ascii_bytes.search(text.encode())) is expected

    def test_non_ascii_name(self) -> None:
        pattern, ascii_bytes = _spelling("café")
        assert pattern.search("[[café]]") and ascii_bytes is None


class TestFrontmatterText:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("---\nat: '[[Mara''s Rest]]'\n---\n", "--- at: '[[mara's rest]]'"),
            (
                "---\ntext: Seen at [[Quay\n  Nine]].\n---\n",
                "--- text: seen at [[quay nine]].",
            ),
            ("---\nat: \"[[CAFÉ]]\"\n---\nBody ''\n", '--- at: "[[café]]"'),
            ("﻿---\na: 1\n---\n", "--- a: 1"),
            ("---\na: 1\n", ""),
            ("No frontmatter ''\n---\n", ""),
            ("", ""),
        ],
    )
    def test_text(self, text: str, expected: str) -> None:
        assert _frontmatter_text(text.encode()) == expected

    def test_undecodable(self) -> None:
        with pytest.raises(UnicodeError):
            _frontmatter_text(b"---\na: \xff\n---\n")


class TestMentions:
    @pytest.mark.parametrize(
        ("text", "needle", "expected"),
        [
            ("---\nat: '[[Mara''s Rest]]'\n---\n", "mara's rest", True),
            ("---\nat: '[[Mara''s Rest]]'\n---\n", "mara's nest", False),
            ("---\ntext: Seen at [[Quay\n  Nine]].\n---\n", "quay nine", True),
            ('---\nat: "[[Caf\\xE9]]"\n---\n', "café", True),
            ("Body, at '[[Mara''s Rest]]'\n", "mara's rest", False),
            ("---\na: 1\n---\nA table cell \\| here.\n", "quay nine", False),
            ("See [[Quay Nine]].", "quay nine", True),
            ("See [[content/QUAY NINE.md|the quay]].", "quay nine", True),
            ("See [[Quay Eight]].", "quay nine", False),
            ("Quay Nine, unlinked.", "quay nine", False),
            ("", "quay nine", False),
            ("See [[Café]] — twice.", "café", True),
            ("See [[Cafe\u0301]].", "café", True),
            ("See [[CAFÉ]].", "café", True),
            ("See [[Cafe]].", "café", False),
            ("Seen — at [[Quay Nine]].", "quay nine", True),
            ("Seen — at [[Quay Eight]].", "quay nine", False),
        ],
    )
    def test_text(self, text: str, needle: str, expected: bool) -> None:
        assert _mentions(text.encode(), needle) is expected

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b"\xef\xbb\xbf[[Quay Nine]]", True),
            (b"[[Quay Nine]] \xff", False),
        ],
    )
    def test_bytes(self, data: bytes, expected: bool) -> None:
        assert _mentions(data, "quay nine") is expected


class TestReferences:
    @pytest.fixture
    def index(self, vault: Path) -> VaultIndex:
        return VaultIndex(vault)

    def references(self, index: VaultIndex, text: str) -> list[Reference]:
        return _references(
            index.root / "content/Shoal Chart.md",
            text.encode(),
            index,
            index.root / "content/Quay Nine.md",
        )

    def test_frontmatter_and_body(self, index: VaultIndex) -> None:
        text = (
            '---\nseen: ["[[Mara]]", "[[Quay Nine]]"]\n---\n[[quay nine|here]]\n'
            "# Notes\n## Events\n![[content/Quay Nine.md#Notes]] [[Port Briselle]]\n"
        )
        assert self.references(index, text) == [
            Reference("content/Shoal Chart.md", "seen", 0),
            Reference("content/Shoal Chart.md", "", 4),
            Reference("content/Shoal Chart.md", "Notes > Events", 7),
        ]

    @pytest.mark.parametrize(
        "text",
        [
            '---\nseen: "[[Quay Nine]]"\n---\n# Notes\n[[Port Briselle]] [[#Notes]]\n',
            "# Notes\n[[Quay Ninety]] [[Old Quay Nine]] [[Quay Nine\n",
            "",
        ],
    )
    def test_body_structure_is_parsed_only_for_body_links(
        self, index: VaultIndex, text: str
    ) -> None:
        with patch.object(Body, "__init__") as body:
            self.references(index, text)
        assert not body.called

    @pytest.mark.parametrize(
        "data",
        [
            b"---\nseen: [\n---\n[[Quay Nine]]\n",
            b"---\nseen: x\n[[Quay Nine]]\n",
            b"---\n- item\n---\n[[Quay Nine]]\n",
            b"[[Quay Nine]] \xff",
        ],
    )
    def test_unparseable_record(self, index: VaultIndex, data: bytes) -> None:
        path, target = (
            index.root / "content/Mara.md",
            index.root / "content/Quay Nine.md",
        )
        assert _references(path, data, index, target) == []

    def test_unparseable_body(self, index: VaultIndex) -> None:
        with patch.object(Body, "__init__", side_effect=RecursionError):
            assert self.references(index, '---\nseen: "[[Quay Nine]]"\n---\n') != []
            assert self.references(index, "[[Quay Nine]]\n") == []


class TestTraceRecord:
    def test_lists_links_with_locations(self, vault: Path) -> None:
        target, references = trace_record(Path("content/Quay Nine.md"), vault)
        assert target == "content/Quay Nine.md"
        session = "campaigns/campaign_1/sessions/S-1-001.md"
        assert [(r.relative, r.where, r.line) for r in references] == [
            (session, "prepared_locations", 0),
            (session, "", 5),
            (session, "Preparation > Locations", 8),
            (session, "Notes > Events", 11),
            (session, "Notes > Events > Aftermath", 14),
            ("content/Shoal Chart.md", "campaign_1.held_by", 0),
            ("content/Shoal Chart.md", "found", 0),
            ("content/Shoal Chart.md", "", 6),
        ]

    @pytest.mark.parametrize("form", ["vault", "vault_absolute", "cwd", "absolute"])
    def test_path_forms_agree(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch, form: str
    ) -> None:
        expected = trace_record(Path("content/Port Briselle.md"), vault)
        if form == "vault":
            monkeypatch.chdir(vault.parent)
            traced = trace_record(Path("content/Port Briselle.md"), vault)
        elif form == "vault_absolute":
            traced = trace_record(vault / "content/Port Briselle.md", vault)
        elif form == "cwd":
            monkeypatch.chdir(vault / "campaigns")
            traced = trace_record(Path("../content/Port Briselle.md"))
        else:
            traced = trace_record(vault / "content/Port Briselle.md")
        assert traced == expected
        assert traced[0] == "content/Port Briselle.md" and len(traced[1]) == 2

    def test_no_links(self, vault: Path) -> None:
        assert trace_record(Path("content/Shoal Chart.md"), vault) == (
            "content/Shoal Chart.md",
            [],
        )

    def test_traces_an_asset(self, vault: Path) -> None:
        write(vault, "content/Map.md", "## Notes\n![[Quay Nine.png]]\n")
        assert trace_record(Path("assets/Quay Nine.png"), vault) == (
            "assets/Quay Nine.png",
            [Reference("content/Map.md", "Notes", 2)],
        )

    @pytest.mark.parametrize(
        ("frontmatter", "where"),
        [
            ("at: '[[Mara''s Rest]]'", "at"),
            ("text: Last seen at [[Mara's\n  Rest]] before the hearing.", "text"),
            ('at: "[[Mara\\u0027s Rest]]"', "at"),
        ],
    )
    def test_finds_links_as_yaml_reads_them(
        self, vault: Path, frontmatter: str, where: str
    ) -> None:
        write(vault, "content/Mara's Rest.md")
        write(vault, "content/Pier.md", f"---\n{frontmatter}\n---\n")
        assert trace_record(Path("content/Mara's Rest.md"), vault)[1] == [
            Reference("content/Pier.md", where, 0)
        ]

    def test_follows_resolution_not_spelling(self, vault: Path) -> None:
        # A second Quay Nine makes the bare name ambiguous, so only links
        # spelling the path still resolve to the first.
        write(vault, "notes/Quay Nine.md", "[[content/Quay Nine]]\n")
        _, references = trace_record(Path("content/Quay Nine.md"), vault)
        assert [(r.relative, r.line) for r in references] == [
            ("campaigns/campaign_1/sessions/S-1-001.md", 8),
            ("notes/Quay Nine.md", 1),
        ]

    def test_reports_the_path_as_the_scan_spells_it(self, vault: Path) -> None:
        # A case-insensitive filesystem opens the file under another spelling.
        spelled = vault / "content/quay nine.md"
        if not spelled.exists():
            pytest.skip("filesystem is case-sensitive")
        target, references = trace_record(spelled)
        assert target == "content/Quay Nine.md" and len(references) == 8

    def test_skips_non_records(self, vault: Path) -> None:
        for relative in (
            "reference/templates/Content.md",
            "reference/extensions/example/templates/Location.md",
            "scripts/README.md",
            ".scratch/Draft.md",
            "content/.Draft.md",
            "content/Draft.txt",
        ):
            write(vault, relative, "[[Shoal Chart]]\n")
        (vault / "content/Linked.md").symlink_to(vault / "content/Shoal Chart.md")
        assert trace_record(Path("content/Shoal Chart.md"), vault)[1] == []

    def test_skips_unparseable_and_unreadable_records(self, vault: Path) -> None:
        write(vault, "content/Broken.md", "---\nx: [\n---\n[[Shoal Chart]]\n")
        (vault / "content/Bytes.md").write_bytes(b"[[Shoal Chart]] \xff")
        unreadable = write(vault, "content/Locked.md", "[[Shoal Chart]]\n").resolve()
        read = Path.read_bytes

        def read_bytes(path: Path) -> bytes:
            if path == unreadable:
                raise OSError("unreadable")
            return read(path)

        with patch.object(Path, "read_bytes", read_bytes):
            assert trace_record(Path("content/Shoal Chart.md"), vault)[1] == []

    def test_parses_only_records_naming_the_target(self, vault: Path) -> None:
        with patch("armarium.trace._references", wraps=_references) as references:
            trace_record(Path("content/Port Briselle.md"), vault)
        assert [call.args[0].name for call in references.call_args_list] == [
            "S-1-001.md"
        ]

    def test_indexes_only_files_sharing_the_name(self, vault: Path) -> None:
        write(vault, "notes/Quay Nine.md")
        with patch("armarium.trace.VaultIndex", wraps=VaultIndex) as index:
            trace_record(Path("content/Quay Nine.md"), vault)
        root = vault.resolve()
        assert [sorted(call.args[1]) for call in index.call_args_list] == [
            [root / "content/Quay Nine.md", root / "notes/Quay Nine.md"]
        ]

    def test_matches_the_whole_vault_index(self, vault: Path) -> None:
        # Every link the full index resolves to the target is listed, and no other.
        write(vault, "notes/Quay Nine.md", "[[content/Quay Nine]] [[Quay Nine]]\n")
        write(vault, "content/Quay Nine.md.md", "[[Quay Nine.md]] [[Quay Nine]]\n")
        index = VaultIndex(vault)
        for relative in (
            "content/Quay Nine.md",
            "notes/Quay Nine.md",
            "content/Quay Nine.md.md",
        ):
            target, references = trace_record(Path(relative), vault)
            assert target == relative
            expected = set()
            for path in record_files(index.root, index.root):
                record, _ = index.parse(path)
                if record is None or path == index.root / relative:
                    continue
                for link in record.links:
                    if link.target and not link.error:
                        if index.resolve(link.target, path)[0] == index.root / relative:
                            expected.add(
                                (path.relative_to(index.root).as_posix(), link.line)
                            )
            assert {(r.relative, r.line) for r in references} == expected

    @pytest.mark.parametrize(
        "relative",
        [
            "content/.Hidden.md",
            ".scratch/Draft.md",
            "node_modules/package/README.md",
            "content/__pycache__/Cached.md",
        ],
    )
    @pytest.mark.parametrize("explicit", [False, True])
    def test_rejects_entries_the_scan_skips(
        self, vault: Path, relative: str, explicit: bool
    ) -> None:
        write(vault, relative)
        with pytest.raises(ValueError, match="is not part of the vault: hidden"):
            if explicit:
                trace_record(Path(relative), vault)
            else:
                trace_record(vault / relative)

    def test_traces_through_a_symlinked_directory_to_a_vault_file(
        self, vault: Path
    ) -> None:
        (vault / "shortcut").symlink_to(vault / "content", target_is_directory=True)
        assert trace_record(vault / "shortcut/Port Briselle.md") == trace_record(
            vault / "content/Port Briselle.md"
        )

    @pytest.mark.parametrize("relative", ["content/Gull.md", "content", "../Loose.md"])
    def test_rejects_unusable_path(self, vault: Path, relative: str) -> None:
        write(vault.parent, "Loose.md")
        with pytest.raises(ValueError):
            trace_record(Path(relative), vault)


class TestTraceOutbound:
    QUAY = "content/Quay Nine.md"
    PORT = "content/Port Briselle.md"
    SESSION = "campaigns/campaign_1/sessions/S-1-001.md"

    def test_lists_links_in_order_with_locations(self, vault: Path) -> None:
        source, references, unresolved = trace_outbound(Path(self.SESSION), vault)
        assert source == self.SESSION
        assert [(r.relative, r.where, r.line) for r in references] == [
            (self.QUAY, "prepared_locations", 0),
            (self.PORT, "prepared_locations", 0),
            (self.QUAY, "", 5),
            (self.QUAY, "Preparation > Locations", 8),
            (self.QUAY, "Notes > Events", 11),
            (self.PORT, "Notes > Events", 12),
            (self.QUAY, "Notes > Events > Aftermath", 14),
        ]
        assert unresolved == ["type: [[Session]] names no file"]

    def test_repeats_at_one_location_are_listed_once(self, vault: Path) -> None:
        _, references, unresolved = trace_outbound(
            Path("content/Shoal Chart.md"), vault
        )
        assert [(r.relative, r.where, r.line) for r in references] == [
            ("content/Mara.md", "campaign_1.held_by", 0),
            (self.QUAY, "campaign_1.held_by", 0),
            (self.QUAY, "found", 0),
            (self.QUAY, "", 6),
        ]
        assert unresolved == ["line 6: [[Quay Ninety]] names no file"]

    def test_links_to_itself_are_left_out(self, vault: Path) -> None:
        assert trace_outbound(Path(self.QUAY), vault) == (self.QUAY, [], [])

    def test_reports_malformed_links(self, vault: Path) -> None:
        source, references, unresolved = trace_outbound(Path("content/Mara.md"), vault)
        assert (source, references) == ("content/Mara.md", [])
        assert len(unresolved) == 1 and unresolved[0].startswith("line 1: ")

    def test_reports_ambiguous_links(self, vault: Path) -> None:
        # A second Quay Nine leaves only the path-qualified link resolving.
        write(vault, "notes/Quay Nine.md")
        _, references, unresolved = trace_outbound(Path(self.SESSION), vault)
        assert [(r.relative, r.line) for r in references] == [
            (self.PORT, 0),
            (self.QUAY, 8),
            (self.PORT, 12),
        ]
        assert unresolved == [
            "type: [[Session]] names no file",
            "prepared_locations: [[Quay Nine]] names several files",
            "line 5: [[quay nine]] names several files",
            "line 11: [[Quay Nine]] names several files",
            "line 11: [[Quay Nine]] names several files",
            "line 14: [[Quay Nine.md]] names several files",
        ]

    def test_links_to_an_asset(self, vault: Path) -> None:
        write(vault, "content/Map.md", "## Notes\n![[Quay Nine.png]]\n")
        assert trace_outbound(Path("content/Map.md"), vault) == (
            "content/Map.md",
            [Reference("assets/Quay Nine.png", "Notes", 2)],
            [],
        )

    def test_matches_the_whole_vault_index(self, vault: Path) -> None:
        write(vault, "notes/Port Briselle.md.md")
        write(vault, "notes/deep/Mara.md")
        root = vault.resolve()
        whole = VaultIndex(root)
        for record in record_files(root, root):
            _, references, _ = trace_outbound(record)
            parsed, _ = whole.parse(record)
            assert parsed is not None
            expected = {
                whole.resolve(link.target, record)[0]
                for link in parsed.links
                if not link.error and link.target
            } - {None, record}
            assert {root / r.relative for r in references} == expected

    def test_indexes_only_files_the_links_could_name(self, vault: Path) -> None:
        for number in range(20):
            write(vault, f"content/Other {number}.md")
        with patch("armarium.trace.VaultIndex", wraps=VaultIndex) as index:
            trace_outbound(Path(self.SESSION), vault)
        files = {file.name for file in index.call_args.args[1]}
        assert files == {"Quay Nine.md", "Port Briselle.md"}

    @pytest.mark.parametrize("form", ["vault", "cwd", "absolute"])
    def test_path_forms_agree(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch, form: str
    ) -> None:
        expected = trace_outbound(Path(self.SESSION), vault)
        if form == "vault":
            monkeypatch.chdir(vault.parent)
            traced = trace_outbound(Path(self.SESSION), vault)
        elif form == "cwd":
            monkeypatch.chdir(vault / "content")
            traced = trace_outbound(Path("..") / self.SESSION)
        else:
            traced = trace_outbound(vault / self.SESSION)
        assert traced == expected and len(traced[1]) == 7

    @pytest.mark.parametrize(
        ("relative", "text", "message"),
        [
            ("assets/Quay Nine.png", None, "is not a Markdown record"),
            ("content/Broken.md", "---\nx: [\n---\n", "cannot parse content/Broken.md"),
            ("content/Open.md", "---\nx: 1\n", "cannot parse content/Open.md"),
            ("content/.Hidden.md", "", "is not part of the vault"),
            ("content/Gull.md", None, "does not exist"),
            ("content", None, "is a directory"),
        ],
    )
    def test_rejects_what_it_cannot_read(
        self, vault: Path, relative: str, text: str | None, message: str
    ) -> None:
        if text is not None:
            write(vault, relative, text)
        with pytest.raises(ValueError, match=message):
            trace_outbound(Path(relative), vault)
