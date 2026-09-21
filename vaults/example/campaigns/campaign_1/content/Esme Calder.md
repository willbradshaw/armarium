---
type: "[[reference/types/Content]]"
subtype: "PC"
summary: "A disgraced advocate who treats every duel as a negotiation with unusually sharp punctuation."
player: "[[campaigns/campaign_1/reference/players/Ellis]]"
campaign_1:
  first_session: "[[campaigns/campaign_1/sessions/S-1-001]]"
  last_session: "[[campaigns/campaign_1/sessions/S-1-002]]"
---
## Notes

Esme lost her place in a countinghouse court after defending a crew whose wages had been seized as collateral. She can recite harbor procedure while balancing on a wet rail, though she prefers a dry lectern.

She carries an unsigned letter of reinstatement and has not decided whether it is a promise or a threat.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[reference/statuses/Pending]] OR status = [[reference/statuses/Hinted]])
```

## Appearances

- [[campaigns/campaign_1/sessions/S-1-001]]: Invoked [[content/The Bell Accord]] to halt the ship's sale and acquired [[campaigns/campaign_1/content/Blue Signal Flare]].
- [[campaigns/campaign_1/sessions/S-1-002]]: Won the pilots' certification and fired the flare to coordinate the departure.
