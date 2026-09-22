---
type: "[[types/Content]]"
subtype: "NPC"
summary: "An independent salvager who carries a claim form as carefully as his boarding hook."
stats:
campaign_2:
  first_session: "[[S-2-001]]"
  last_session: "[[S-2-001]]"
---

## Notes

Silas works alone from an unpainted rowing skiff. He speaks softly
and expects everyone else to lean closer. In [[S-2-001]], he met [[Tern]] at the
reef and asserted a prior claim to [[Copper Finch]], holding up a folded form.
The company saw a seal but did not inspect the whole document. He stood aside for
the rescue and agreed to discuss terms afterward.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_2/clues"
WHERE contains(subjects, this.file.link) AND (status = [[Pending]] OR status = [[Hinted]])
```

## Appearances

- [[S-2-001]]: Asserted a salvage claim to [[Copper Finch]] and let [[Tern]] pass when [[Darian Holt]] insisted that the rescue came first.
