---
type: "[[types/Content]]"
subtype: "NPC"
summary: "The stubborn owner-captain of [[Copper Finch]], more practiced at bargaining than swimming."
stats:
campaign_2:
  first_session: "[[S-2-001]]"
  last_session: "[[S-2-001]]"
---

## Notes

Oren keeps his cargo accounts in a waxed sleeve inside his coat.
He sent his deckhands ashore in the boat's tender after the rudder broke, then
became trapped when he returned below to check the flooding. [[Bram Kest]] freed
him in [[S-2-001]]. Aboard [[Tern]], Oren asked to catch his breath before agreeing
to any salvage terms.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_2/clues"
WHERE contains(subjects, this.file.link) AND (status = [[Pending]] OR status = [[Hinted]])
```

## Appearances

- [[S-2-001]]: Struck the cabin beams to guide [[Bram Kest]] to him, escaped aboard [[Tern]], and asked the rival salvagers to postpone their argument.
