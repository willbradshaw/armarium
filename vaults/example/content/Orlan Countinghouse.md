---
type: "[[types/Content]]"
subtype: "Faction"
summary: "A ship-financing house in [[Port Briselle]] that lends against vessels and future cargoes."
members:
campaign_1:
  first_session: "[[S-1-001]]"
  last_session: "[[S-1-002]]"
---
## Notes

Orlan advances money for repairs and voyages in exchange for a claim on the next
cargo. Its clerks keep duplicate contracts, one at the countinghouse and one with
the harbor registry. Its influence rests on keeping ships sailing and making
repossession look like ordinary administration.

In [[S-1-001]], Orlan sought the sale of [[Glass Petrel]] against an alleged unpaid
repair advance. The [[Glass Petrel Crew]] disputed the charge. The subsequent
hearing certified the party's right to contest the sale; it did not settle the debt.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[Pending]] OR status = [[Hinted]])
```

## Appearances

- [[S-1-001]]: Orlan's auction officer posted the sale notice on [[Glass Petrel]], prompting the party to demand a hearing.
- [[S-1-002]]: Orlan's messenger challenged the petition before the [[Free Pilots Assembly]], which certified it despite the objection.
