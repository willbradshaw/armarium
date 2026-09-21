---
type: "[[reference/types/Content]]"
subtype: "Object"
summary: "A salt-stained chart of the outer shoals with pencilled tide marks."
campaign_1:
  first_session: "[[campaigns/campaign_1/sessions/S-1-002]]"
  last_session: "[[campaigns/campaign_1/sessions/S-1-002]]"
  held_by: "[[campaigns/campaign_1/content/Glass Petrel Crew]]"
---
## Notes

The chart records soundings, exposed rocks and three safe channels beyond [[content/Port Briselle]]. [[content/Captain Mara Vey]] delivered it to the crew following the Assembly's vote in [[campaigns/campaign_1/sessions/S-1-002]].

Small pencilled marks appear beside two tide heights. Their meaning has not been established; the crew noticed them before departure.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[reference/statuses/Pending]] OR status = [[reference/statuses/Hinted]])
```

## Appearances

- [[campaigns/campaign_1/sessions/S-1-002]]: The pilots entrusted the chart to the crew, which inspected its unexplained tide marks.
