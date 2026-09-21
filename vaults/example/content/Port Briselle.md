---
type: "[[reference/types/Content]]"
subtype: "Location"
summary: "A terraced harbor republic where pilot guilds bargain with merchant captains."
parent_location: "[[content/The Crownless Coast]]"
campaign_1:
  first_session: "[[campaigns/campaign_1/sessions/S-1-001]]"
  last_session: "[[campaigns/campaign_1/sessions/S-1-002]]"
---
## Notes

Briselle climbs a red limestone headland above a harbor crowded with lateen sails. Hoists carry cargo over tiled roofs; narrow bridges join countinghouses that disagree about nearly everything except the price of a berth.

The harbor bell is maintained jointly by the countinghouses and the [[content/Free Pilots Assembly]]. Under [[content/The Bell Accord]], captains can demand a public hearing before an impounded ship is sold. [[campaigns/campaign_1/content/Quay Nine]] lies below the eastern signal tower.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[reference/statuses/Pending]] OR status = [[reference/statuses/Hinted]])
```

## Appearances

- [[campaigns/campaign_1/sessions/S-1-001]]: The crew crossed the rooftop market to reach the eastern docks.
- [[campaigns/campaign_1/sessions/S-1-002]]: The crew carried its petition through the harbor and escaped aboard the Glass Petrel.
