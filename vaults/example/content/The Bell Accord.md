---
type: "[[reference/types/Content]]"
subtype: "Lore"
summary: "A harbor compact governing public hearings and the release of detained vessels."
campaign_1:
  first_session: "[[campaigns/campaign_1/sessions/S-1-001]]"
  last_session: "[[campaigns/campaign_1/sessions/S-1-002]]"
---
## Notes

Any captain can claim a hearing by ringing the quay bell while presenting a vessel's name and a witness. The hearing must finish before the vessel can be sold. The compact protects a hearing, not immunity from debts or criminal charges.

The [[content/Free Pilots Assembly]] supplies a witness when countinghouse officers dispute a petition.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[reference/statuses/Pending]] OR status = [[reference/statuses/Hinted]])
```

## Appearances

- [[campaigns/campaign_1/sessions/S-1-001]]: [[campaigns/campaign_1/content/Esme Calder]] invoked the hearing provision to delay the sale of the Glass Petrel.
- [[campaigns/campaign_1/sessions/S-1-002]]: The pilots certified the crew's petition under the hearing provision.
