---
type: "[[types/Content]]"
subtype: "PC"
summary: "A former customs courier with a talent for rooftop escapes and borrowed authority."
player: "[[Rowan]]"
campaign_1:
  first_session: "[[S-1-001]]"
  last_session: "[[S-1-002]]"
---
## Notes

Talia left the customs service after being ordered to burn a cargo register before its owners could contest a seizure. She keeps her old courier sash but has cut its official tassels away. She wants the Glass Petrel free of countinghouse control.

Her fencing is brisk and improvised: a railing, a coat or a swinging cargo hook is part of the argument.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[Pending]] OR status = [[Hinted]])
```

## Appearances

- [[S-1-001]]: Crossed the market rooftops and secured [[Brass Harbor Seal]] from a distracted clerk.
- [[S-1-002]]: Presented the seal to the quay watch and opened the harbor boom.
