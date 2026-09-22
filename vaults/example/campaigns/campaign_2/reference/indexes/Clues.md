---
aliases:
  - Secrets and Clues
  - Secrets
---

Tracker for in-play clues in [[campaign_2/reference/Campaign]]. Each clue lives in its own file under `campaigns/campaign_2/clues/` with a stable ID (`C-2-XXXX`).

A clue is a persistent GM-known candidate fact not fully known to players. It may
be abandoned without revelation and never become canon. Status definitions live in
[[Pending]], [[Hinted]], [[Revealed]],
[[Abandoned]], [[Dormant]], and [[Superseded]].

## Active

```dataview
TABLE WITHOUT ID
  file.link as "ID",
  status as "Status",
  last_session as "Last Session",
  text as "Text"
FROM "campaigns/campaign_2/clues"
WHERE status != [[Revealed]] AND status != [[Abandoned]] AND status != [[Superseded]] AND status != [[Dormant]]
SORT file.name ASC
```

## Closed

```dataview
TABLE WITHOUT ID
  file.link as "ID",
  status as "Status",
  last_session as "Last Session",
  text as "Text"
FROM "campaigns/campaign_2/clues"
WHERE status = [[Revealed]] OR status = [[Abandoned]] OR status = [[Superseded]] OR status = [[Dormant]]
SORT file.name ASC
```
