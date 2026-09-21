---
type: "[[types/Clue]]"
status: "[[statuses/Pending]]"
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
FROM "campaign_1/sessions"
WHERE contains(file.outlinks, this.file.link)
SORT date ASC
```
