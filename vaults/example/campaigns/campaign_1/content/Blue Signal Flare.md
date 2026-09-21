---
type: "[[types/Content]]"
subtype: "Object"
summary: "A blue-burning signal charge wrapped in waxed cloth."
campaign_1:
  first_session: "[[S-1-001]]"
  last_session: "[[S-1-002]]"
  held_by: "GONE"
---
## Notes

When fired, the charge produced a blue light visible across the harbor. It was expended during the departure from [[Quay Nine]] in [[S-1-002]].

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[Pending]] OR status = [[Hinted]])
```

## Appearances

- [[S-1-001]]: [[Esme Calder]] acquired the charge from the ship's stores.
- [[S-1-002]]: [[Esme Calder]] fired the charge, consuming it as the departure signal.
