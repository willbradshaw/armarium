"""Selected-record link, target-kind, placement and campaign checks."""

import re
from pathlib import Path
from typing import Any

from armarium.index import VaultIndex
from armarium.lib import Diagnostic, iter_wikilinks
from armarium.markdown import links, values, visible_lines
from armarium.parse import Note


def campaign(path: Path, root: Path) -> str | None:
    """Return the containing numeric campaign folder, if present."""
    parts = path.relative_to(root).parts
    if (
        len(parts) > 1
        and parts[0] == "campaigns"
        and re.fullmatch(r"campaign_\d+", parts[1])
    ):
        return parts[1]
    return None


def check(note: Note, index: VaultIndex) -> list[Diagnostic]:
    """Check this note's context without reporting unrelated vault problems."""
    root = index.root
    relative = note.path.relative_to(root).as_posix()
    errors: list[Diagnostic] = []
    scope = campaign(note.path, root)

    def error(rule: str, message: str, field: str = "", line: int = 0) -> None:
        errors.append(Diagnostic(relative, rule, message, field, line))

    def resolve(target: str, field: str = "", line: int = 0) -> Path | None:
        path, rule = index.resolve(target, note.path)
        if rule:
            error(
                rule,
                f"cannot uniquely resolve [[{target}]]; use a vault-relative path",
                field,
                line,
            )
        elif path is not None and path.suffix.lower() == ".md":
            _, failures = index.note(path)
            if failures:
                error(
                    "link.malformed",
                    f"referenced note {path.relative_to(root)} cannot be parsed",
                    field,
                    line,
                )
        return path

    def check_links(text: str, field: str = "", line: int = 0) -> None:
        """Report syntax errors and resolve successfully parsed targets.

        Args:
            text: One body line or a parsed frontmatter string.
            field: Frontmatter field path, if this text came from metadata.
            line: One-based source line for body text; 0 when unavailable.

        Returns:
            None: Findings are appended to this note's diagnostics.
        """
        for result in iter_wikilinks(text):
            if isinstance(result, ValueError):
                error("link.syntax", str(result), field, line)
            else:
                resolve(result, field, line)

    for field, text in values(note.frontmatter):
        check_links(text, field)
    for number, text in visible_lines(note.body):
        check_links(text, line=note.body_start_line + number - 1)

    def target_notes(value: Any, field: str) -> list[Note]:
        result: list[Note] = []
        for _, text in values(value):
            for target in links(text):
                path, _ = index.resolve(target, note.path)
                if path is not None:
                    if path.suffix.lower() != ".md":
                        error(
                            "target.kind",
                            "relationship target must be a Markdown record",
                            field,
                        )
                        continue
                    parsed, _ = index.note(path)
                    if parsed is not None:
                        result.append(parsed)
        return result

    def require(
        value: Any,
        field: str,
        kinds: set[str],
        subtypes: set[str] | None = None,
        expected_scope: str | None = None,
    ) -> None:
        for target in target_notes(value, field):
            rel = target.path.relative_to(root).as_posix()
            if (
                rel.startswith("reference/templates/")
                or target.kind not in kinds
                or (
                    subtypes is not None
                    and target.frontmatter.get("subtype") not in subtypes
                )
            ):
                error(
                    "target.kind", f"target must be {sorted(subtypes or kinds)}", field
                )
            if expected_scope and campaign(target.path, root) != expected_scope:
                error(
                    "campaign.mismatch",
                    f"target must belong to {expected_scope}",
                    field,
                )

    kind = note.kind
    if kind:
        targets = links(str(note.frontmatter["type"]))
        path, _ = index.resolve(targets[0], note.path) if targets else (None, None)
        if path and path != root / "reference/types" / f"{kind}.md":
            error(
                "target.type",
                "type must resolve to its canonical reference/types definition",
                "type",
            )
    placements = {
        "Content": "content",
        "Clue": "clues",
        "Session": "sessions",
        "Transcript": "sessions/transcripts",
        "Player": "reference/players",
    }
    if kind in placements:
        prefix = root / "campaigns" / scope if scope else root
        expected = prefix / placements[kind]
        if note.path.parent != expected or (kind != "Content" and not scope):
            error(
                "record.placement",
                f"{kind} belongs in {placements[kind]} inside its campaign"
                if kind != "Content"
                else "Content belongs in shared or campaign content/",
            )
    if kind in {"Session", "Clue"} and scope:
        letter, digits = ("S", 3) if kind == "Session" else ("C", 4)
        match = re.fullmatch(
            rf"{letter}-{scope.split('_')[1]}-(\d{{{digits}}})", note.path.stem
        )
        if not match:
            error(
                "record.identity",
                f"filename must be {letter}-{scope.split('_')[1]}-" + "0" * digits,
            )
        elif kind == "Session" and (
            type(note.frontmatter.get("session_number")) is not int
            or note.frontmatter["session_number"] != int(match[1])
        ):
            error(
                "record.identity",
                "session_number must match filename ordinal",
                "session_number",
            )
    if kind == "Session" and scope:
        campaign_targets = target_notes(note.frontmatter.get("campaign"), "campaign")
        expected = root / "campaigns" / scope / "reference/Campaign.md"
        if len(campaign_targets) != 1 or campaign_targets[0].path != expected:
            error(
                "campaign.mismatch",
                "campaign must link to the containing campaign overview",
                "campaign",
            )
    if kind == "Transcript":
        require(
            note.frontmatter.get("session"),
            "session",
            {"Session"},
            expected_scope=scope,
        )
    if kind == "Content":
        require(note.frontmatter.get("player"), "player", {"Player"})
        require(
            note.frontmatter.get("parent_location"),
            "parent_location",
            {"Content"},
            {"Location"},
        )
        require(note.frontmatter.get("members"), "members", {"Content"}, {"PC", "NPC"})
    if kind == "Player":
        require(note.frontmatter.get("plays"), "plays", {"Content"}, {"PC"})
    if kind == "Clue":
        require(note.frontmatter.get("subjects"), "subjects", {"Content"})
    if kind == "Session":
        require(
            note.frontmatter.get("players_absent"),
            "players_absent",
            {"Player"},
            expected_scope=scope,
        )
    for field, text in values(note.frontmatter):
        last = field.split(".")[-1]
        if last in {"first_session", "last_session"}:
            block = field.split(".")[0]
            expected_scope = block if re.fullmatch(r"campaign_\d+", block) else scope
            require(text, field, {"Session"}, expected_scope=expected_scope)
        if "held_by" in field.split("."):
            require(text, field, {"Content"}, {"PC", "NPC", "Faction"})
    if "status" in note.frontmatter:
        for status_note in target_notes(note.frontmatter["status"], "status"):
            if status_note.path.parent != root / "reference/statuses":
                error(
                    "target.status",
                    "status must be a canonical status definition",
                    "status",
                )
            applies = target_notes(status_note.frontmatter.get("applies_to"), "status")
            if not any(
                t.path == root / "reference/types" / f"{kind}.md" for t in applies
            ):
                error(
                    "status.applicability", f"status does not apply to {kind}", "status"
                )
    return errors
