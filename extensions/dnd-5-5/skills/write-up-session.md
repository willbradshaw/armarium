# D&D 5.5: experience and levels

This addendum, from the `dnd-5-5` extension, adds the party's experience
points (XP) and any levels gained to a write-up.

Some campaigns award XP, and the characters can gain a level once their XP
reaches the next threshold. Others award none, and the characters gain a level
when the GM decides, often at a milestone in the story. The two are written up
differently.

## Which kind of campaign this is

At step 2, look in the campaign's Session reference for whether the campaign
awards XP. If it awards XP, look also for whether it shares an encounter's XP
as described under "Sharing XP" below, or by a rule of its own.

Where the Session reference does not say, ask the GM before you draft. In step
7, propose adding their answers to the Session reference, so that the questions
are not asked again.

## Sharing XP

Unless the Session reference gives another rule, share each fight's XP like
this:

- Divide the fight's Total XP evenly among the party's characters.
- An ally who gave the party substantial help in the fight counts as one more
  member of the party, whatever its CR, so each character's share is smaller.
  A character's own familiar or animal companion is part of that character,
  not an ally. Whether an ally's help was substantial is the GM's call: if
  this is unclear, ask about it under Questions.

Round each share down to a whole number.

A campaign may use its own rule instead, such as leaving out absent players'
characters, or giving an ally a share in proportion to its XP. Follow the
Session reference where it says so.

## A campaign that awards XP

Add an XP part to the draft, after Loot. It is written under Rewards, in a
`### XP` section before Loot, in this form:

```markdown
### XP
| Combat Encounter | Total XP | XP per PC |
| ---------------- | -------- | --------- |
| Ambush at the ford | 450 | 150 |
| **Total** | **450** | **150** |

| Source | XP per PC |
| ------ | --------- |
| Combat | 150 |
| **Total** | **150** |
| Previous Campaign Total | 2,850 |
| ***Total for Campaign*** | ***3,000*** |
```

- **Combat Encounter.** One row for each fight the Events show ending in the
  party's favour. Name it as its heading under Encounters does, or describe it
  if it was not prepared. A fight still going when the Session ended has no
  row: its XP is awarded in the Session that finishes it.
- **Total XP.** The XP of every creature defeated or otherwise neutralized in
  that fight. Take each creature's XP from the encounter's Enemies table or
  its record. Where neither gives it, ask the GM.
- **XP per PC.** One character's share of the Total XP, as "Sharing XP"
  above describes.
- **Source.** Combat, then one row for each other award of XP that the
  source or the GM names. Propose none yourself.
- **Previous Campaign Total.** The previous Session's Total for Campaign. If
  no earlier Session has one, ask the GM: the characters may have started
  with the XP for a level above 1.
- **Total for Campaign.** Total plus Previous Campaign Total. It assumes
  every character has the same XP. If their totals have come to differ, ask
  the GM how to record them.

Where a figure rests on something the source leaves unclear, such as whether a
creature that fled was neutralized, mark it with `(?)` and ask under
Questions.

Then compare the Total for Campaign with the thresholds in
`reference/extensions/dnd-5-5/rules/Character Advancement.md`. Reaching a
threshold does not by itself give a character the level: campaigns differ on
whether it comes at once, after a rest or at some later point. For each
character whose total reaches a level above their `level` field, ask under
Questions whether they gained that level in this Session. Ask again in each
write-up until the GM says they have.

## A campaign that levels without XP

Write no XP section. If the source is unclear on whether a character gained a
level, ask under Questions.

## Advancement

A character has gained a level only where the source or the GM says so. Never
add one because a threshold was reached.

When a character has gained a level, add an Advancement part to the draft,
written under Rewards in a `### Advancement` section before Loot, with a line
for each character:

```markdown
### Advancement
- [[Talia]] reached level 4.
```

Leave the section out when no one gained a level. As with Loot, it records
the night; the character's record holds their level now.

The Events say nothing of XP or levels, under the rule against numbers in step
3. Where the story marks the moment, the Events tell it in the world's terms.
