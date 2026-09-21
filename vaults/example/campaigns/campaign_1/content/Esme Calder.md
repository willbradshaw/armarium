---
type: "[[types/Content]]"
subtype: "PC"
summary: "A disgraced advocate who treats every duel as a negotiation with unusually sharp punctuation."
player: "[[Ellis]]"
campaign_1:
  first_session: "[[S-1-001]]"
  last_session: "[[S-1-002]]"
---
## Notes

Esme lost her place in a countinghouse court after defending a crew whose wages had been seized as collateral. She can recite harbor procedure while balancing on a wet rail, though she prefers a dry lectern.

She carries an unsigned letter of reinstatement and has not decided whether it is a promise or a threat.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[Pending]] OR status = [[Hinted]])
```

## Appearances

- [[S-1-001]]: Invoked [[The Bell Accord]] to halt the ship's sale and acquired [[Blue Signal Flare]].
- [[S-1-002]]: Won the pilots' certification and fired the flare to coordinate the departure.
