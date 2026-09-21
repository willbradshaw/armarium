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

Follow-on work is tracked in the [repository issues](https://github.com/willbradshaw/armarium/issues).
Private reference vaults are not included.
