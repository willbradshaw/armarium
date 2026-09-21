# Create a basic setting vault

The basic installer copies the canonical starter into a **new path outside the
Armarium checkout**. The setting vault is an independent directory and can have
its own Git repository. Python 3.10 or later is the only installation dependency;
the installer uses no model API, network access, Obsidian plugins, or third-party
Python libraries.

## Install

From the Armarium checkout:

```sh
python3 scripts/create_vault.py /path/to/my-setting \
  --name "My Setting" \
  --campaign 1 "First Campaign"
```

The parent directory must already exist. The destination itself must not exist,
even as an empty directory or symlink. The installer will not merge into, repair,
or overwrite an existing vault. It renders into a temporary staging directory
first, then copies to the fresh destination. A filesystem failure during the final
copy can leave an incomplete destination; inspect it before manually removing it
or choosing another path. Rerunning will refuse that existing directory.

Use an absolute script path to run from another directory. Campaign IDs are stable
lowercase letters/digits with optional internal hyphens (at most 40 characters).
Display names may contain spaces, punctuation, and Unicode. IDs are unique within
a vault; display names do not determine filesystem paths.

Omitting `--campaign` creates ID `1`, named `First Campaign`. Repeat the flag to
create several campaigns at installation:

```sh
python3 scripts/create_vault.py /path/to/my-setting \
  --name "My Setting" \
  --campaign expedition "The Survey" \
  --campaign homecoming "The Return"
```

Open the resulting directory as a vault in Obsidian and open `Home.md`. No fictional
setting or campaign content is installed. The displayed campaign names and empty
indexes are the only campaign-specific initialization.

## Installed structure

```text
my-setting/
  Home.md
  Vault Guide.md
  armarium.json
  AGENTS.md
  CLAUDE.md
  .gitignore
  .obsidian/app.json
  world/
    World.md
    locations/ npcs/ factions/ lore/ objects/
  campaigns/
    Campaigns.md
    <id>/
      Campaign-<id>.md
      Sessions-<id>.md
      Clues-<id>.md
      sessions/ transcripts/ pcs/ players/ npcs/
      locations/ factions/ lore/ objects/ clues/
  reference/
    Reference.md
    sources/
  templates/
  types/
  statuses/
  bases/Views.md
  assets/
    Assets.md
    maps/ handouts/ images/
  .input/
    unprocessed/ processed/
  .scratch/
```

Empty content folders contain `.gitkeep` so they survive version control. Input
and scratch folders are entirely ignored, including their markers; recreate them
as needed after a clone. Durable embeddable assets live in a visible folder.

The JSON configuration records the setting name, campaign IDs/paths, and starter
version/content hash. It contains no absolute machine paths. Its toolkit repository
reference identifies Armarium, but `revision: null` explicitly means no shared
runtime dependency has been installed or pinned yet. Do not interpret the starter
hash as runtime validation or an update mechanism.

## Scope of this increment

Included:

- Static navigation and canonical system-general templates.
- Linked page types and all six accepted clue-status pages.
- Per-campaign state using a `campaigns` map, even on campaign-bound entities.
- Recent Isles session organization with generic encounters/rewards instead of
  required classes, levels, XP tables, or a setting calendar.
- Separate world/reference/campaign/asset/input/scratch responsibilities.
- Local agent instructions preserving canon, review, and Git workflow conventions.

Live views are intentionally not implemented here. Clue indexes and Active Clues
contain ordinary links, and session prep tables hold links/session-specific notes
without copying source summaries. The explicit `prepared_*` lists prepare for the
Bases evaluation in issue #5. Dataview and Bases are not required for this increment.

No utilities or shared skills are copied into the vault. `AGENTS.md` and `CLAUDE.md`
are local orientation, not a claim of installed or tested agent skills. Shared
runtime/skill discovery, updates, adding a campaign to an existing vault, and
full lint commands belong to later issues. No Git repository is initialized and
no existing setting is migrated.

The installed templates and instructions are user-owned. Moving the vault does not
break its paths or require the Armarium checkout for reading and ordinary editing.

## Original example

Follow [the two-campaign example](../examples/two-campaigns/README.md) to populate a
separate test vault. The ordinary installer does not copy this fixture.

The example demonstrates a shared place and NPC across two campaign eras, separate
PC histories, a still-pending candidate clue, and an abandoned unrevealed candidate
that has not been promoted into world canon.

## Automated acceptance checks

The smoke tests need PyYAML only for parsing installed Markdown frontmatter:

```sh
uv run --no-project --with 'PyYAML>=6,<7' python -m unittest discover -s tests -v
```

Alternatively, install `requirements-dev.txt` in a development environment and run
`python -m unittest discover -s tests -v`. The installer itself has no dependency on
that environment.

The suite exercises an unrelated working directory, a fresh path with spaces,
multiple campaigns, metadata/link integrity, original example semantics, malformed
input, existing targets, failed rendering, repeatable output, relocation, and
preservation of customized files. These tests are a starter-specific smoke check,
not the full planned vault validator.

## Manual Obsidian acceptance checklist

Record the Obsidian version and observed results when executing this checklist.
File-level tests do not establish that this in-app check has passed.

- Open the blank vault at its independent path; Home navigation and campaign hubs
  should work without installing community plugins.
- Open templates and their type links; same-named templates/type pages must resolve
  to the intended full-path target.
- Copy the Session template into a campaign, fill its identity, and verify the
  Preparation/Notes organization and generic tables are usable.
- Open the example, follow both campaign session indexes to the shared observatory
  and NPC, and verify separate histories are understandable.
- Follow the pending clue from Active Clues and the abandoned clue from its closed
  index; the abandoned passage claim must not appear as world fact.
- Confirm empty folders and the assets location are usable. No Base or Dataview
  output is expected in this basic increment.
