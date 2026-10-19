"""Planning, merging, applying and rolling back updates to a vault's managed copies."""

import json
import os
import shutil
from pathlib import Path

import pytest

from armarium.changes import FileChange
from armarium.init import init_vault
from armarium.lib import RECORD, managed_files, read_settings
from armarium.update import (
    INPUTS,
    PENDING,
    Change,
    Update,
    _classify,
    _file_changes,
    _inputs,
    _lines,
    _marked,
    _pending_inputs,
    _sync_regions,
    _terminated,
    _vault_file,
    _write_pending,
    merge3,
    plan_update,
    update_vault,
)
from armarium.validate import validate

STARTER = Path(__file__).resolve().parents[1] / "vaults/starter"
AGENTS = "AGENTS.md"
SNIPPET = ".obsidian/snippets/armarium-opacity-art.css"
STYLE = "reference/styles/Gear.md"
SKILL = ".agents/skills/interview/SKILL.md"


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    return init_vault(tmp_path / "vault")


@pytest.fixture
def upstream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A copy of the starter that the running Armarium supplies."""
    source = tmp_path / "upstream"
    shutil.copytree(STARTER, source)
    for module in ("update", "validate"):
        monkeypatch.setattr(f"armarium.{module}.starter", lambda: source)
    return source


def prepend(path: Path, text: str) -> None:
    path.write_text(text + path.read_text())


def append(path: Path, text: str) -> None:
    path.write_text(path.read_text() + text)


class TestChangeWrites:
    @pytest.mark.parametrize(
        ("action", "writes"),
        [
            ("added", True),
            ("updated", True),
            ("merged", True),
            ("conflict", False),
            ("resolved", True),
            ("removed", True),
            ("released", False),
            ("omitted", False),
            ("local", False),
            ("kept", False),
        ],
    )
    def test_actions(self, action: str, writes: bool) -> None:
        assert Change("a", action).writes is writes


class TestUpdateConflicts:
    def test_lists_conflicts(self, tmp_path: Path) -> None:
        changes = [
            Change("a", "conflict"),
            Change("b", "merged"),
            Change("c", "conflict"),
        ]
        assert Update(tmp_path, None, "1.0.0", changes).conflicts == ["a", "c"]


class TestUpdateVaultFiles:
    def test_leaves_out_record_and_pending(self, tmp_path: Path) -> None:
        kept = [
            FileChange("replace", "AGENTS.md"),
            FileChange("create", ".armarium.md"),
        ]
        files = [
            *kept,
            FileChange("replace", ".armarium/vault.json"),
            FileChange("delete", ".scratch/armarium-update/AGENTS.md"),
        ]
        assert Update(tmp_path, None, "1.0.0", [], files).vault_files == kept


class TestLines:
    @pytest.mark.parametrize(
        ("content", "lines"),
        [
            (b"", []),
            (b"a\nb", ["a\n", "b"]),
            (b"a\r\nb\n", ["a\r\n", "b\n"]),
        ],
    )
    def test_split(self, content: bytes, lines: list[str]) -> None:
        assert _lines(content) == lines

    def test_round_trips_other_bytes(self) -> None:
        content = b"\xff\xfe\n"
        assert "".join(_lines(content)).encode("utf-8", "surrogateescape") == content


class TestTerminated:
    @pytest.mark.parametrize(
        ("lines", "expected"),
        [([], []), (["a\n"], ["a\n"]), (["a\n", "b"], ["a\n", "b\n"])],
    )
    def test_last_line(self, lines: list[str], expected: list[str]) -> None:
        assert _terminated(lines) == expected


class TestSyncRegions:
    @pytest.mark.parametrize(
        ("base", "vault", "new", "regions"),
        [
            ("abc", "aXc", "abcd", [(0, 1, 0, 0), (2, 3, 2, 2), (3, 3, 3, 4)]),
            ("", "x", "", [(0, 0, 1, 0)]),
            ("ab", "ab", "ab", [(0, 2, 0, 0), (2, 2, 2, 2)]),
        ],
    )
    def test_regions(
        self, base: str, vault: str, new: str, regions: list[tuple[int, ...]]
    ) -> None:
        assert _sync_regions(list(base), list(vault), list(new)) == regions


class TestMerge3:
    BASE = b"a\nb\nc\nd\ne\n"

    @pytest.mark.parametrize(
        ("vault", "new", "merged"),
        [
            (b"a\nB\nc\nd\ne\n", b"a\nb\nc\nD\ne\n", b"a\nB\nc\nD\ne\n"),
            (
                b"a\nb\nc\nd\ne\nmine\n",
                b"top\na\nb\nc\nd\ne\n",
                b"top\n" + BASE + b"mine\n",
            ),
            (b"a\nB\nc\nd\ne\n", BASE, b"a\nB\nc\nd\ne\n"),
            (BASE, b"a\nb\nc\nD\ne\n", b"a\nb\nc\nD\ne\n"),
            (b"a\nB\nc\nd\ne\n", b"a\nB\nc\nd\ne\n", b"a\nB\nc\nd\ne\n"),
            (b"a\nc\nd\ne\n", b"a\nb\nc\nd\nE\n", b"a\nc\nd\nE\n"),
        ],
        ids=["both", "insertions", "vault", "armarium", "same", "deletion"],
    )
    def test_clean(self, vault: bytes, new: bytes, merged: bytes) -> None:
        assert merge3(self.BASE, vault, new) == (merged, False)

    @pytest.mark.parametrize(
        ("base", "vault", "new", "merged"),
        [
            (
                BASE,
                b"a\nB\nc\nd\ne\n",
                b"a\nX\nc\nd\ne\n",
                b"a\n<<<<<<< vault\nB\n=======\nX\n>>>>>>> armarium\nc\nd\ne\n",
            ),
            (
                b"a\n",
                b"a\nmine",
                b"a\ntheirs",
                b"a\n<<<<<<< vault\nmine\n=======\ntheirs\n>>>>>>> armarium\n",
            ),
            (b"", b"x\n", b"y\n", b"<<<<<<< vault\nx\n=======\ny\n>>>>>>> armarium\n"),
        ],
        ids=["same-line", "unterminated", "no-base"],
    )
    def test_conflict(
        self, base: bytes, vault: bytes, new: bytes, merged: bytes
    ) -> None:
        assert merge3(base, vault, new) == (merged, True)

    def test_keeps_other_bytes(self) -> None:
        assert merge3(b"a\n", b"\xff\na\n", b"a\nb\n") == (b"\xff\na\nb\n", False)


class TestClassify:
    @pytest.mark.parametrize(
        ("base", "vault", "new", "adopting", "expected"),
        [
            (b"o", b"o", None, False, Change("p", "removed")),
            (b"o", b"v", None, False, Change("p", "released")),
            (b"o", None, None, False, None),
            (None, None, b"n", False, Change("p", "added", b"n")),
            (b"o", None, b"n", False, Change("p", "omitted")),
            (b"o", None, b"o", False, None),
            (b"o", None, b"o", True, Change("p", "omitted")),
            (b"o", b"n", b"n", False, None),
            (b"o", b"o", b"n", False, Change("p", "updated", b"n")),
            (b"o", b"v", b"o", False, None),
            (b"o", b"v", b"o", True, Change("p", "kept")),
            (b"a\n", b"v\na\n", b"a\nn\n", False, Change("p", "merged", b"v\na\nn\n")),
            (
                b"a\n",
                b"v\n",
                b"n\n",
                False,
                Change(
                    "p", "conflict", b"<<<<<<< vault\nv\n=======\nn\n>>>>>>> armarium\n"
                ),
            ),
            (
                None,
                b"v\n",
                b"n\n",
                False,
                Change(
                    "p", "conflict", b"<<<<<<< vault\nv\n=======\nn\n>>>>>>> armarium\n"
                ),
            ),
        ],
    )
    def test_actions(
        self,
        base: bytes | None,
        vault: bytes | None,
        new: bytes | None,
        adopting: bool,
        expected: Change | None,
    ) -> None:
        assert _classify("p", base, vault, new, adopting=adopting) == expected


class TestVaultFile:
    def test_reads(self, tmp_path: Path) -> None:
        (tmp_path / "a").write_bytes(b"x")
        assert _vault_file(tmp_path, "a") == b"x"
        assert _vault_file(tmp_path, "missing/b") is None

    @pytest.mark.parametrize(
        ("relative", "message"),
        [("link/a", "symlinks"), ("linked", "symlinks"), ("folder", "not a file")],
    )
    def test_refuses(self, tmp_path: Path, relative: str, message: str) -> None:
        (tmp_path / "folder").mkdir()
        (tmp_path / "folder/a").write_text("x")
        (tmp_path / "link").symlink_to(tmp_path / "folder")
        (tmp_path / "linked").symlink_to(tmp_path / "folder/a")
        with pytest.raises(ValueError, match=message):
            _vault_file(tmp_path, relative)


class TestPlanUpdate:
    def test_up_to_date(self, vault: Path) -> None:
        update = plan_update(vault, managed_files(STARTER))
        assert update.changes == []
        assert update.previous == update.version

    def test_changes(self, vault: Path) -> None:
        new = managed_files(STARTER)
        new[AGENTS] = b"Rewritten\n"
        new["docs/new.md"] = b"New\n"
        del new[SKILL]
        new[STYLE] += b"More\n"
        append(vault / "docs/armarium.md", "Vault's own\n")
        settings = json.loads((vault / RECORD / "vault.json").read_text())
        settings["local"] = [STYLE]
        (vault / RECORD / "vault.json").write_text(json.dumps(settings))
        assert plan_update(vault, new).changes == [
            Change(SKILL, "removed"),
            Change(AGENTS, "updated", b"Rewritten\n"),
            Change("docs/new.md", "added", b"New\n"),
            Change(STYLE, "local"),
        ]

    def test_adopts_vault_without_record(self, vault: Path) -> None:
        shutil.rmtree(vault / RECORD)
        (vault / SNIPPET).unlink()
        append(vault / AGENTS, "Vault's own\n")
        update = plan_update(vault, managed_files(STARTER))
        assert update.previous is None
        assert update.changes == [Change(SNIPPET, "omitted"), Change(AGENTS, "kept")]

    @pytest.mark.parametrize("allow", [False, True])
    def test_downgrade(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch, allow: bool
    ) -> None:
        monkeypatch.setattr("armarium.update.armarium_version", lambda: "0.0.1")
        if allow:
            assert plan_update(vault, managed_files(STARTER), allow_downgrade=True)
        else:
            with pytest.raises(ValueError, match="--allow-downgrade"):
                plan_update(vault, managed_files(STARTER))

    def test_refuses_symlinked_record(self, vault: Path, tmp_path: Path) -> None:
        (vault / RECORD).rename(tmp_path / "elsewhere")
        (vault / RECORD).symlink_to(tmp_path / "elsewhere")
        with pytest.raises(ValueError, match="symlink"):
            plan_update(vault, managed_files(STARTER))

    @pytest.mark.parametrize(
        ("resolution", "stale", "action"),
        [
            (None, False, "conflict"),
            (b"Resolved\n", False, "resolved"),
            (b"<<<<<<< vault\nx\n=======\ny\n>>>>>>> armarium\n", False, "conflict"),
            (b"Resolved\n", True, "conflict"),
        ],
    )
    def test_resolution(
        self, vault: Path, resolution: bytes | None, stale: bool, action: str
    ) -> None:
        new = conflicting(vault)
        _write_pending(plan_update(vault, new), new)
        if resolution is not None:
            (vault / PENDING / AGENTS).write_bytes(resolution)
        if stale:
            append(vault / AGENTS, "Later edit\n")
        [change] = plan_update(vault, new).changes
        assert change.action == action
        if action == "resolved":
            assert change.content == resolution


class TestMarked:
    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            (b"<<<<<<< vault\na\n=======\nb\n>>>>>>> armarium\n", True),
            (b"=======\n>>>>>>> armarium\n", False),
            (b"<<<<<<< vault\n", False),
            (b"Resolved\n", False),
        ],
    )
    def test_markers(self, content: bytes, expected: bool) -> None:
        assert _marked(content) is expected


class TestInputs:
    def test_digests(self) -> None:
        inputs = _inputs(b"a", None)
        assert set(inputs) == {"vault", "new"}
        assert inputs["new"] == _inputs(b"", b"")["new"]
        assert inputs != _inputs(b"b", None)


class TestPendingInputs:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            (None, {}),
            ("not json", {}),
            ("[]", {}),
            ('{"a": {"vault": "1", "new": "2"}}', {"a": {"vault": "1", "new": "2"}}),
        ],
    )
    def test_reads(
        self, tmp_path: Path, text: str | None, expected: dict[str, object]
    ) -> None:
        if text is not None:
            (tmp_path / INPUTS).parent.mkdir(parents=True)
            (tmp_path / INPUTS).write_text(text)
        assert _pending_inputs(tmp_path) == expected


def conflicting(vault: Path) -> dict[str, bytes]:
    """Change the vault's and Armarium's AGENTS.md on the same line."""
    new = managed_files(STARTER)
    new[AGENTS] = b"Armarium's\n" + new[AGENTS]
    prepend(vault / AGENTS, "Vault's\n")
    return new


def files(vault: Path) -> dict[str, bytes]:
    """Map each file in the vault outside its scratch directory to its contents."""
    return {
        p.relative_to(vault).as_posix(): p.read_bytes()
        for p in sorted(vault.rglob("*"))
        if p.is_file() and not p.relative_to(vault).as_posix().startswith(".scratch/")
    }


class TestFileChanges:
    def test_plans_files_record_and_pending(self, vault: Path) -> None:
        new = managed_files(STARTER)
        new[AGENTS] = b"Rewritten\n"
        new["docs/extra/new.md"] = b"New\n"
        del new[SKILL]
        (vault / PENDING).mkdir(parents=True)
        (vault / INPUTS).write_text("{}")
        changes = _file_changes(plan_update(vault, new), new, ["x"])
        changes.apply(prune=True)
        assert (vault / AGENTS).read_bytes() == b"Rewritten\n"
        assert (vault / "docs/extra/new.md").read_bytes() == b"New\n"
        assert not (vault / SKILL).parent.exists()
        assert not (vault / RECORD / "base" / SKILL).parent.exists()
        assert managed_files(vault / RECORD / "base") == new
        assert read_settings(vault / RECORD)["local"] == ["x"]
        assert not (vault / PENDING).exists()
        assert (vault / ".scratch/.gitkeep").exists()

    def test_writes_only_changed_base_copies(self, vault: Path) -> None:
        new = managed_files(STARTER)
        changes = _file_changes(plan_update(vault, new), new, [])
        assert set(changes.writes) == {vault / RECORD / "vault.json"}
        assert changes.deletes == set()

    def test_failure_restores(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        new = managed_files(STARTER)
        new[AGENTS] = b"Rewritten\n"
        new["docs/new.md"] = b"New\n"
        before = files(vault)
        replace = os.replace

        def fail(source: str, target: Path) -> None:
            if Path(target).name == "vault.json":
                raise KeyboardInterrupt
            replace(source, target)

        monkeypatch.setattr("armarium.changes.os.replace", fail)
        with pytest.raises(KeyboardInterrupt):
            _file_changes(plan_update(vault, new), new, []).apply(prune=True)
        monkeypatch.undo()
        assert files(vault) == before


class TestWritePending:
    def test_writes_merge_and_inputs(self, vault: Path) -> None:
        new = conflicting(vault)
        _write_pending(plan_update(vault, new), new)
        assert _marked((vault / PENDING / AGENTS).read_bytes())
        assert _pending_inputs(vault) == {
            AGENTS: _inputs((vault / AGENTS).read_bytes(), new[AGENTS])
        }

    @pytest.mark.parametrize("stale", [False, True])
    def test_keeps_work_on_current_merge(self, vault: Path, stale: bool) -> None:
        new = conflicting(vault)
        _write_pending(plan_update(vault, new), new)
        pending = vault / PENDING / AGENTS
        pending.write_text(pending.read_text() + "Work in progress\n")
        if stale:
            append(vault / AGENTS, "Later edit\n")
        _write_pending(plan_update(vault, new), new)
        assert ("Work in progress" in pending.read_text()) is not stale
        assert _pending_inputs(vault)[AGENTS] == _inputs(
            (vault / AGENTS).read_bytes(), new[AGENTS]
        )


class TestUpdateVault:
    def test_brings_vault_up_to_date(self, vault: Path, upstream: Path) -> None:
        prepend(upstream / AGENTS, "Armarium's new rule\n")
        (upstream / "docs/new.md").write_text("New\n")
        (upstream / SKILL).unlink()
        append(upstream / SNIPPET, "/* changed */\n")
        append(upstream / STYLE, "More\n")
        append(vault / AGENTS, "Vault's own rule\n")
        (vault / SNIPPET).unlink()
        settings = json.loads((vault / RECORD / "vault.json").read_text())
        settings["local"] = [STYLE]
        (vault / RECORD / "vault.json").write_text(json.dumps(settings))
        style = (vault / STYLE).read_bytes()

        dry = update_vault(vault, dry_run=True)
        assert not (vault / "docs/new.md").exists()
        update = update_vault(vault)
        assert update.changes == dry.changes
        assert update.files == dry.files
        assert update.vault_files == [
            FileChange("delete", SKILL),
            FileChange("replace", AGENTS),
            FileChange("create", "docs/new.md"),
        ]
        assert [(c.path, c.action) for c in update.changes] == [
            (SKILL, "removed"),
            (SNIPPET, "omitted"),
            (AGENTS, "merged"),
            ("docs/new.md", "added"),
            (STYLE, "local"),
        ]
        agents = (vault / AGENTS).read_text()
        assert agents.startswith("Armarium's new rule\n")
        assert agents.endswith("Vault's own rule\n")
        assert not (vault / SNIPPET).exists()
        assert (vault / STYLE).read_bytes() == style
        assert managed_files(vault / RECORD / "base") == managed_files(upstream)
        assert read_settings(vault / RECORD)["local"] == [STYLE]
        assert not validate(vault).failed
        assert update_vault(vault).changes == []

    def test_conflict_changes_nothing_until_resolved(
        self, vault: Path, upstream: Path
    ) -> None:
        prepend(upstream / AGENTS, "Armarium's line\n")
        (upstream / "docs/new.md").write_text("New\n")
        prepend(vault / AGENTS, "Vault's line\n")
        before = files(vault)

        assert update_vault(vault, dry_run=True).conflicts == [AGENTS]
        assert not (vault / PENDING).exists()
        update = update_vault(vault)
        assert update.conflicts == [AGENTS]
        assert update.vault_files == [FileChange("create", "docs/new.md")]
        assert files(vault) == before
        pending = vault / PENDING / AGENTS
        assert pending.read_text().startswith(
            "<<<<<<< vault\nVault's line\n=======\nArmarium's line\n>>>>>>> armarium\n"
        )

        pending.write_text(
            "Both lines\n" + pending.read_text().split("armarium\n", 1)[1]
        )
        update = update_vault(vault)
        assert [(c.path, c.action) for c in update.changes] == [
            (AGENTS, "resolved"),
            ("docs/new.md", "added"),
        ]
        assert (vault / AGENTS).read_text().startswith("Both lines\n# Agent")
        assert (vault / "docs/new.md").exists()
        assert not (vault / PENDING).exists()
        assert managed_files(vault / RECORD / "base") == managed_files(upstream)
        assert not validate(vault).failed
        assert update_vault(vault).changes == []

    @pytest.mark.parametrize("recorded", [False, True])
    def test_dry_run_changes_nothing(
        self, vault: Path, upstream: Path, recorded: bool
    ) -> None:
        if not recorded:
            shutil.rmtree(vault / RECORD)
        prepend(upstream / AGENTS, "New\n")
        before = files(vault)
        update = update_vault(vault, dry_run=True)
        assert (update.previous is None) is not recorded
        assert [(c.path, c.action) for c in update.changes] == [
            (AGENTS, "updated" if recorded else "kept")
        ]
        assert files(vault) == before

    def test_adopts_vault_without_record(self, vault: Path, upstream: Path) -> None:
        shutil.rmtree(vault / RECORD)
        update_vault(vault)
        assert managed_files(vault / RECORD / "base") == managed_files(upstream)
        assert read_settings(vault / RECORD)["local"] == []
