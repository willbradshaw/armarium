---
type: "[[types/Content]]"
subtype: "Lore"
summary: "A compact governing vessel-seizure hearings in [[Port Briselle]]."
campaign_1:
  first_session: "[[S-1-001]]"
  last_session: "[[S-1-002]]"
---
## Notes

A vessel's captain or authorized crew representative can claim a hearing by ringing the quay bell while presenting a vessel's name and a witness. The hearing must finish before the vessel can be sold. The compact protects a hearing, not immunity from debts or criminal charges.

The [[Free Pilots Assembly]] supplies a witness when countinghouse officers dispute a petition.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns"
WHERE type = [[types/Clue]] AND contains(subjects, this.file.link) AND (status = [[Pending]] OR status = [[Hinted]])
SORT file.name ASC
```

## Appearances

- [[S-1-001]]: [[Esme Calder]] invoked the hearing provision to delay the sale of the [[Glass Petrel]].
- [[S-1-002]]: The [[Free Pilots Assembly]] certified [[Glass Petrel Crew|the crew]]'s petition under the hearing provision.
