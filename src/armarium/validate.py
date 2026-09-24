"""Read-only entry points coordinating parsing and record validation."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import overload

from jsonschema.exceptions import SchemaError

from armarium.index import VaultIndex
from armarium.lib import (
    CAMPAIGN_NAME,
    WIKILINK,
    Diagnostic,
    Findings,
    Result,
    VaultNotFoundError,
    check_vault,
    find_campaign,
    find_children,
    find_files,
    find_vault,
    parse_wikilink,
)
from armarium.parse import Note
from armarium.schemas import Schema, select_schema


@dataclass(frozen=True)
class Target:
    """Requirements on the record that a type-bound field links to.

    Attributes:
        record_type: Required declared type of the target.
        subtypes: Permitted Content subtypes, or empty for any subtype.
        campaign: Campaign directory name (campaign_N) the target must belong
            to, or None for no fixed campaign.
        local: Whether the target must belong to the campaign containing the
            linking record; no restriction applies when that record is outside
            every campaign. Shared Content outside every campaign satisfies
            either campaign requirement.
    """

    record_type: str
    subtypes: frozenset[str] = frozenset()
    campaign: str | None = None
    local: bool = False


# Infrastructure every vault must contain. Extra folders and files are allowed.
VAULT_DIRECTORIES = (
    "assets",
    "campaigns",
    "content",
    "reference/schemas",
    "reference/statuses",
    "reference/templates",
    "reference/types",
    "reference/views",
)
VAULT_TYPES = (
    "Clue",
    "Content",
    "Player",
    "Reference",
    "Session",
    "Status",
    "Transcript",
    "Type",
)
VAULT_STATUSES = ("Abandoned", "Dormant", "Hinted", "Pending", "Revealed", "Superseded")
VAULT_TEMPLATES = ("Clue", "Content", "Player", "Session", "Transcript")
CAMPAIGN_DIRECTORIES = (
    "clues",
    "content",
    "reference/indexes",
    "reference/players",
    "sessions",
    "sessions/transcripts",
)
CAMPAIGN_FILES = ("reference/Campaign.md", "reference/indexes/Clues.md")

# An Appearances entry: a wikilink, a colon and a description.
ENTRY = re.compile(rf"({WIKILINK.pattern}): \S.*")

# Top-level frontmatter fields whose links must target a record of a given type:
# on every record, then by the record's (type, subtype), where entries under
# (type, None) apply to every record of that type.
LINK_TARGETS = {"type": Target("Type"), "status": Target("Status")}
RECORD_LINK_TARGETS: dict[tuple[str, str | None], dict[str, Target]] = {
    ("Status", None): {"applies_to": Target("Type")},
    ("Content", "PC"): {"player": Target("Player", local=True)},
    ("Content", "Location"): {
        "parent_location": Target("Content", frozenset({"Location"}), local=True)
    },
    ("Content", "Faction"): {
        "members": Target("Content", frozenset({"PC", "NPC"}), local=True)
    },
    ("Player", None): {"plays": Target("Content", frozenset({"PC"}), local=True)},
    ("Transcript", None): {"session": Target("Session", local=True)},
    ("Clue", None): {
        "text": Target("Content", local=True),
        "subjects": Target("Content", local=True),
        "first_session": Target("Session", local=True),
        "last_session": Target("Session", local=True),
    },
    ("Session", None): {
        "campaign": Target("Reference", local=True),
        "players_absent": Target("Player", local=True),
        "prepared_clues": Target("Clue", local=True),
        "prepared_locations": Target("Content", frozenset({"Location"}), local=True),
        "prepared_npcs": Target("Content", frozenset({"NPC"}), local=True),
    },
}


def validate(path: Path, vault: Path | None = None) -> Result:
    """Validate a Markdown file or directory using the appropriate checks.

    Args:
        path: File or directory to validate.
        vault: Optional explicit vault boundary, passed to the selected validator.

    Returns:
        Result: Findings and counts from file or recursive directory validation.

    Raises:
        ValueError: The target or explicit vault is invalid, or a file has no
            inferable vault context.
        OSError: Directory traversal fails.
    """
    if path.is_dir():
        return validate_directory(path, vault)
    return validate_markdown(path, vault)


def validate_markdown(
    path: Path, vault: Path | None = None, *, index: VaultIndex | None = None
) -> Result:
    """Validate one Markdown record against its schema and vault context.

    Args:
        path: Existing Markdown file, absolute or relative to the working
            directory. Direct symlink targets are excluded.
        vault: Optional explicit vault boundary; otherwise infer the nearest
            enclosing vault from its structural markers.
        index: Optional index for this vault, shared during directory validation.

    Returns:
        Result: Diagnostics and checked/skipped/unsupported counts for this
            file. Parse failures and missing or malformed types are errors.
            After parsing, only files under reference/templates are skipped,
            with an explicit informational diagnostic. Type/status definitions
            are records too and require declared types and schema validation.
            Typed files receive their vault-local schema checks;
            absent schemas produce errors. Invalid schemas
            fail validation without being counted as missing coverage.
            Links are checked against the whole vault; only linked Markdown
            dependencies are parsed. No source files are modified.

    Raises:
        ValueError: The target is not a regular Markdown file, is a symlink,
            lies outside the selected vault, has no inferable vault, or the
            supplied index belongs to another vault.
    """
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".md":
        raise ValueError("target must be a regular Markdown file, not a symlink")
    root = check_vault(path, vault) if vault is not None else find_vault(path)
    path = path.resolve()
    relative = path.relative_to(root).as_posix()
    if index is not None and index.root != root:
        raise ValueError("index must belong to the selected vault")
    note, diagnostics = (
        index.parse(path) if index is not None else Note.parse(path, root)
    )
    if note is None:
        return Result(diagnostics=diagnostics, checked=1)
    if path.is_relative_to(root / "reference/templates"):
        return Result(
            diagnostics=[
                Diagnostic(
                    relative,
                    "record.template",
                    "template parsed; completed-record validation skipped",
                    severity="info",
                )
            ],
            skipped=1,
        )
    if note.frontmatter.type is None:
        return Result(
            diagnostics=[
                Diagnostic(
                    relative,
                    "record.type",
                    "type is required and must be a canonical wikilink",
                    field="type",
                )
            ],
            checked=1,
        )
    schema, diagnostics = select_schema(note, root)
    if schema is not None:
        diagnostics.extend(schema.validate(note))
    if index is None:
        index = VaultIndex(root)
        index.notes[path] = (note, [])
    diagnostics.extend(validate_wikilinks(note, index))
    diagnostics.extend(validate_placement(note, index))
    diagnostics.extend(validate_filename(note, index))
    diagnostics.extend(validate_campaigns(note, index))
    diagnostics.extend(validate_identity_links(note, index))
    diagnostics.extend(validate_appearances(note, index))
    diagnostics.extend(validate_clue(note, index))
    return Result(
        diagnostics=sorted(diagnostics),
        checked=1,
        unsupported=int(any(d.rule == "schema.unsupported" for d in diagnostics)),
    )


def validate_directory(path: Path, vault: Path | None = None) -> Result:
    """Validate visible Markdown descendants, discovering vaults as needed.

    Args:
        path: Directory to scan recursively. Hidden entries, caches,
            node_modules and symlinks are excluded by find_files.
        vault: Optional explicit vault containing the entire selected directory.
            Otherwise try the selected directory, then descend until a vault
            is found. A selected vault applies to its entire subtree.

    Returns:
        Result: Aggregated findings and counts, with diagnostic paths relative
            to the scanned directory. Markdown outside discovered vaults is
            ignored. Empty directories succeed with zero counts. Templates
            receive the same parse-only handling as single-file validation.
            Every vault root that is scanned, whether selected or discovered,
            also receives the validate_vault infrastructure checks.

    Raises:
        ValueError: The target is not a real directory, or the explicit vault
            does not contain it.
        OSError: Directory traversal fails. The scan does not claim completeness
            when part of the directory cannot be read.
    """
    if path.is_symlink() or not path.is_dir():
        raise ValueError("directory validation requires a real directory")
    try:
        context = check_vault(path, vault) if vault is not None else find_vault(path)
    except VaultNotFoundError:
        results = [
            validate_directory(child).add_context(child.name)
            for child in find_children(path)
            if child.is_dir()
        ]
        return sum(results, Result())
    files = [file for file in find_files(path) if file.suffix.lower() == ".md"]
    index = VaultIndex(context)
    result = sum(
        (validate_markdown(file, context, index=index) for file in files), Result()
    )
    # A vault root, whether named directly or found by recursion, must also
    # carry the shared infrastructure; a directory inside a vault need not.
    if path.resolve() == context:
        result += Result(diagnostics=validate_vault(context))
    return result.add_context(context, relative_to=path.resolve())


def validate_vault(root: Path) -> list[Diagnostic]:
    """Check a vault root's shared infrastructure and campaign layout.

    Args:
        root: Resolved vault directory.

    Returns:
        list[Diagnostic]: Findings attributed to the vault itself (an empty
            path, which directory validation rebases onto the vault), each
            naming the affected entry. Extra folders and files are allowed;
            record contents are validated separately.
    """
    diagnostics: list[Diagnostic] = []

    def report(rule: str, message: str) -> None:
        diagnostics.append(Diagnostic("", rule, message))

    def require(relative: str, directory: bool) -> None:
        path = root / relative
        present = path.is_dir() if directory else path.is_file()
        if path.is_symlink() or not present:
            kind = "directory" if directory else "file"
            report("vault.required", f"required {kind} {relative} is missing")

    for relative in VAULT_DIRECTORIES:
        require(relative, True)
    for name in VAULT_TYPES:
        require(f"reference/types/{name}.md", False)
    for name in VAULT_STATUSES:
        require(f"reference/statuses/{name}.md", False)
    for name in VAULT_TEMPLATES:
        require(f"reference/templates/{name}.md", False)

    campaigns = root / "campaigns"
    if not campaigns.is_dir() or campaigns.is_symlink():
        report("vault.campaign", "cannot check campaigns: campaigns/ is missing")
    else:
        found = []
        for child in find_children(campaigns):
            if child.is_dir() and CAMPAIGN_NAME.fullmatch(child.name):
                found.append(child.name)
            else:
                report(
                    "vault.campaign",
                    f"campaigns/{child.name} is not a campaign_N directory",
                )
        if not found:
            report("vault.campaign", "campaigns/ has no campaign_N directory")
        for name in found:
            for relative in CAMPAIGN_DIRECTORIES:
                require(f"campaigns/{name}/{relative}", True)
            for relative in CAMPAIGN_FILES:
                require(f"campaigns/{name}/{relative}", False)

    # Schemas and Type definitions correspond by name: Clue.md <-> clue.schema.json.
    types = root / "reference/types"
    schemas = root / "reference/schemas"
    for directory in (types, schemas):
        if not directory.is_dir() or directory.is_symlink():
            relative = directory.relative_to(root).as_posix()
            report(
                "schema.missing", f"cannot check schema coverage: {relative} is missing"
            )
            return diagnostics
    definitions = {
        file.stem for file in find_files(types) if file.suffix.lower() == ".md"
    }
    schema_names: set[str] = set()
    for file in find_files(schemas):
        relative = file.relative_to(root).as_posix()
        if not file.name.endswith(".schema.json"):
            if file.suffix.lower() == ".json":
                report("schema.unused", f"{relative} is not named <type>.schema.json")
            continue
        try:
            Schema.load(file, root)
        except (OSError, ValueError, SchemaError, RecursionError) as exc:
            report("schema.invalid", f"{relative}: {exc}")
        name = file.name.removesuffix(".schema.json")
        schema_names.add(name)
        if name not in {definition.lower() for definition in definitions}:
            report("schema.unused", f"{relative} matches no Type definition")
    for definition in sorted(definitions):
        if definition.lower() not in schema_names:
            report("schema.missing", f"no vault-local schema for {definition}")
    return diagnostics


def validate_appearances(note: Note, index: VaultIndex) -> list[Diagnostic]:
    """Reconcile a Content record's Appearances list with its campaign blocks.

    Args:
        note: Selected record; only Content records carry Appearances.
        index: Vault index used to resolve the linked Sessions.

    Returns:
        list[Diagnostic]: Problems with the Appearances section or its entries,
            with the order of campaigns and of each campaign's appearances, and
            with the campaign_N blocks' first_session and last_session.
    """
    if note.frontmatter.type != "Content":
        return []
    findings = Findings(note.path.relative_to(index.root).as_posix())
    # 1. Read the recorded appearances
    appearances = _read_appearances(note, index, findings)
    # 2. Validate the sequence of campaigns
    order = [int(campaign.removeprefix("campaign_")) for campaign, _, _ in appearances]
    findings.diagnose(order != sorted(order), "history.order", "campaigns out of order")
    # 3. Check each campaign with appearances or a block
    campaigns = {campaign for campaign, _, _ in appearances}
    for campaign in sorted(campaigns | note.frontmatter.campaigns.keys()):
        history = [(ordinal, path) for c, ordinal, path in appearances if c == campaign]
        _check_campaign_history(note, index, campaign, history, findings)
    return findings.diagnostics


def _read_appearances(
    note: Note, index: VaultIndex, findings: Findings
) -> list[tuple[str, int, Path]]:
    """Collect the appearances recorded under a Content record's Appearances.

    Args:
        note: Content record to read.
        index: Vault index used to resolve and parse linked Sessions.
        findings: Collector for the problems found.

    Returns:
        list[tuple[str, int, Path]]: Campaign, session number and path of each
            Session linked under Appearances, in list order. A malformed
            section ends the read; a malformed or unusable entry is omitted.
    """
    # 1. Find and validate the Appearances section.
    history: list[tuple[str, int, Path]] = []
    sections = [
        s for s in note.body.walk() if s.level == 2 and s.title == "Appearances"
    ]
    if findings.diagnose(not sections, "history.format", "no Appearances heading"):
        return history
    section = sections[0]
    problems = (
        (len(sections) > 1, "repeated Appearances heading"),
        (bool(section.children), "subheadings under Appearances"),
        (
            len(section.blocks) != 1 or section.blocks[0].kind != "list",
            "Appearances must be a single list",
        ),
    )
    for check, message in problems:
        if findings.diagnose(check, "history.format", message, line=section.line):
            return history
    # 2. An N/A placeholder stands alone.
    appearances = section.blocks[0].children
    placeholders = [item.line for item in appearances if item.text == "N/A"]
    if placeholders:
        findings.diagnose(
            len(appearances) > 1,
            "history.format",
            "N/A listed with appearances",
            line=placeholders[0],
        )
        return history
    # 3. Collect the linked Sessions.
    linked: list[tuple[int, Note]] = []
    for appearance in appearances:
        match = ENTRY.fullmatch(appearance.text)
        if match is None:
            findings.add(
                "history.format", "invalid appearance format", line=appearance.line
            )
            continue
        try:
            target = parse_wikilink(match[1], canonical=True)
        except ValueError as exc:
            findings.add("history.format", f"entry link: {exc}", line=appearance.line)
            continue
        session = linked_note(target, note, index, Target("Session"))
        if isinstance(session, tuple):
            findings.add(
                "history.entry",
                f"cannot check appearance: {session[1]}",
                line=appearance.line,
            )
            continue
        linked.append((appearance.line, session))
    # 4. Validate the linked Sessions.
    scope = find_campaign(note.path, index.root)
    for line, session in linked:
        stem = session.path.stem
        ordinal = session.frontmatter.get("session_number")
        campaign = find_campaign(session.path, index.root)
        if isinstance(ordinal, bool) or not isinstance(ordinal, int):
            findings.add(
                "history.entry",
                f"invalid session number in {stem}: {ordinal!r}",
                line=line,
            )
            continue
        if campaign is None:
            findings.add("history.entry", f"no campaign for {stem}", line=line)
            continue
        if findings.diagnose(
            scope is not None and campaign != scope,
            "history.campaign",
            f"appearance in {campaign} recorded in a {scope} record",
            line=line,
        ):
            continue
        history.append((campaign, ordinal, session.path))
    return history


def _check_campaign_history(
    note: Note,
    index: VaultIndex,
    campaign: str,
    history: list[tuple[int, Path]],
    findings: Findings,
) -> None:
    """Check one campaign's recorded appearances against its campaign_N block.

    Args:
        note: Content record being checked.
        index: Vault index used to resolve the block's Session links.
        campaign: Campaign directory name, campaign_N.
        history: That campaign's appearances as (ordinal, Session path), in
            list order; empty when none are recorded.
        findings: Collector for the problems found.
    """
    # 1. Validate the sequence of appearances
    ordinals = [ordinal for ordinal, _ in history]
    sessions = [session for _, session in history]
    findings.diagnose(
        ordinals != sorted(ordinals),
        "history.order",
        f"{campaign} appearances out of order",
    )
    findings.diagnose(
        len(sessions) != len(set(sessions)),
        "history.duplicate",
        f"{campaign} repeats a Session",
    )
    # 2. Find the campaign block
    block = note.frontmatter.campaigns.get(campaign)
    if block is None:
        findings.add(
            "history.block", f"no {campaign} block for its appearances", campaign
        )
        return
    # 3. Compare the block's range with the earliest and latest appearances
    ordered = sorted(history)
    bounds = (
        ("first_session", ordered[0][1] if ordered else None),
        ("last_session", ordered[-1][1] if ordered else None),
    )
    for field, expected in bounds:
        location = f"{campaign}.{field}"
        if expected is None:
            findings.diagnose(
                block.get(field) is not None,
                "history.range",
                f"{location} set without appearances",
                location,
            )
            continue
        resolved, error = index.resolve_field(note, location)
        if error is not None:
            findings.add("history.range", f"cannot check {location}: {error}", location)
            continue
        findings.diagnose(
            resolved != expected,
            "history.range",
            f"{location} must be [[{expected.stem}]]",
            location,
        )


def validate_clue(note: Note, index: VaultIndex) -> list[Diagnostic]:
    """Check a Clue's subjects against its text and the order of its Sessions.

    Args:
        note: Selected record; only Clues carry text, subjects and Session range.
        index: Vault index used to resolve the links.

    Returns:
        list[Diagnostic]: subjects that are not exactly the records linked in
            text, or a link that cannot be resolved for that comparison
            (clue.subjects); a last_session without first_session
            (history.range); a last_session before first_session, or a Session
            that cannot be ordered (history.order).
    """
    if note.frontmatter.type != "Clue":
        return []
    findings = Findings(note.path.relative_to(index.root).as_posix())
    # 1. Resolve every link in text and subjects
    linked: dict[str, set[Path]] = {"text": set(), "subjects": set()}
    comparable = True
    for link in note.links:
        if link.field not in linked:
            continue
        result = None if link.error else linked_note(link.target, note, index)
        if not isinstance(result, Note):
            reason = link.error or (result[1] if result else "not a note")
            findings.add(
                "clue.subjects", f"cannot check subjects: {reason}", link.location
            )
            comparable = False
            continue
        linked[link.field].add(result.path)
    # 2. Compare the two sets
    if comparable and linked["text"] != linked["subjects"]:
        missing = sorted(p.stem for p in linked["text"] - linked["subjects"])
        extra = sorted(p.stem for p in linked["subjects"] - linked["text"])
        detail = "; ".join(
            f"{label} {', '.join(f'[[{stem}]]' for stem in stems)}"
            for label, stems in (("missing", missing), ("extra", extra))
            if stems
        )
        findings.add(
            "clue.subjects", f"subjects do not match text: {detail}", "subjects"
        )
    # 3. Read the Session ordinals
    ordinals: dict[str, int | None] = {}
    for field in ("first_session", "last_session"):
        if note.frontmatter.get(field) is None:
            ordinals[field] = None
            continue
        resolved, error = index.resolve_field(note, field)
        session = (
            index.parse(resolved)[0] if resolved and resolved.suffix == ".md" else None
        )
        ordinal = session.frontmatter.get("session_number") if session else None
        if error or isinstance(ordinal, bool) or not isinstance(ordinal, int):
            reason = error or f"{field} does not link a numbered Session"
            findings.add("history.order", f"cannot order {field}: {reason}", field)
            continue
        ordinals[field] = ordinal
    # 4. Validate the range
    first, last = ordinals.get("first_session"), ordinals.get("last_session")
    if "first_session" in ordinals and "last_session" in ordinals:
        findings.diagnose(
            last is not None and first is None,
            "history.range",
            "last_session requires first_session",
            "last_session",
        )
        findings.diagnose(
            last is not None and first is not None and last < first,
            "history.order",
            "last_session precedes first_session",
            "last_session",
        )
    return findings.diagnostics


def validate_wikilinks(note: Note, index: VaultIndex) -> list[Diagnostic]:
    """Check every link the note contains against the vault.

    Links within a type-bound field must target a correctly placed record
    meeting that field's Target requirements; see _link_targets.

    Args:
        note: Selected note inside the indexed vault.
        index: Whole-vault file index and lazy note cache for this run.

    Returns:
        list[Diagnostic]: Findings attributed to the selected note, with metadata
            locations or body source lines. Unrelated notes are not parsed.
            Heading and block existence, query execution and ordinary URLs are
            excluded.
    """
    path = note.path.relative_to(index.root).as_posix()
    targets = _link_targets(note, index)
    diagnostics: list[Diagnostic] = []
    for link in note.links:
        if link.error is not None:
            problem: tuple[str, str] | None = ("link.syntax", link.error)
        else:
            problem = validate_wikilink(
                link.target, note, index, targets.get(link.field)
            )
        if problem is not None:
            diagnostics.append(Diagnostic(path, *problem, link.location, link.line))
    return diagnostics


def _link_targets(note: Note, index: VaultIndex) -> dict[str, Target]:
    """Collect the Target requirements for a note's type-bound fields.

    Args:
        note: Selected record whose type, subtype, status and campaign blocks
            select the requirements.
        index: Whole-vault index used to resolve the record's status.

    Returns:
        dict[str, Target]: Requirements keyed by frontmatter location: the
            universal fields, those for the record's (type, subtype),
            superseded_by for a Superseded Clue, and campaign_N block fields
            bound to campaign_N. Custom fields are not interpreted by name.
    """
    kind = note.frontmatter.type or ""
    subtype = note.frontmatter.get("subtype")
    targets = LINK_TARGETS | RECORD_LINK_TARGETS.get((kind, None), {})
    if isinstance(subtype, str):
        targets |= RECORD_LINK_TARGETS.get((kind, subtype), {})
    if kind == "Clue":
        # Replacement metadata outside Superseded status remains deferred to #36.
        status, _ = index.resolve_field(note, "status")
        if status is not None and status.stem == "Superseded":
            targets["superseded_by"] = Target("Clue", local=True)
    if kind == "Content":
        for field in note.frontmatter.campaigns:
            # Block fields are bound to that block's campaign, not the record's.
            targets[f"{field}.first_session"] = Target("Session", campaign=field)
            targets[f"{field}.last_session"] = Target("Session", campaign=field)
            if subtype == "Object":
                targets[f"{field}.held_by"] = Target(
                    "Content", frozenset({"PC", "NPC", "Faction"}), field
                )
    return targets


def validate_wikilink(
    target: str, note: Note, index: VaultIndex, expected: Target | None = None
) -> tuple[str, str] | None:
    """Check that one wikilink target resolves to a usable vault file.

    Args:
        target: Parsed wikilink target, without alias, heading or block suffix.
        note: Note containing the link; its path breaks resolution ties and its
            declared type takes part in target-specific checks.
        index: Whole-vault file index and lazy note cache for this run.
        expected: Requirements on the target record, or None for any file.

    Returns:
        tuple[str, str] | None: The problem found by linked_note, or None when
            the target is usable.
    """
    result = linked_note(target, note, index, expected)
    return result if isinstance(result, tuple) else None


@overload
def linked_note(
    target: str, note: Note, index: VaultIndex, expected: Target
) -> Note | tuple[str, str]: ...


@overload
def linked_note(
    target: str, note: Note, index: VaultIndex, expected: None = None
) -> Note | tuple[str, str] | None: ...


def linked_note(
    target: str, note: Note, index: VaultIndex, expected: Target | None = None
) -> Note | tuple[str, str] | None:
    """Resolve one wikilink target and check it, returning the note it names.

    Args:
        target: Parsed wikilink target, without alias, heading or block suffix.
        note: Note containing the link; its path breaks resolution ties and its
            declared type takes part in target-specific checks.
        index: Whole-vault file index and lazy note cache for this run.
        expected: Requirements on the target record, or None for any file.

    Returns:
        Note | tuple[str, str] | None: The linked note when it parses and meets
            expected; None when no record type is expected and the target is a
            usable non-note file or self-anchor; otherwise the rule and message
            for a missing, ambiguous or unparseable target, one that is not a
            correctly placed record of the expected type and subtype, one
            outside the expected campaign, or one failing its type's own check.
    """
    resolved, rule = index.resolve(target, note.path)
    if rule:
        return rule, f"cannot uniquely resolve [[{target}]]; use a vault-relative path"
    linked = None
    if resolved is not None and resolved.suffix.lower() == ".md":
        linked, failures = index.parse(resolved)
        if failures:
            relative = resolved.relative_to(index.root)
            return "link.malformed", f"referenced note {relative} cannot be parsed"
    if expected is None:
        return linked
    kind = expected.record_type
    if (
        linked is None
        or linked.frontmatter.type != kind
        or validate_placement(linked, index)
    ):
        return "link.type", f"[[{target}]] must link to a placed {kind} record"
    subtype = linked.frontmatter.get("subtype")
    if expected.subtypes and (
        not isinstance(subtype, str) or subtype not in expected.subtypes
    ):
        allowed = ", ".join(sorted(expected.subtypes))
        return "link.type", f"[[{target}]] must link to a {kind} with subtype {allowed}"
    required = expected.campaign
    if expected.local:
        required = find_campaign(note.path, index.root)
    scope = find_campaign(linked.path, index.root)
    shared = kind == "Content" and scope is None
    if required is not None and scope != required and not shared:
        allowed = required + (" or shared content" if kind == "Content" else "")
        return "campaign.mismatch", f"[[{target}]] must belong to {allowed}"
    check = _TARGET_CHECKS.get(kind)
    problem = check(linked, note, index) if check else None
    return problem if problem is not None else linked


def _validate_wikilink_status(
    status: Note, note: Note, index: VaultIndex
) -> tuple[str, str] | None:
    """Check that a linked Status applies to the linking record's type.

    Args:
        status: Correctly placed Status definition the link resolved to.
        note: Record containing the link.
        index: Whole-vault index used to resolve applies_to and the record type.

    Returns:
        tuple[str, str] | None: An applicability error when the Status has no
            usable applies_to, the record has no usable type link, or the two
            resolve to different files.
    """
    applies_to, error = index.resolve_field(status, "applies_to")
    if error is not None:
        relative = status.path.relative_to(index.root)
        return "status.applicability", f"status {relative}: {error}"
    record_type, error = index.resolve_field(note, "type")
    if error is not None:
        return "status.applicability", f"cannot check applicability: {error}"
    if applies_to == record_type:
        return None
    return (
        "status.applicability",
        f"status does not apply to {note.frontmatter.type} records",
    )


# Extra checks on a typed link target, keyed by the target's declared type.
_TARGET_CHECKS: dict[
    str, Callable[[Note, Note, VaultIndex], tuple[str, str] | None]
] = {"Status": _validate_wikilink_status}


def validate_placement(note: Note, index: VaultIndex) -> list[Diagnostic]:
    """Check the record's directory against its declared type.

    Args:
        note: Selected record; templates are excluded by the caller.
        index: Index supplying the selected vault boundary.

    Returns:
        list[Diagnostic]: A placement error for a misplaced built-in type.
            Unknown custom types and Reference records have no placement rule.
    """
    kind = note.frontmatter.type
    directories = {
        "Content": "content",
        "Session": "sessions",
        "Clue": "clues",
        "Transcript": "sessions/transcripts",
        "Player": "reference/players",
        "Type": "reference/types",
        "Status": "reference/statuses",
    }
    if kind not in directories:
        return []
    scope = find_campaign(note.path, index.root)
    prefix = index.root
    if scope and kind not in {"Type", "Status"}:
        prefix /= f"campaigns/{scope}"
    expected = prefix / directories[kind]
    valid = note.path.is_relative_to(expected)
    if kind in {"Session", "Clue", "Transcript", "Player"} and not scope:
        valid = False
    # The Transcript subtree is reserved for transcripts, not Session records.
    if kind == "Session" and note.path.is_relative_to(expected / "transcripts"):
        valid = False
    if valid:
        return []
    return [
        Diagnostic(
            note.path.relative_to(index.root).as_posix(),
            "record.placement",
            f"{kind} belongs under {expected.relative_to(index.root)}"
            + (
                " inside a numeric campaign"
                if scope is None and kind not in {"Content", "Type", "Status"}
                else ""
            ),
        )
    ]


def validate_filename(note: Note, index: VaultIndex) -> list[Diagnostic]:
    """Check campaign record filenames and the Session ordinal they encode.

    Args:
        note: Selected record; templates are excluded by the caller.
        index: Index supplying the selected vault boundary.

    Returns:
        list[Diagnostic]: A Session, Clue or Transcript outside every campaign,
            one whose filename does not match its campaign's pattern, or a
            Session whose session_number differs from its filename. Other
            types have no filename rule.
    """
    scope = find_campaign(note.path, index.root)
    kind = note.frontmatter.type
    if kind not in {"Session", "Clue", "Transcript"}:
        return []
    path = note.path.relative_to(index.root).as_posix()
    if scope is None:
        return [
            Diagnostic(
                path,
                "record.identity",
                f"cannot check {kind} filename: record is outside every campaign",
            )
        ]
    number = scope.removeprefix("campaign_")
    pattern = {
        "Clue": rf"C-{number}-[0-9]{{4}}",
        "Session": rf"S-{number}-([0-9]{{3}})",
        "Transcript": rf"S-{number}-[0-9]{{3}} Transcript",
    }[kind]
    match = re.fullmatch(pattern, note.path.stem)
    if match is None:
        return [
            Diagnostic(path, "record.identity", f"{kind} filename must match {pattern}")
        ]
    ordinal = note.frontmatter.get("session_number")
    # bool is an int subclass, so compare the exact type.
    if kind == "Session" and (type(ordinal) is not int or ordinal != int(match[1])):
        return [
            Diagnostic(
                path,
                "record.identity",
                "session_number must match filename ordinal",
                "session_number",
            )
        ]
    return []


def validate_campaigns(note: Note, index: VaultIndex) -> list[Diagnostic]:
    """Check the record's campaign directory and any campaign_N blocks.

    Args:
        note: Selected record; only Content records carry campaign_N blocks.
        index: Index supplying the vault boundary.

    Returns:
        list[Diagnostic]: A record under campaigns/ that is not inside a
            campaign_N directory; a Content record's campaign_N field that is
            not a mapping; or one whose directory does not exist or differs
            from the campaign containing the record.
    """
    relative = note.path.relative_to(index.root)
    parts = relative.parts
    diagnostics: list[Diagnostic] = []
    if parts[0] == "campaigns" and not CAMPAIGN_NAME.fullmatch(parts[1]):
        diagnostics.append(
            Diagnostic(
                relative.as_posix(),
                "campaign.name",
                "records under campaigns/ belong inside a campaign_N directory",
            )
        )
    if note.frontmatter.type != "Content":
        return diagnostics
    scope = find_campaign(note.path, index.root)
    for field, block in note.frontmatter.items():
        if not CAMPAIGN_NAME.fullmatch(field):
            continue
        directory = index.root / "campaigns" / field
        if not isinstance(block, dict):
            diagnostics.append(
                Diagnostic(
                    relative.as_posix(),
                    "campaign.block",
                    "campaign block must be a mapping of campaign state",
                    field,
                )
            )
        elif (
            not directory.is_dir()
            or directory.is_symlink()
            or (scope is not None and scope != field)
        ):
            diagnostics.append(
                Diagnostic(
                    relative.as_posix(),
                    "campaign.mismatch",
                    "campaign block must name an existing campaign compatible "
                    "with the record's location",
                    field,
                )
            )
    return diagnostics


def validate_identity_links(note: Note, index: VaultIndex) -> list[Diagnostic]:
    """Check the link that names a campaign Session's or Transcript's identity.

    Args:
        note: Selected record; templates are excluded by the caller.
        index: Whole-vault index used to resolve the link.

    Returns:
        list[Diagnostic]: A Session or Transcript outside every campaign, one
            whose identity link cannot be resolved, a Session whose campaign is
            not the containing campaign's overview, or a Transcript not named
            after its linked Session plus " Transcript". Other types have no
            identity link.
    """
    scope = find_campaign(note.path, index.root)
    kind = note.frontmatter.type
    if kind not in {"Session", "Transcript"}:
        return []
    path = note.path.relative_to(index.root).as_posix()
    field = "campaign" if kind == "Session" else "session"
    resolved, error = index.resolve_field(note, field)
    if scope is None:
        message = f"cannot check {kind} identity: record is outside every campaign"
    elif error is not None:
        message = f"cannot check {kind} identity: {error}"
    elif kind == "Session":
        if resolved == index.root / f"campaigns/{scope}/reference/Campaign.md":
            return []
        message = "campaign must link to the containing campaign overview"
    elif resolved is not None and note.path.stem == f"{resolved.stem} Transcript":
        return []
    else:
        message = "Transcript filename must match its linked Session plus ' Transcript'"
    rule = "campaign.mismatch" if kind == "Session" else "record.identity"
    return [Diagnostic(path, rule, message, field)]
