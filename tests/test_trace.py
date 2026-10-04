"""Tracing lists resolved links to one record with their locations."""

from pathlib import Path
from unittest.mock import patch

import pytest

from armarium.index import VaultIndex
from armarium.parse import Record
from armarium.trace import Reference, _mentions, _spelling, _target, trace_record

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


class TestTarget:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("Quay Nine", "content/Quay Nine.md"),
            ("  quay nine.md ", "content/Quay Nine.md"),
            ("content/Quay Nine", "content/Quay Nine.md"),
            ("/content/Quay Nine", "content/Quay Nine.md"),
            ("the ninth", "content/Quay Nine.md"),
            ("Quay Nine.png", "assets/Quay Nine.png"),
            ("S-1-001", "campaigns/campaign_1/sessions/S-1-001.md"),
            ("Quay   Nine", "content/Quay Nine.md"),
            ("the  NINTH", "content/Quay Nine.md"),
        ],
    )
    def test_resolves_name_path_or_alias(
        self, vault: Path, name: str, expected: str
    ) -> None:
        index = VaultIndex(vault)
        assert _target(index, name) == index.root / expected

    @pytest.mark.parametrize(
        ("name", "message"),
        [
            ("", "name must not be blank"),
            ("   ", "name must not be blank"),
            ("Gull", "no record is named Gull$"),
            ("Quay Nin", "no record is named Quay Nin$"),
            ("Quay", "no record is named Quay$"),
            (
                "Mara",
                "several files are named Mara: content/Mara.md, notes/Mara.md; "
                "use a vault-relative path",
            ),
            (
                "Old Quay",
                "several records have the name or alias Old Quay: content/Mara.md, "
                "notes/Mara.md$",
            ),
            (
                "Old  Harbour",
                "several records have the name or alias Old  Harbour: "
                "content/Old Harbour.md, notes/Mara.md$",
            ),
        ],
    )
    def test_rejects_missing_or_ambiguous(
        self, vault: Path, name: str, message: str
    ) -> None:
        write(vault, "notes/Mara.md", "---\naliases: [Old Quay, Old Harbour]\n---\n")
        write(vault, "content/Mara.md", "---\naliases: [Old Quay]\n---\n")
        write(vault, "content/Old Harbour.md")
        with pytest.raises(ValueError, match=message):
            _target(VaultIndex(vault), name)

    def test_name_precedes_alias(self, vault: Path) -> None:
        write(vault, "content/The Ninth.md")
        index = VaultIndex(vault)
        assert _target(index, "The Ninth") == index.root / "content/The Ninth.md"


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
            ("quay nine", "[[old quay nine]]", False),
            ("quay nine", "[[quay ninety]]", False),
            ("quay nine", "[[quay nine/pier]]", False),
            ("quay nine", "[[pier|quay nine]]", False),
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


class TestMentions:
    @pytest.mark.parametrize(
        ("text", "needle", "expected"),
        [
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


class TestTraceRecord:
    def test_lists_links_with_locations(self, vault: Path) -> None:
        target, references = trace_record("Quay Nine", vault)
        assert target == vault.resolve() / "content/Quay Nine.md"
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

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("the ninth", "content/Quay Nine.md"),
            ("content/Port Briselle.md", "content/Port Briselle.md"),
        ],
    )
    def test_resolves_the_name(self, vault: Path, name: str, expected: str) -> None:
        target, references = trace_record(name, vault)
        assert target == vault.resolve() / expected
        assert references

    def test_no_links(self, vault: Path) -> None:
        target, references = trace_record("Shoal Chart", vault)
        assert target == vault.resolve() / "content/Shoal Chart.md"
        assert references == []

    def test_traces_an_asset(self, vault: Path) -> None:
        write(vault, "content/Map.md", "## Notes\n![[Quay Nine.png]]\n")
        target, references = trace_record("Quay Nine.png", vault)
        assert target == vault.resolve() / "assets/Quay Nine.png"
        assert references == [Reference("content/Map.md", "Notes", 2)]

    def test_follows_resolution_not_spelling(self, vault: Path) -> None:
        # A second Quay Nine makes the bare name ambiguous, so only links
        # spelling the path still resolve to the first.
        write(vault, "notes/Quay Nine.md", "[[content/Quay Nine]]\n")
        _, references = trace_record("content/Quay Nine", vault)
        assert [(r.relative, r.line) for r in references] == [
            ("campaigns/campaign_1/sessions/S-1-001.md", 8),
            ("notes/Quay Nine.md", 1),
        ]

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
        assert trace_record("Shoal Chart", vault)[1] == []

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
            assert trace_record("Shoal Chart", vault)[1] == []

    def test_parses_only_records_naming_the_target(self, vault: Path) -> None:
        with patch.object(Record, "parse", wraps=Record.parse) as parse:
            trace_record("Port Briselle", vault)
        assert [call.args[0].name for call in parse.call_args_list] == ["S-1-001.md"]

    def test_discovers_the_vault(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(vault / "content")
        assert len(trace_record("Port Briselle")[1]) == 2

    @pytest.mark.parametrize("name", ["", "Gull"])
    def test_rejects_unknown_name(self, vault: Path, name: str) -> None:
        with pytest.raises(ValueError):
            trace_record(name, vault)

    def test_rejects_missing_vault(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            trace_record("Quay Nine", tmp_path)
