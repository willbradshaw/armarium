---
type: "[[reference/types/Content]]"
subtype: "Location"
summary: "A narrow working quay beneath Briselle's eastern signal tower."
parent_location: "[[content/Port Briselle]]"
campaign_1:
  first_session: "[[campaigns/campaign_1/sessions/S-1-001]]"
  last_session: "[[campaigns/campaign_1/sessions/S-1-002]]"
---
## Notes

A capstan controls the harbor boom beside a customs booth and three weathered mooring rings. The public bell hangs above a stair to the rooftop market.

A stamped [[campaigns/campaign_1/content/Brass Harbor Seal]] authorizes the watch to open the boom at the third bell; the crew confirmed this procedure in [[campaigns/campaign_1/sessions/S-1-001]] (see [[campaigns/campaign_1/clues/C-1-0001]]).

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[reference/statuses/Pending]] OR status = [[reference/statuses/Hinted]])
```

## Appearances

- [[campaigns/campaign_1/sessions/S-1-001]]: The crew rang the public bell and obtained a night-passage authorization.
- [[campaigns/campaign_1/sessions/S-1-002]]: The crew opened the boom and signalled the Glass Petrel out of harbor.
