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
    Findings,
    Result,
    VaultNotFoundError,
    check_vault,
    find_campaign,
    find_children,
    find_files,
    find_vault,
    iter_wikilinks,
    parse_directories,
    parse_wikilink,
)
from armarium.parse import Record, Section
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


# Infrastructure every vault must contain. Together with the directories Type
# records declare, these bound where every entry in the vault may live. The
# Obsidian settings make the folder open in Obsidian as the records expect.
VAULT_DIRECTORIES = (
    ".obsidian",
    ".obsidian/snippets",
    "assets",
    "campaigns",
    "content",
    "notes",
    "reference/schemas",
    "reference/statuses",
    "reference/templates",
    "reference/types",
    "reference/views",
)
VAULT_TYPES = (
    "Clue",
    "Content",
    "Note",
    "Player",
    "Reference",
    "Session",
    "Status",
    "Transcript",
    "Type",
)
VAULT_FILES = (
    ".obsidian/app.json",
    ".obsidian/appearance.json",
    ".obsidian/snippets/armarium-prose.css",
)
VAULT_STATUSES = ("Abandoned", "Dormant", "Hinted", "Pending", "Revealed", "Superseded")
VAULT_TEMPLATES = ("Clue", "Content", "Note", "Player", "Session", "Transcript")
CAMPAIGN_DIRECTORIES = (
    "clues",
    "content",
    "notes",
    "reference/indexes",
    "reference/players",
    "sessions",
    "sessions/transcripts",
)
CAMPAIGN_FILES = ("reference/Campaign.md", "reference/indexes/Clues.md")

# Where non-Markdown files may live outside assets/, by extension.
ASSET_EXCEPTIONS = {".base": "reference/views", ".schema.json": "reference/schemas"}

# An Appearances entry: a wikilink, a colon and a description.
ENTRY = re.compile(rf"({WIKILINK.pattern}): \S.*")

# A Transcript utterance opens with a speaker tag, a space and text.
SPEECH = re.compile(r"\[[^\[\]]+\] \S")

