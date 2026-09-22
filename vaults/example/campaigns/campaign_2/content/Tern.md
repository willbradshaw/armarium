---
type: "[[types/Content]]"
subtype: "Object"
summary: "A broad-beamed salvage sloop with a hand-cranked lifting tackle."
campaign_2:
  first_session: "[[S-2-001]]"
  last_session: "[[S-2-001]]"
  held_by: "[[Tern Salvage Company]]"
---

## Notes

The [[Tern Salvage Company]] owns and operates the sloop. A removable deck grate
lets wet lines drain clear of the bunks; the lifting tackle can haul a diver and
his gear without swinging them over the rail.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_2/clues"
WHERE contains(subjects, this.file.link) AND (status = [[Pending]] OR status = [[Hinted]])
```

## Appearances

- [[S-2-001]]: Carried the company from [[Port Briselle]] to [[The Red Teeth]] and received [[Oren Vale]] after the rescue.
