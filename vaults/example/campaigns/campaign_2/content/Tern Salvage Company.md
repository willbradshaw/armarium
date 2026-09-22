---
type: "[[types/Content]]"
subtype: "Faction"
summary: "The two-man salvage partnership sailing [[Tern]]."
members: ["[[Darian Holt]]", "[[Bram Kest]]"]
campaign_2:
  first_session: "[[S-2-001]]"
  last_session: "[[S-2-001]]"
---

## Notes

[[Darian Holt]] and [[Bram Kest]] split earnings after repairs and supplies.
Either can call off a dive. Their working rule is to rescue people before arguing
over goods, even when that leaves them with nothing to sell.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_2/clues"
WHERE contains(subjects, this.file.link) AND (status = [[Pending]] OR status = [[Hinted]])
```

## Appearances

- [[S-2-001]]: Accepted the [[Free Pilots Assembly]] rescue request and brought [[Oren Vale]] to safety; the company deferred its salvage bargain until he could speak for himself.
