---
type: "[[reference/types/Content]]"
subtype: "Object"
summary: "A blue-burning signal charge wrapped in waxed cloth."
campaign_1:
  first_session: "[[campaigns/campaign_1/sessions/S-1-001]]"
  last_session: "[[campaigns/campaign_1/sessions/S-1-002]]"
  held_by: "GONE"
---
## Notes

When fired, the charge produced a blue light visible across the harbor. It was expended during the departure from [[campaigns/campaign_1/content/Quay Nine]] in [[campaigns/campaign_1/sessions/S-1-002]].

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[reference/statuses/Pending]] OR status = [[reference/statuses/Hinted]])
```

## Appearances

- [[campaigns/campaign_1/sessions/S-1-001]]: [[campaigns/campaign_1/content/Esme Calder]] acquired the charge from the ship's stores.
- [[campaigns/campaign_1/sessions/S-1-002]]: [[campaigns/campaign_1/content/Esme Calder]] fired the charge, consuming it as the departure signal.
