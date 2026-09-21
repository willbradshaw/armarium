---
type: "[[reference/types/Clue]]"
status: "[[reference/statuses/Pending]]"
text: ""
subjects:
first_session:
last_session:
---
## Sessions
```dataview
TABLE WITHOUT ID
  file.link as "Session",
  date as "Date"
FROM "campaigns/campaign_1/sessions"
WHERE type = [[reference/types/Session]] AND contains(file.outlinks, this.file.link)
SORT date ASC
```
