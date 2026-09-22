---
type: "[[types/Content]]"
subtype: "Faction"
summary: "An association of harbor pilots that keeps [[Port Briselle|Briselle]]'s channel knowledge outside countinghouse control."
members: ["[[Captain Mara Vey]]"]
campaign_1:
  first_session: "[[S-1-002]]"
  last_session: "[[S-1-002]]"
campaign_2:
  first_session: "[[S-2-001]]"
  last_session: "[[S-2-001]]"
---
## Notes

The Assembly maintains channel markers, arbitrates pilot fees and supplies witnesses for harbor hearings. Members vote by placing their brass pilot tokens on a sailcloth tally. [[Captain Mara Vey]] holds a seat for the eastern approaches.

During [[S-1-002]], the Assembly publicly certified [[Glass Petrel Crew|the crew]]'s petition and released [[Shoal Chart]] into its custody.

## Active Clues

### campaign_1

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[Pending]] OR status = [[Hinted]])
```

### campaign_2

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_2/clues"
WHERE contains(subjects, this.file.link) AND (status = [[Pending]] OR status = [[Hinted]])
```

## Appearances

### campaign_1

- [[S-1-002]]: The Assembly voted to certify the petition and entrust [[Glass Petrel Crew|the crew]] with [[Shoal Chart]].

### campaign_2

- [[S-2-001]]: Dispatched the [[Tern Salvage Company]] to rescue whoever remained aboard [[Copper Finch]], without awarding salvage rights.
