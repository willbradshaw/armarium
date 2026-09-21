---
type: "[[reference/types/Content]]"
subtype: "Faction"
summary: "An association of harbor pilots that keeps Briselle's channel knowledge outside countinghouse control."
members: ["[[content/Captain Mara Vey]]"]
campaign_1:
  first_session: "[[campaigns/campaign_1/sessions/S-1-002]]"
  last_session: "[[campaigns/campaign_1/sessions/S-1-002]]"
---
## Notes

The Assembly maintains channel markers, arbitrates pilot fees and supplies witnesses for harbor hearings. Members vote by placing their brass pilot tokens on a sailcloth tally. [[content/Captain Mara Vey]] holds a seat for the eastern approaches.

During [[campaigns/campaign_1/sessions/S-1-002]], the Assembly publicly certified the crew's petition and released [[campaigns/campaign_1/content/Shoal Chart]] into its custody.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[reference/statuses/Pending]] OR status = [[reference/statuses/Hinted]])
```

## Appearances

- [[campaigns/campaign_1/sessions/S-1-002]]: The Assembly voted to certify the petition and entrust the crew with the Shoal Chart.
