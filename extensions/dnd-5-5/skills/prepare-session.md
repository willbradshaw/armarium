# D&D 5.5: rating encounters

This addendum, from the `dnd-5-5` extension, rates each prepared fight against
the party's XP budget. It applies to every campaign, whether or not the
campaign awards XP.

The rules are in
`reference/extensions/dnd-5-5/rules/Combat Encounter Difficulty.md`. Read that
page before rating anything, and take budgets and XP from it, from the
creatures' records or from the GM, never from memory.

## Writing an encounter

Give each fight its own `###` heading under Encounters, named for where or what
it is, such as `### Ambush at the ford`. Put any notes on running it first,
then these tables:

```markdown
#### Enemies
| Type | Number | CR | XP |
| ---- | ------ | -- | -- |

#### Allies
| Type | Number | CR | XP |
| ---- | ------ | -- | -- |

#### Difficulty
| Enemy XP | Characters | Allies | Level | Difficulty |
| -------- | ---------- | ------ | ----- | ---------- |
```

- **Enemies.** One row for each kind of creature. Type links the record
  whose stat block the creature uses, such as a Monster or an NPC. XP is for
  one creature, as its stat block gives it.
- **Allies.** Creatures expected to give the party substantial help in the
  fight, with the same columns as Enemies. One that only tags along or helps
  in a minor way is not listed; mention it in the notes on running the fight.
  Leave the table out when there are none. A character's own familiar or animal
  companion is part of that character, not an ally, and is not listed.
- **Enemy XP.** The sum, over the rows, of Number times XP.
- **Characters and Level.** The number of characters in the party, and their
  level. Read each PC's `level` field. If a level is missing, or the
  characters' levels differ, ask the GM which level to rate the fight at.
- **Allies.** The number of allies in the Allies table, or 0. Each counts as
  one more character of the party's level, as an ally who gives substantial
  help counts as a member of the party when XP is shared. Whether an ally did
  give substantial help is settled after play, when the Session is written
  up.

To calculate the encounter's difficulty, first calculate its Low, Moderate and
High budgets by multiplying the number of characters plus allies by the
corresponding figure in the XP budget table for the party's level. The
encounter's difficulty is then the lowest of these whose budget its Enemy XP
does not exceed. If it exceeds the High budget, write `Above High`. When you
show the encounter to the GM at step 7d, give the three budgets alongside its
Enemy XP, so that the GM can see how close it falls to each.
