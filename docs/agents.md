# Agent skills and guides

A vault created by [`armarium init`](init.md) carries instructions for coding
agents that work in it: a short `AGENTS.md`, two guides and a set of skills.
They are plain files copied from the [starter vault](../vaults/starter/), and
the vault owns them from then on.

## What a vault holds

| Path | Holds |
| --- | --- |
| `AGENTS.md` | the entry point agents read: a pointer to the agent guide, then the vault's own rules |
| `docs/armarium.md` | a short guide to the vault's layout, record types and commands, for anyone |
| `docs/agents/armarium.md` | working rules for agents, and which skill to follow for which task |
| `.agents/skills/NAME/SKILL.md` | a skill: the procedure for one kind of task |
| `.claude/skills/NAME/SKILL.md` | a stub with the same name and description, telling the agent to read the skill in `.agents/skills/` |

Skills follow the [Agent Skills](https://agentskills.io/specification) format.
`.agents/skills/` is the location shared between agents; Claude Code reads only
`.claude/skills/`, so each skill has a stub there. A stub's name and description
must match its skill's, since they decide when the skill is used.

`docs/` and `AGENTS.md` are [optional root entries](vault.md#other-entries), and
the two skills directories are hidden, so [validation](validate.md) reads none
of them as records.

## Skills

| Skill | Use |
| --- | --- |
| `update-record` | The base procedure for creating or changing any record: find it with [`armarium find`](find.md), read its [Type record](type.md), create it with [`armarium add`](add.md) or edit it, [validate](validate.md), resolve new links, and check the records that link to it with [`armarium trace`](trace.md). Other skills build on it. |

## Changing and updating them

Edit any of these files to suit the vault; add the vault's own rules to
`AGENTS.md`. Upgrading Armarium does not change them. To take a newer version
of a skill or guide, or to add them to a vault created without them, copy the
files from the starter vault.

## Tested hosts

Discovery and use of `update-record` in a fresh vault were checked with Claude
Code 2.1.289, through the stub, and Codex CLI 0.157.1, through `.agents/skills/`.
