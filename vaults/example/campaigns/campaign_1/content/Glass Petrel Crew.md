---
type: "[[types/Content]]"
subtype: "Faction"
summary: "The small company sailing the swift, underfunded cutter [[Glass Petrel]]."
members: ["[[Talia Venn]]", "[[Esme Calder]]"]
campaign_1:
  first_session: "[[S-1-001]]"
  last_session: "[[S-1-002]]"
---
## Notes

The party consists of [[Talia Venn]] and [[Esme Calder]], operating [[Glass Petrel]] as a small sailing company. Under their written shares, supplies and repairs are paid before profits are divided. Both must agree before accepting a new debt in the company's name.

The crew accepted collective custody of [[Shoal Chart]] at the pilots' hearing in [[S-1-002]]. The chart is kept in [[Glass Petrel]]'s document chest.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[Pending]] OR status = [[Hinted]])
```

## Appearances

- [[S-1-001]]: The company agreed to contest [[Orlan Countinghouse]]'s repair charge and seek certification from the [[Free Pilots Assembly]].
- [[S-1-002]]: The company accepted custody of [[Shoal Chart]] and coordinated [[Glass Petrel]]'s departure from [[Quay Nine]].
