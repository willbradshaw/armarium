---
type: "[[types/Content]]"
subtype: "Object"
summary: "A brass stamp granting one vessel passage through [[Port Briselle|Briselle]]'s night boom."
campaign_1:
  first_session: "[[S-1-001]]"
  last_session: "[[S-1-002]]"
  held_by: "[[Talia Venn]]"
---
## Notes

The face shows a bell above three waves. It accompanies the written [[harbor-pass.txt]] issued at [[Quay Nine]]. Its purpose was established in [[S-1-001]]; see [[C-1-0001]].

The stamp is reusable; the signed permission names the vessel and crossing.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[Pending]] OR status = [[Hinted]])
```

## Appearances

- [[S-1-001]]: [[Talia Venn]] obtained the seal with [[Glass Petrel]]'s passage papers.
- [[S-1-002]]: [[Talia Venn]] used it to authenticate [[Glass Petrel]]'s passage order at [[Quay Nine]].
