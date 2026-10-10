---
name: interview
description: Interviews the GM to develop part of this Armarium vault, such as lore, history, characters or places, then records what is settled.
---

# Interview the GM

This procedure develops a topic by questioning the GM until it is settled, and
then records it. The topic may be new, a gap in what the vault holds, or
something the GM wants to rethink.

You need the topic, and the campaign it belongs to, if it belongs to one. Run
the commands from the vault root, or add `--vault PATH`.

## 1. Read what the vault already says

Find the records the topic touches with `armarium find` and `armarium trace`,
and read them and their Type records.

Open by stating what is already established, with links, so that the GM can
correct your reading before it shapes your questions. Do not ask what the vault
already answers unless the GM wants to revisit it.

## 2. Ask in rounds

Settle one dependency at a time: what a thing is before how it works, and how
it works before what it is called. Ask a few questions per round, and give your
recommended answer to each.

If you have a tool for structured questions, offer options that the GM can
combine, and leave room for an answer of their own. Otherwise, ask in prose and
list the options. When the GM wants to discuss something, drop the options and
reply in prose.

After each round, look for contradictions and gaps in the answers, and ask
about them. Test ideas with situations in the world, such as "a traveller
arrives by sea: what do they see first?". Push back when an idea does not hold
together, and drop your own suggestion cleanly when it fails.

Draft nothing until the GM says the topic is settled.

## 3. Write it up

Record each settled fact once, in the record of the entity it is most about,
where that record's Type record says it belongs. Other records link to it. A
fact the players do not know yet goes there too. Create a Clue only if the GM
asks for one.

For each record you write, follow `.agents/skills/update-record/SKILL.md`. Then,
for each other record the new facts bear on, such as one that links to a record
you changed, follow `.agents/skills/refresh-record/SKILL.md`.

The GM's edits to what you wrote are canon. Carry them through the other records
you wrote, and report any fact an edit removed rather than restoring it.

## 4. Report

Say which records you wrote, which stubs you created and which records you
refreshed, and list the questions still open. The work is finished when the GM
says it is.
