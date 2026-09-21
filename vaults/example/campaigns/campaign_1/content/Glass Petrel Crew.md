---
type: "[[reference/types/Content]]"
subtype: "Faction"
summary: "The small company sailing the swift, underfunded cutter Glass Petrel."
members: ["[[campaigns/campaign_1/content/Talia Venn]]", "[[campaigns/campaign_1/content/Esme Calder]]"]
campaign_1:
  first_session: "[[campaigns/campaign_1/sessions/S-1-002]]"
  last_session: "[[campaigns/campaign_1/sessions/S-1-002]]"
---
## Notes

The company operates by written shares: supplies and repairs are paid before profits are divided. The cutter has patched ochre sails, a shallow draft and a galley stove that draws poorly in an easterly wind.

The crew accepted collective custody of [[campaigns/campaign_1/content/Shoal Chart]] at the pilots' hearing in [[campaigns/campaign_1/sessions/S-1-002]]. The chart is kept in the ship's document chest.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[reference/statuses/Pending]] OR status = [[reference/statuses/Hinted]])
```

## Appearances

- [[campaigns/campaign_1/sessions/S-1-002]]: The company accepted custody of the Shoal Chart and coordinated its departure from the quay.
