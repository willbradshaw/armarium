---
type: "[[reference/types/Content]]"
subtype: "Object"
summary: "A brass stamp granting one vessel passage through Briselle's night boom."
campaign_1:
  first_session: "[[campaigns/campaign_1/sessions/S-1-001]]"
  last_session: "[[campaigns/campaign_1/sessions/S-1-002]]"
  held_by: "[[campaigns/campaign_1/content/Talia Venn]]"
---
## Notes

The face shows a bell above three waves. It accompanies the written [[assets/harbor-pass.txt]] issued at [[campaigns/campaign_1/content/Quay Nine]]. Its purpose was established in [[campaigns/campaign_1/sessions/S-1-001]]; see [[campaigns/campaign_1/clues/C-1-0001]].

The stamp is reusable; the signed permission names the vessel and crossing.

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[reference/statuses/Pending]] OR status = [[reference/statuses/Hinted]])
```

## Appearances

- [[campaigns/campaign_1/sessions/S-1-001]]: [[campaigns/campaign_1/content/Talia Venn]] obtained the seal with the ship's passage papers.
- [[campaigns/campaign_1/sessions/S-1-002]]: [[campaigns/campaign_1/content/Talia Venn]] used it to authenticate the order at the boom.
