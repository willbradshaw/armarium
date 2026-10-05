# Agent instructions and skills

A vault created by [`armarium init`](init.md) carries instructions for coding
agents that work in it: `AGENTS.md`, a vault guide and a set of skills,
copied from the [starter vault](../vaults/starter/).

## What a vault holds

| Path | Holds |
| --- | --- |
| `AGENTS.md` | what agents read first: working rules, then the vault's own rules |
| `docs/armarium.md` | a short guide to the vault's layout, record types and commands, for anyone |
| `.agents/skills/NAME/SKILL.md` | a skill: the procedure for one kind of task |
| `.claude/skills/NAME/SKILL.md` | a stub with the same name and description, telling the agent to read the skill in `.agents/skills/` |

Skills follow the [Agent Skills](https://agentskills.io/specification) format.
`.agents/skills/` is the location shared between agents; Claude Code reads only
`.claude/skills/`, so each skill has a stub there. A stub's name and description
must match its skill's, since they decide when the skill is used. Each skill's
description says what it is for; the
[starter vault](../vaults/starter/.agents/skills/) holds the current set.

`docs/` and `AGENTS.md` are [optional root entries](vault.md#other-entries), and
the two skills directories are hidden, so [validation](validate.md) reads none
of them as records.
