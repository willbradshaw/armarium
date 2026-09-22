---
type: "[[types/Content]]"
subtype: "Object"
summary: "A pilot cutter captained by [[Captain Mara Vey]] for the approaches to [[Port Briselle]]."
campaign_1:
  first_session:
  last_session:
  held_by: "[[Captain Mara Vey]]"
---
## Notes

A white stripe runs along the cutter's dark hull so incoming captains can identify
it against the cliffs. Its deck carries spare marker buoys and neatly coiled
towing lines. [[Captain Mara Vey]] uses it to guide ships through [[The Red Teeth]].

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns"
WHERE type = [[types/Clue]] AND contains(subjects, this.file.link) AND (status = [[Pending]] OR status = [[Hinted]])
SORT file.name ASC
```

## Appearances

- N/A
