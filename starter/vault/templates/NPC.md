---
type: "[[types/NPC]]"
aliases:
summary: ""
stats:
birth_year:
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
FROM "campaign_1/clues"
WHERE contains(subjects, this.file.link) AND status != [[statuses/Revealed]] AND status != [[statuses/Abandoned]] AND status != [[statuses/Superseded]] AND status != [[statuses/Dormant]]
```
## Appearances
- N/A
