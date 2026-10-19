<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/armarium-banner-dark.svg">
    <img src="docs/assets/armarium-banner.svg" alt="Armarium" width="900">
  </picture>
</p>

Armarium turns an [Obsidian](https://obsidian.md) vault into a home for a
tabletop roleplaying campaign: its characters, places, factions and lore, the
clues the players are chasing, and a record of every session. It gives each kind
of note a defined shape, and comes with a command-line tool that creates, checks
and maintains the vault. It works with any game system; support for D&D 5.5
comes as an extension.

## Why use it

- **Notes that stay consistent.** Every kind of record, from an NPC or a
  location to a clue or a session, has a template and a set of rules, and
  `armarium validate` tells you when something has drifted.
- **Links that hold.** Rename, merge or delete a record, and Armarium rewrites
  every link to it.
- **Preparation kept apart from play.** A Session separates what you prepared
  from what happened at the table, and each character, place and item lists the
  sessions it actually appeared in.
- **Clues you can follow.** Each clue moves from pending through hinted to
  revealed, and every character, place and item shows the clues still open
  about it.
- **More than one campaign.** Campaigns in one vault can share a setting while
  keeping their own state.
- **Help at the table and after it.** Turn a session recording into a
  transcript, print handouts for the players, and illustrate records.
- **Ready for AI assistants.** Every vault carries instructions and skills, so
  coding agents such as Claude Code or Codex can prepare sessions, write them
  up and update records following the same rules you do.

## Getting started

You need Python 3.14 or later, [uv](https://docs.astral.sh/uv/), and Obsidian
1.13.7 or later with the core Bases plugin and the
[Frontmatter Markdown Links](https://github.com/mnaoumov/obsidian-frontmatter-markdown-links)
community plugin enabled.

```sh
uv tool install armarium
armarium init my-campaign
```

Then:

1. Open `my-campaign` in Obsidian and enable the plugins above.
2. Describe your campaign in `campaigns/campaign_1/reference/Campaign.md`.
3. From inside the vault, add your first record, for example
   `armarium add content "Port Briselle" --subtype Location`.
4. Check the vault with `armarium validate .`.

To see what a vault looks like in use, browse [vaults/example](vaults/example),
a small vault with two campaigns.

## Learn more

The [documentation](docs/README.md) covers every command, the vault's layout
and record types, extensions and agent support.

Armarium is MIT licensed. See the [changelog](CHANGELOG.md) for what's new, and
the [issues](https://github.com/willbradshaw/armarium/issues) for planned work.
