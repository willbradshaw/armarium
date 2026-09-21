---
aliases:
  - Secrets and Clues
  - Secrets
---

Tracker for in-play clues in [[campaigns/campaign_1/reference/Campaign]]. Each clue lives in its own file under `campaigns/campaign_1/clues/` with a stable ID (`C-1-XXXX`).

A clue is a persistent GM-known candidate fact not fully known to players. It may
be abandoned without revelation and never become canon. Status definitions live in
[[reference/statuses/Pending]], [[reference/statuses/Hinted]], [[reference/statuses/Revealed]],
[[reference/statuses/Abandoned]], [[reference/statuses/Dormant]], and [[reference/statuses/Superseded]].

## Active

```dataview
TABLE WITHOUT ID
  file.link as "ID",
  status as "Status",
  last_session as "Last Session",
  text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE status != [[reference/statuses/Revealed]] AND status != [[reference/statuses/Abandoned]] AND status != [[reference/statuses/Superseded]] AND status != [[reference/statuses/Dormant]]
SORT file.name ASC
```

## Closed

```dataview
TABLE WITHOUT ID
  file.link as "ID",
  status as "Status",
  last_session as "Last Session",
  text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE status = [[reference/statuses/Revealed]] OR status = [[reference/statuses/Abandoned]] OR status = [[reference/statuses/Superseded]] OR status = [[reference/statuses/Dormant]]
SORT file.name ASC
```
