---
type: "[[reference/types/Content]]"
subtype:
summary:
aliases:
campaign_1:
  first_session:
  last_session:
---
## Notes
- N/A
## Active Clues
```dataview
TABLE WITHOUT ID
  file.link as "ID",
  text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND status != [[reference/statuses/Revealed]] AND status != [[reference/statuses/Abandoned]] AND status != [[reference/statuses/Superseded]] AND status != [[reference/statuses/Dormant]]
```
## Appearances
- N/A