# Fields that link a record to its predecessor, followed record to record.
CHAIN_FIELDS = {"Content": "parent_location", "Clue": "superseded_by"}

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
        "superseded_by": Target("Clue", local=True),
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
            Typed files receive their vault-local schema checks; absent
            schemas produce errors, and invalid schemas fail validation
            without being counted as missing coverage. A record that fails
            its schema stage gets no further checks. Links are checked
            against the whole vault; only linked Markdown dependencies are
            parsed. No source files are modified.

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
    record, diagnostics = (
        index.parse(path) if index is not None else Record.parse(path, root)
    )
    if record is None:
        return Result(diagnostics=diagnostics, checked=1)
    # 1. Skip templates and untyped files
    findings = Findings(relative)
    if path.is_relative_to(root / "reference/templates"):
        findings.add(
            "record.template",
            "template parsed; completed-record validation skipped",
            severity="info",
        )
        return Result(diagnostics=findings.diagnostics, skipped=1)
    if record.frontmatter.type is None:
        findings.add(
            "record.type", "type is required and must be a canonical wikilink", "type"
        )
        return Result(diagnostics=findings.diagnostics, checked=1)
    # 2. Validate against the vault-local schema; a failure ends the checks
    schema, diagnostics = select_schema(record, root)
    if schema is not None:
        diagnostics.extend(schema.validate(record))
    findings += Findings(relative, diagnostics)
    unsupported = int(any(d.rule == "schema.unsupported" for d in diagnostics))
    if any(d.severity == "error" for d in diagnostics):
        return Result(
            diagnostics=sorted(findings.diagnostics), checked=1, unsupported=unsupported
        )
    # 3. Run the record checks against the whole vault
    if index is None:
        index = VaultIndex(root)
        index.records[path] = (record, [])
    findings = sum((check(record, index) for check in RECORD_CHECKS), findings)
    return Result(
        diagnostics=sorted(findings.diagnostics), checked=1, unsupported=unsupported
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
        result += Result(diagnostics=validate_vault(context).diagnostics)
    return result.add_context(context, relative_to=path.resolve())


def validate_vault(root: Path) -> Findings:
    """Check a vault root's shared infrastructure and campaign layout.

    Args:
        root: Resolved vault directory.

    Returns:
        Findings: Problems attributed to the vault itself (an empty path,
            which directory validation rebases onto the vault), each naming
            the affected entry. Every entry must lie inside a required
            directory, fixed or declared by a Type record; record contents
            are validated separately.
    """
    findings = Findings("")
    required: dict[str, bool] = {}
    # Directories a required directory lies beneath; they exist by implication.
    ancestors: set[Path] = set()

    def require(relative: str, directory: bool) -> None:
        # Fixed and declared directories overlap; report each entry once.
        if relative in required:
            return
        required[relative] = directory
        if directory:
            ancestors.update(Path(relative).parents)
        path = root / relative
        present = path.is_dir() if directory else path.is_file()
        kind = "directory" if directory else "file"
        findings.diagnose(
            path.is_symlink() or not present,
            "vault.required",
            f"required {kind} {relative} is missing",
        )

    # 1. Require the shared directories and definitions
    for relative in VAULT_DIRECTORIES:
        require(relative, True)
    for relative in VAULT_FILES:
        require(relative, False)
    for name in VAULT_TYPES:
        require(f"reference/types/{name}.md", False)
    for name in VAULT_STATUSES:
        require(f"reference/statuses/{name}.md", False)
    for name in VAULT_TEMPLATES:
        require(f"reference/templates/{name}.md", False)

    # 2. Check the campaign layout
    campaigns = root / "campaigns"
    found: list[str] = []
    if not campaigns.is_dir() or campaigns.is_symlink():
        findings.add("vault.campaign", "cannot check campaigns: campaigns/ is missing")
    else:
        for child in find_children(campaigns):
            if child.is_dir() and CAMPAIGN_NAME.fullmatch(child.name):
                found.append(child.name)
            else:
                findings.add(
                    "vault.campaign",
                    f"campaigns/{child.name} is not a campaign_N directory",
                )
        findings.diagnose(
            not found, "vault.campaign", "campaigns/ has no campaign_N directory"
        )
        for name in found:
            for relative in CAMPAIGN_DIRECTORIES:
                require(f"campaigns/{name}/{relative}", True)
            for relative in CAMPAIGN_FILES:
                require(f"campaigns/{name}/{relative}", False)

    # 3. Require the directories each Type record declares for its records
    types = root / "reference/types"
    if not types.is_dir() or types.is_symlink():
        for rule, subject in (
            ("vault.type", "declared directories"),
            ("vault.entry", "vault entries"),
            ("schema.missing", "schema coverage"),
        ):
            findings.add(rule, f"cannot check {subject}: reference/types is missing")
        return findings
    definitions = [file for file in find_files(types) if file.suffix.lower() == ".md"]
    for file in definitions:
        relative = file.relative_to(root).as_posix()
        record, failures = Record.parse(file, root)
        if record is None:
            findings.add(
                "vault.type",
                f"cannot check {relative} directories: {failures[0].message}",
            )
            continue
        try:
            directories = parse_directories(record.frontmatter.get("directories"))
        except ValueError as exc:
            findings.add("vault.type", f"{relative}: {exc}")
            continue
        for scope, path in directories.items():
            if scope == "shared":
                require(path, True)
            for name in found if scope == "campaign" else ():
                require(f"campaigns/{name}/{path}", True)

    # 4. Report entries outside the vault skeleton
    named = {Path(relative) for relative, directory in required.items() if directory}
    pending = [root]
    while pending:
        directory = pending.pop()
        parent = directory.relative_to(root)
        # An ancestor of a required directory is closed to other entries.
        closed = parent in ancestors
        for child in find_children(directory):
            entry = child.relative_to(root)
            location = entry.as_posix()
            if entry == Path("campaigns"):
                # Phase 2 reports its entries; check the campaigns it found.
                pending += [child / name for name in found]
            elif child.is_dir():
                # A reported directory is not descended into.
                if not closed or entry in named | ancestors:
                    pending.append(child)
                else:
                    findings.add(
                        "vault.entry", f"{location} is not in the vault skeleton"
                    )
            elif closed and parent not in named:
                # A closed directory holds files only if it is itself required.
                findings.add("vault.entry", f"{location} is not in the vault skeleton")
            elif child.suffix.lower() != ".md" and entry.parts[0] != "assets":
                # Non-Markdown files belong in assets/, except views and schemas.
                findings.diagnose(
                    not any(
                        child.name.lower().endswith(suffix)
                        and entry.is_relative_to(home)
                        for suffix, home in ASSET_EXCEPTIONS.items()
                    ),
                    "vault.entry",
                    f"{location} is not Markdown and belongs in assets/",
                )

    # 5. Match schemas and Type definitions by name: Clue.md <-> clue.schema.json.
    schemas = root / "reference/schemas"
    if not schemas.is_dir() or schemas.is_symlink():
        findings.add(
            "schema.missing",
            "cannot check schema coverage: reference/schemas is missing",
        )
        return findings
    names = {file.stem for file in definitions}
    schema_names: set[str] = set()
    for file in find_files(schemas):
        relative = file.relative_to(root).as_posix()
        if not file.name.endswith(".schema.json"):
            findings.diagnose(
                file.suffix.lower() == ".json",
                "schema.unused",
                f"{relative} is not named <type>.schema.json",
            )
            continue
        try:
            Schema.load(file, root)
        except (OSError, ValueError, SchemaError, RecursionError) as exc:
            findings.add("schema.invalid", f"{relative}: {exc}")
        name = file.name.removesuffix(".schema.json")
        schema_names.add(name)
        findings.diagnose(
            name not in {definition.lower() for definition in names},
            "schema.unused",
            f"{relative} matches no Type definition",
        )
    for definition in sorted(names):
        findings.diagnose(
            definition.lower() not in schema_names,
            "schema.missing",
            f"no vault-local schema for {definition}",
        )
    return findings


def validate_appearances(record: Record, index: VaultIndex) -> Findings:
    """Reconcile a Content record's Appearances list with its campaign blocks.

    Args:
        record: Selected record; only Content records carry Appearances.
        index: Vault index used to resolve the linked Sessions.

    Returns:
        Findings: Problems with the Appearances section or its entries, with
            the order of campaigns and of each campaign's appearances, and
            with the campaign_N blocks' first_session and last_session.
    """
    if record.frontmatter.type != "Content":
        return Findings.from_record(record, index)
    # 1. Read the recorded appearances
    appearances, findings = _read_appearances(record, index)
    # 2. Validate the sequence of campaigns
    order = [int(campaign.removeprefix("campaign_")) for campaign, _, _ in appearances]
    findings.diagnose(order != sorted(order), "history.order", "campaigns out of order")
    # 3. Check each campaign with appearances or a block
    campaigns = {campaign for campaign, _, _ in appearances}
    checks = (
        _check_campaign_history(
            record,
            index,
            campaign,
            [(ordinal, path) for c, ordinal, path in appearances if c == campaign],
        )
        for campaign in sorted(campaigns | record.frontmatter.campaigns.keys())
    )
    return sum(checks, findings)


def _read_appearances(
    record: Record, index: VaultIndex
) -> tuple[list[tuple[str, int, Path]], Findings]:
    """Collect the appearances recorded under a Content record's Appearances.

    Args:
        record: Content record to read.
        index: Vault index used to resolve and parse linked Sessions.

    Returns:
        tuple[list[tuple[str, int, Path]], Findings]: Campaign, session number
            and path of each Session linked under Appearances, in list order,
            and the problems found. A malformed section ends the read; a
            malformed or unusable entry is omitted.
    """
    findings = Findings.from_record(record, index)
    # 1. Find and validate the Appearances section.
    history: list[tuple[str, int, Path]] = []
    sections = [
        s for s in record.body.walk() if s.level == 2 and s.title == "Appearances"
    ]
    if findings.diagnose(not sections, "history.format", "no Appearances heading"):
        return history, findings
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
            return history, findings
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
        return history, findings
    # 3. Collect the linked Sessions.
    linked: list[tuple[int, Record]] = []
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
        session = linked_record(target, record, index, Target("Session"))
        if isinstance(session, tuple):
            findings.add(
                "history.entry",
                f"cannot check appearance: {session[1]}",
                line=appearance.line,
            )
            continue
        linked.append((appearance.line, session))
    # 4. Validate the linked Sessions.
    scope = find_campaign(record.path, index.root)
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
    return history, findings


def _check_campaign_history(
    record: Record, index: VaultIndex, campaign: str, history: list[tuple[int, Path]]
) -> Findings:
    """Check one campaign's recorded appearances against its campaign_N block.

    Args:
        record: Content record being checked.
        index: Vault index used to resolve the block's Session links.
        campaign: Campaign directory name, campaign_N.
        history: That campaign's appearances as (ordinal, Session path), in
            list order; empty when none are recorded.

    Returns:
        Findings: Appearances out of order or repeated, a missing campaign_N
            block, and a block range that disagrees with the appearances.
    """
    findings = Findings.from_record(record, index)
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
    block = record.frontmatter.campaigns.get(campaign)
    if block is None:
        findings.add(
            "history.block", f"no {campaign} block for its appearances", campaign
        )
        return findings
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
        resolved, error = index.resolve_field(record, location)
        if error is not None:
            findings.add("history.range", f"cannot check {location}: {error}", location)
            continue
        findings.diagnose(
            resolved != expected,
            "history.range",
            f"{location} must be [[{expected.stem}]]",
            location,
        )
    return findings


def validate_clue(record: Record, index: VaultIndex) -> Findings:
    """Check a Clue's subjects against its text and the order of its Sessions.

    Args:
        record: Selected record; only Clues carry text, subjects and Session range.
        index: Vault index used to resolve the links.

    Returns:
        Findings: subjects that are not exactly the records linked in text, or
            a link that cannot be resolved for that comparison
            (clue.subjects); a last_session without first_session
            (history.range); a last_session before first_session, or a Session
            that cannot be ordered (history.order).
    """
    findings = Findings.from_record(record, index)
    if record.frontmatter.type != "Clue":
        return findings
    # 1. Resolve every link in text and subjects
    linked: dict[str, set[Path]] = {"text": set(), "subjects": set()}
    comparable = True
    for link in record.links:
        if link.field not in linked:
            continue
        result = None if link.error else linked_record(link.target, record, index)
        if not isinstance(result, Record):
            reason = link.error or (result[1] if result else "not a record")
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
        if record.frontmatter.get(field) is None:
            ordinals[field] = None
            continue
        resolved, error = index.resolve_field(record, field)
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
    return findings


def validate_transcript(record: Record, index: VaultIndex) -> Findings:
    """Check that a Transcript body follows the transcript grammar.

    After the frontmatter, the body is a run of titled level-two sections.
    Each holds one bullet list whose items are the utterances: single
    paragraphs opening with a speaker tag, a space and text. After the tag,
    square brackets may appear only inside wikilinks, so that a tagged line
    whose leading dash is missing, which CommonMark folds into the previous
    item, is still reported.

    Args:
        record: Selected record; only Transcripts carry speech.
        index: Vault index used to name the record.

    Returns:
        Findings: A finding at each offending line: a block before the
            first heading or a heading that is not a titled level two
            (transcript.heading); a section without a list, a block that is
            not a bullet list, or a second list (transcript.section); an item
            holding more than one paragraph (transcript.item); item text
            without a speaker tag, or with brackets after it outside wikilinks
            (transcript.speaker).
    """
    findings = Findings.from_record(record, index)
    if record.frontmatter.type != "Transcript":
        return findings
    # 1. Nothing precedes the first heading; every heading is a titled level two
    for block in record.body.blocks:
        findings.add(
            "transcript.heading", "content before the first heading", line=block.line
        )
    sections = [s for s in record.body.walk() if s is not record.body]
    for section in sections:
        findings.diagnose(
            section.level != 2 or not section.title.strip(),
            "transcript.heading",
            "heading must be ## with a title",
            line=section.line,
        )
    # 2. Each section holds one bullet list and nothing else
    for section in sections:
        findings.diagnose(
            not section.blocks,
            "transcript.section",
            "section holds no bullet list",
            line=section.line,
        )
        for position, block in enumerate(section.blocks):
            if findings.diagnose(
                block.kind != "list",
                "transcript.section",
                "only a bullet list may follow a heading",
                line=block.line,
            ):
                continue
            findings.diagnose(
                position > 0,
                "transcript.section",
                "one bullet list per section",
                line=block.line,
            )
            # 3. Each item is one paragraph opening with a speaker tag
            for item in block.children:
                findings.diagnose(
                    bool(item.children),
                    "transcript.item",
                    "utterance must be a single paragraph",
                    line=item.line,
                )
                match = SPEECH.match(item.text)
                if match is None:
                    findings.add(
                        "transcript.speaker",
                        "utterance must open with a speaker tag",
                        line=item.line,
                    )
                    continue
                rest = WIKILINK.sub("", item.text[match.end() - 1 :])
                findings.diagnose(
                    "[" in rest or "]" in rest,
                    "transcript.speaker",
                    "square brackets after the speaker tag",
                    line=item.line,
                )
    return findings


def validate_wikilinks(record: Record, index: VaultIndex) -> Findings:
    """Check every link the record contains against the vault.

    Links within a type-bound field must target a correctly placed record
    meeting that field's Target requirements; see _link_targets.

    Args:
        record: Selected record inside the indexed vault.
        index: Whole-vault file index and lazy record cache for this run.

    Returns:
        Findings: Problems attributed to the selected record, with metadata
            locations or body source lines: links that are malformed, cannot be
            resolved, name a missing anchor or fail their field's requirements,
            a list entry in a type-bound field that names the same file as an
            earlier entry (link.duplicate), and links that an unescaped ``|``
            splits across table cells. Unrelated records are not parsed. Query
            execution and ordinary URLs are excluded.
    """
    findings = Findings.from_record(record, index)
    targets = _link_targets(record)
    seen: dict[str, set[Path]] = {}
    for link in record.links:
        # 1. Check the link as written
        if link.error is not None:
            problem: tuple[str, str] | None = ("link.syntax", link.error)
        else:
            problem = validate_wikilink(
                link.target, record, index, targets.get(link.field), link.anchor
            )
        if problem is not None:
            findings.add(*problem, link.location, link.line)
        # 2. A list entry in a type-bound field repeating an earlier entry
        if link.error is None and link.field in targets and link.location != link.field:
            resolved, _ = index.resolve(link.target, record.path)
            if resolved is None:
                continue
            findings.diagnose(
                resolved in seen.setdefault(link.field, set()),
                "link.duplicate",
                f"[[{link.target}]] repeats an earlier {link.field} entry",
                link.location,
            )
            seen[link.field].add(resolved)
    # 3. Links that a table cell boundary cuts in two: the row reads as a
    # whole, but Obsidian splits its cells at every unescaped pipe.
    lines = record.body.text.splitlines()
    for row in (block for block in record.body.iter_blocks() if block.kind == "row"):
        broken = (
            isinstance(p, ValueError)
            for c in row.children
            for p in iter_wikilinks(c.text)
        )
        whole = (
            isinstance(p, ValueError)
            for p in iter_wikilinks(lines[row.line - record.body.line])
        )
        findings.diagnose(
            any(broken) and not any(whole),
            "link.syntax",
            "table cell boundary splits a wikilink; escape | as \\|",
            line=row.line,
        )
    return findings


def _link_targets(record: Record) -> dict[str, Target]:
    """Collect the Target requirements for a record's type-bound fields.

    Args:
        record: Selected record whose type, subtype and campaign blocks select
            the requirements.

    Returns:
        dict[str, Target]: Requirements keyed by frontmatter location: the
            universal fields, those for the record's (type, subtype), and
            campaign_N block fields bound to campaign_N. Custom fields are not
            interpreted by name. A Clue's superseded_by is bound regardless of
            status; the Clue schema forbids it outside Superseded.
    """
    kind = record.frontmatter.type or ""
    subtype = record.frontmatter.get("subtype")
    targets = LINK_TARGETS | RECORD_LINK_TARGETS.get((kind, None), {})
    if isinstance(subtype, str):
        targets |= RECORD_LINK_TARGETS.get((kind, subtype), {})
    if kind == "Content":
        for field in record.frontmatter.campaigns:
            # Block fields are bound to that block's campaign, not the record's.
            targets[f"{field}.first_session"] = Target("Session", campaign=field)
            targets[f"{field}.last_session"] = Target("Session", campaign=field)
            if subtype == "Object":
                targets[f"{field}.held_by"] = Target(
                    "Content", frozenset({"PC", "NPC", "Faction"}), field
                )
    return targets


def validate_wikilink(
    target: str,
    record: Record,
    index: VaultIndex,
    expected: Target | None = None,
    anchor: str = "",
) -> tuple[str, str] | None:
    """Check that one wikilink target resolves to a usable vault file.

    Args:
        target: Parsed wikilink target, without alias or anchor.
        record: Record containing the link; its path breaks resolution ties and its
            declared type takes part in target-specific checks.
        index: Whole-vault file index and lazy record cache for this run.
        expected: Requirements on the target record, or None for any file.
        anchor: Heading path or ``^block-id`` the link names, if any.

    Returns:
        tuple[str, str] | None: The problem found by linked_record, or None when
            the target is usable.
    """
    result = linked_record(target, record, index, expected, anchor)
    return result if isinstance(result, tuple) else None


@overload
def linked_record(
    target: str, record: Record, index: VaultIndex, expected: Target, anchor: str = ""
) -> Record | tuple[str, str]: ...


@overload
def linked_record(
    target: str,
    record: Record,
    index: VaultIndex,
    expected: None = None,
    anchor: str = "",
) -> Record | tuple[str, str] | None: ...


def linked_record(
    target: str,
    record: Record,
    index: VaultIndex,
    expected: Target | None = None,
    anchor: str = "",
) -> Record | tuple[str, str] | None:
    """Resolve one wikilink target and check it, returning the record it names.

    Args:
        target: Parsed wikilink target, without alias or anchor.
        record: Record containing the link; its path breaks resolution ties and its
            declared type takes part in target-specific checks.
        index: Whole-vault file index and lazy record cache for this run.
        expected: Requirements on the target record, or None for any file.
        anchor: Heading path or ``^block-id`` the link names, if any. Checked
            against a linked record's structure; non-record targets such as
            assets and Bases views have no headings or blocks to check.

    Returns:
        Record | tuple[str, str] | None: The linked record when it parses and meets
            expected; None when no record type is expected and the target is a
            usable non-record file or self-anchor; otherwise the rule and message
            for a missing, ambiguous or unparseable target, an anchor the record
            lacks, one that is not a correctly placed record of the expected
            type and subtype, one outside the expected campaign, or one failing
            its type's own check.
    """
    resolved, rule = index.resolve(target, record.path)
    if rule:
        return rule, f"cannot uniquely resolve [[{target}]]; use a vault-relative path"
    linked = None
    if resolved is not None and resolved.suffix.lower() == ".md":
        linked, failures = index.parse(resolved)
        if failures:
            relative = resolved.relative_to(index.root)
            return "link.malformed", f"referenced record {relative} cannot be parsed"
    if anchor and linked is not None:
        problem = _check_anchor(linked, anchor)
        if problem is not None:
            return problem
    if expected is None:
        return linked
    kind = expected.record_type
    if (
        linked is None
        or linked.frontmatter.type != kind
        or validate_placement(linked, index).diagnostics
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
        required = find_campaign(record.path, index.root)
    scope = find_campaign(linked.path, index.root)
    shared = kind == "Content" and scope is None
    if required is not None and scope != required and not shared:
        allowed = required + (" or shared content" if kind == "Content" else "")
        return "campaign.mismatch", f"[[{target}]] must belong to {allowed}"
    check = _TARGET_CHECKS.get(kind)
    problem = check(linked, record, index) if check else None
    return problem if problem is not None else linked


def _check_anchor(record: Record, anchor: str) -> tuple[str, str] | None:
    """Check that a record contains the heading path or block id an anchor names.

    Headings match Obsidian's link rules: case-insensitively, ignoring the
    characters ``# | [ ] ^`` and runs of whitespace, on the heading text as
    written. ``A#B`` names heading B beneath heading A. A block id matches any
    paragraph or item ending in ``^id`` anywhere in the record.

    Args:
        record: Parsed record the link resolved to.
        anchor: Heading path or ``^block-id`` after the link's ``#``.

    Returns:
        tuple[str, str] | None: A link.anchor problem, or None when found.
    """
    stem = record.path.stem
    if anchor.startswith("^"):
        wanted = anchor[1:].casefold()
        blocks = record.body.iter_blocks()
        if any(
            b.block_id is not None and b.block_id.casefold() == wanted for b in blocks
        ):
            return None
        return "link.anchor", f"[[{stem}#{anchor}]]: no block {anchor}"
    within: list[Section] = [record.body]
    for segment in anchor.split("#"):
        wanted = _heading_key(segment)
        within = [
            s
            for c in within
            for s in c.walk()
            if s is not c and _heading_key(s.title) == wanted
        ]
        if not within:
            return "link.anchor", f"[[{stem}#{anchor}]]: no heading {segment}"
    return None


def _heading_key(text: str) -> str:
    """Normalise heading text the way Obsidian matches heading links."""
    return " ".join(re.sub(r"[#|\[\]^]", "", text).split()).casefold()


def _validate_wikilink_status(
    status: Record, record: Record, index: VaultIndex
) -> tuple[str, str] | None:
    """Check that a linked Status applies to the linking record's type.

    Args:
        status: Correctly placed Status definition the link resolved to.
        record: Record containing the link.
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
    record_type, error = index.resolve_field(record, "type")
    if error is not None:
        return "status.applicability", f"cannot check applicability: {error}"
    if applies_to == record_type:
        return None
    return (
        "status.applicability",
        f"status does not apply to {record.frontmatter.type} records",
    )


# Extra checks on a typed link target, keyed by the target's declared type.
_TARGET_CHECKS: dict[
    str, Callable[[Record, Record, VaultIndex], tuple[str, str] | None]
] = {"Status": _validate_wikilink_status}


def validate_placement(record: Record, index: VaultIndex) -> Findings:
    """Check the record's directory against the directories its type declares.

    Each Type record declares where its records live: shared paths under the
    vault root, campaign paths under each campaigns/campaign_N. A record
    belongs to the longest declared directory containing it, so a directory
    declared inside another type's (Transcript's sessions/transcripts inside
    Session's sessions) claims its subtree. Other subfolders inside a
    declared directory are allowed.

    Args:
        record: Selected record; templates are excluded by the caller.
        index: Index supplying the vault boundary and the Type records.

    Returns:
        Findings: A record.placement error when the type declares no usable
            directories, the record lies outside them, or another type's
            longer declaration claims its directory.
    """
    findings = Findings.from_record(record, index)
    kind = record.frontmatter.type or ""
    declarations = index.declared_directories()

    def describe(scope: str, path: str) -> str:
        return path if scope == "shared" else f"campaigns/campaign_N/{path}"

    # 1. The type must declare where its records live
    if findings.diagnose(
        kind not in declarations,
        "record.placement",
        f"cannot check placement: {kind} declares no directories",
    ):
        return findings
    # 2. The deepest declared directory containing the record must be its type's
    containing = index.containing_directories(record.path)
    if containing and kind in containing[-1][2]:
        return findings
    declared = " or ".join(
        describe(area, path) for area, path in declarations[kind].items()
    )
    message = f"{kind} belongs under {declared}"
    if any(kind in names for _, _, names in containing):
        message += f", outside {describe(*containing[-1][:2])}"
    findings.add("record.placement", message)
    return findings


def validate_filename(record: Record, index: VaultIndex) -> Findings:
    """Check the record's filename and the Session ordinal it encodes.

    Args:
        record: Selected record; templates are excluded by the caller.
        index: Index supplying the selected vault boundary.

    Returns:
        Findings: A filename with leading, trailing, doubled or non-space
            whitespace; a Session, Clue or Transcript outside every campaign,
            one whose filename does not match its campaign's pattern, or a
            Session whose session_number differs from its filename. Other
            types have no further filename rule.
    """
    findings = Findings.from_record(record, index)
    # 1. Check the whitespace of every filename
    stem = record.path.stem
    if findings.diagnose(
        stem != " ".join(stem.split()),
        "record.identity",
        "filename has leading, trailing or doubled whitespace",
    ):
        return findings
    # 2. Check the campaign pattern of numbered records
    scope = find_campaign(record.path, index.root)
    kind = record.frontmatter.type
    if kind not in {"Session", "Clue", "Transcript"}:
        return findings
    if scope is None:
        findings.add(
            "record.identity",
            f"cannot check {kind} filename: record is outside every campaign",
        )
        return findings
    number = scope.removeprefix("campaign_")
    pattern = {
        "Clue": rf"C-{number}-[0-9]{{4}}",
        "Session": rf"S-{number}-([0-9]{{3}})",
        "Transcript": rf"S-{number}-[0-9]{{3}} Transcript",
    }[kind]
    match = re.fullmatch(pattern, stem)
    if match is None:
        findings.add("record.identity", f"{kind} filename must match {pattern}")
        return findings
    # 3. Compare a Session's ordinal with its filename
    ordinal = record.frontmatter.get("session_number")
    # bool is an int subclass, so compare the exact type.
    findings.diagnose(
        kind == "Session" and (type(ordinal) is not int or ordinal != int(match[1])),
        "record.identity",
        "session_number must match filename ordinal",
        "session_number",
    )
    return findings


def validate_campaigns(record: Record, index: VaultIndex) -> Findings:
    """Check the record's campaign directory and any campaign_N blocks.

    Args:
        record: Selected record; only Content records carry campaign_N blocks.
        index: Index supplying the vault boundary.

    Returns:
        Findings: A record under campaigns/ that is not inside a campaign_N
            directory; a Content record's campaign_N field that is not a
            mapping; or one whose directory does not exist or differs from
            the campaign containing the record.
    """
    findings = Findings.from_record(record, index)
    # 1. Check the record's directory
    parts = record.path.relative_to(index.root).parts
    findings.diagnose(
        parts[0] == "campaigns" and not CAMPAIGN_NAME.fullmatch(parts[1]),
        "campaign.name",
        "records under campaigns/ belong inside a campaign_N directory",
    )
    if record.frontmatter.type != "Content":
        return findings
    # 2. Check each campaign_N block
    scope = find_campaign(record.path, index.root)
    for field, block in record.frontmatter.items():
        if not CAMPAIGN_NAME.fullmatch(field):
            continue
        directory = index.root / "campaigns" / field
        if findings.diagnose(
            not isinstance(block, dict),
            "campaign.block",
            "campaign block must be a mapping of campaign state",
            field,
        ):
            continue
        findings.diagnose(
            not directory.is_dir()
            or directory.is_symlink()
            or (scope is not None and scope != field),
            "campaign.mismatch",
            "campaign block must name an existing campaign compatible "
            "with the record's location",
            field,
        )
    return findings


def validate_identity_links(record: Record, index: VaultIndex) -> Findings:
    """Check the link that names a campaign Session's or Transcript's identity.

    Args:
        record: Selected record; templates are excluded by the caller.
        index: Whole-vault index used to resolve the link.

    Returns:
        Findings: A Session or Transcript outside every campaign, one whose
            identity link cannot be resolved, a Session whose campaign is not
            the containing campaign's overview, or a Transcript not named
            after its linked Session plus " Transcript". Other types have no
            identity link.
    """
    findings = Findings.from_record(record, index)
    scope = find_campaign(record.path, index.root)
    kind = record.frontmatter.type
    if kind not in {"Session", "Transcript"}:
        return findings
    field = "campaign" if kind == "Session" else "session"
    resolved, error = index.resolve_field(record, field)
    if scope is None:
        message = f"cannot check {kind} identity: record is outside every campaign"
    elif error is not None:
        message = f"cannot check {kind} identity: {error}"
    elif kind == "Session":
        if resolved == index.root / f"campaigns/{scope}/reference/Campaign.md":
            return findings
        message = "campaign must link to the containing campaign overview"
    elif resolved is not None and record.path.stem == f"{resolved.stem} Transcript":
        return findings
    else:
        message = "Transcript filename must match its linked Session plus ' Transcript'"
    rule = "campaign.mismatch" if kind == "Session" else "record.identity"
    findings.add(rule, message, field)
    return findings


def validate_chains(record: Record, index: VaultIndex) -> Findings:
    """Check that the record's chain field never leads back to the record.

    Args:
        record: Selected record; only the types in CHAIN_FIELDS carry a chain.
        index: Whole-vault index used to follow the chain.

    Returns:
        Findings: A link.cycle when following the field from record to record
            returns to this record, or enters a loop elsewhere. A chain ending
            at a null, absent, unresolvable or unparseable link is not a
            cycle; such links are reported by the link checks.
    """
    findings = Findings.from_record(record, index)
    field = CHAIN_FIELDS.get(record.frontmatter.type or "")
    if field is None or record.frontmatter.get(field) is None:
        return findings
    chain: list[Path] = []
    current = record
    while True:
        resolved, error = index.resolve_field(current, field)
        if error or resolved is None or resolved.suffix.lower() != ".md":
            return findings
        via = ", ".join(f"[[{p.stem}]]" for p in chain)
        if resolved == record.path:
            message = (
                f"{field} returns to this record via {via}"
                if via
                else f"{field} links to this record"
            )
            findings.add("link.cycle", message, field)
            return findings
        if resolved in chain:
            findings.add(
                "link.cycle", f"{field} chain loops at [[{resolved.stem}]]", field
            )
            return findings
        linked, _ = index.parse(resolved)
        if linked is None or linked.frontmatter.get(field) is None:
            return findings
        chain.append(resolved)
        current = linked


# Checks every typed record receives, in the order validate_markdown runs them.
RECORD_CHECKS: tuple[Callable[[Record, VaultIndex], Findings], ...] = (
    validate_wikilinks,
    validate_placement,
    validate_filename,
    validate_campaigns,
    validate_identity_links,
    validate_chains,
    validate_appearances,
    validate_clue,
    validate_transcript,
)
