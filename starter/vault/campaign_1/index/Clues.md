---
aliases:
  - Secrets and Clues
  - Secrets
---

Tracker for in-play clues in [[campaign_1/Campaign]]. Each clue lives in its own file under `campaign_1/clues/` with a stable ID (`C-1-XXXX`).

A clue is a persistent GM-known candidate fact not fully known to players. It may
be abandoned without revelation and never become canon. Status definitions live in
[[statuses/Pending]], [[statuses/Hinted]], [[statuses/Revealed]],
[[statuses/Abandoned]], [[statuses/Dormant]], and [[statuses/Superseded]].

## Active

```dataview
TABLE WITHOUT ID
  file.link as "ID",
  status as "Status",
  last_session as "Last Session",
  text as "Text"
FROM "campaign_1/clues"
WHERE status != [[statuses/Revealed]] AND status != [[statuses/Abandoned]] AND status != [[statuses/Superseded]] AND status != [[statuses/Dormant]]
SORT file.name ASC
```

## Closed

```dataview
TABLE WITHOUT ID
  file.link as "ID",
  status as "Status",
  last_session as "Last Session",
  text as "Text"
FROM "campaign_1/clues"
WHERE status = [[statuses/Revealed]] OR status = [[statuses/Abandoned]] OR status = [[statuses/Superseded]] OR status = [[statuses/Dormant]]
SORT file.name ASC
```
