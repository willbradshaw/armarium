# Armarium

A system-general foundation for AI-assisted tabletop roleplaying knowledge bases:
Obsidian vault structure, page templates, reusable skills, and supporting scripts.

Armarium is intended to provide a coherent default workflow that GMs can customize,
from establishing a knowledge base and preparing sessions to maintaining session
notes and related entities. It is not tied to a particular game, setting, or campaign.
Terminal-based setup is in scope, including use with an AI assistant's help.
A vault can hold multiple campaigns sharing world information.

## Try the basic starter

With Python 3.10 or later, create a new independent setting vault:

```sh
python3 scripts/create_vault.py /path/to/my-setting \
  --name "My Setting" --campaign 1 "First Campaign"
```

The parent directory must exist and the destination must be new. Open the resulting
folder in Obsidian and start at `Home.md`. The installer refuses existing paths and
does not copy campaign content, shared skills, or executable utilities.

See the [starter guide](docs/starter-vault.md) for the layout, multiple campaigns,
tests, and an original example. This first implementation provides static pages
and templates; live views, packaged tooling, agent skill installation, and updates
remain later work. It has no runtime dependencies beyond Python's standard library.

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
