# Armarium

A system-general foundation for AI-assisted tabletop roleplaying knowledge bases:
Obsidian vault structure, page templates, reusable skills, and supporting scripts.

Armarium is intended to provide a coherent default workflow that GMs can customize,
from establishing a knowledge base and preparing sessions to maintaining session
notes and related entities. It is not tied to a particular game, setting, or campaign.
Terminal-based setup is in scope, including use with an AI assistant's help.
A vault can hold multiple campaigns sharing world information.

## Try the basic starter

With Python 3.10 or later, copy the minimal Isles-derived starter:

```sh
python3 scripts/create_vault.py /path/to/new-setting
```

The parent directory must exist and the destination must be new and outside this
checkout. Open the folder in Obsidian and find `campaign_1/Campaign.md` using the
file browser. This increment contains one blank campaign and shared world folders.

See the [starter guide](docs/starter-vault.md) for the source-to-starter extraction
record, exact scope, tests, and pending manual checks. Inherited live queries require
Dataview; the installer does not install plugins. Multi-campaign setup, navigation,
agent support, and evaluated Bases replacements are follow-on increments.

## Project planning

Proposed designs in the planning documents are not final decisions.

- [Product brief](docs/planning/product-brief.md): agreed scope and open questions.
- [Source review](docs/planning/source-review.md): lessons from existing projects.
- [Work programme](docs/planning/work-programme.md): numbered issue index and dependencies.
- [Initial implementation plan](docs/planning/implementation-plan.md): proposed
  numbered sequence, dependencies, and completion criteria.
- [Agent portability](docs/planning/agent-portability.md): Claude Code and Codex as
  the minimum, with broader skill portability and optional API support to investigate.
- [Conventions for review](docs/planning/conventions-review.md): candidate defaults,
  optional workflows, and conflicting source guidance for owner review.

The public project will contain reusable materials and original examples. The
private reference projects used during planning are not included.
