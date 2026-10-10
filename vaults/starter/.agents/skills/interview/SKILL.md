---
name: interview
description: Interviews the GM to settle canon that exists only in their head, such as lore, history, motivations or names, then writes it into the records it concerns.
---

# Interview the GM

This procedure draws out canon the vault does not hold yet, by questioning the
GM until the topic is settled, and then records it.

You need the topic, and the campaign it belongs to, if it belongs to one. Run
the commands from the vault root, or add `--vault PATH`.

## 1. Read what the vault already says

Find the records the topic touches with `armarium find` and `armarium trace`,
and read them and their Type records.

Open by stating what is already established, with links, so that the GM can
correct your reading before it shapes your questions. Never ask what the vault
already answers.

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

## 3. Leave names to the GM

When the GM asks for suggestions, give ten to fifteen in prose, grouped by
style, with a gloss for each and the ones you favour. Follow any naming rules
in `AGENTS.md`.

## 4. Write it up

Record each settled fact once, in the record of the entity it is most about,
where that record's Type record says it belongs. Other records link to it. A
fact the players do not know yet goes there too. Create a Clue only if the GM
asks for one.

For each record you write, follow `.agents/skills/update-record/SKILL.md`. Then,
for each other record the new facts bear on, such as one that links to a record
you changed, follow `.agents/skills/refresh-record/SKILL.md`.

The GM's edits to what you wrote are canon. Carry them through the other records
you wrote, and report any fact an edit removed rather than restoring it.

## 5. Report

Say which records you wrote, which stubs you created and which records you
refreshed, and list the questions still open. The work is finished when the GM
says it is.
