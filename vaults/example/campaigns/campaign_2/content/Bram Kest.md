---
type: "[[types/Content]]"
subtype: "PC"
summary: "A salvage diver who counts every person aboard before he counts the cargo."
player: "[[Peter]]"
campaign_2:
  first_session: "[[S-2-001]]"
  last_session: "[[S-2-001]]"
---

## Notes

Bram learned diving by retrieving dropped tools beneath harbor
hoists. He checks his partner's knots twice and his own three times. With
[[Darian Holt]], he runs the [[Tern Salvage Company]]; he refuses jobs that treat
trapped sailors as an inconvenience to salvage.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_2/clues"
WHERE contains(subjects, this.file.link) AND (status = [[Pending]] OR status = [[Hinted]])
```

## Appearances

- [[S-2-001]]: Entered [[Copper Finch]] through the stern hatch and freed [[Oren Vale]] before the rising water reached the cabin beams.
