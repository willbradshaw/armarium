---
type: "[[reference/types/Content]]"
subtype: "NPC"
summary: "A harbor pilot and duelist who settles arguments with unnerving courtesy."
stats:
campaign_1:
  first_session: "[[campaigns/campaign_1/sessions/S-1-001]]"
  last_session: "[[campaigns/campaign_1/sessions/S-1-002]]"
---
## Notes

Mara captains the pilot cutter Wake-lark and sits in the [[content/Free Pilots Assembly]]. A burn scar runs across her left palm; she wears a ribbon over it when negotiating. She asks opponents to name their terms before drawing her narrow sabre.

She knows the outer shoals by the sound of surf against the sea wall. Her practical loyalties are to pilots whose livelihoods depend on access to [[content/Port Briselle]].

## Active Clues

```dataview
TABLE WITHOUT ID file.link as "ID", text as "Text"
FROM "campaigns/campaign_1/clues"
WHERE contains(subjects, this.file.link) AND (status = [[reference/statuses/Pending]] OR status = [[reference/statuses/Hinted]])
```

## Appearances

- [[campaigns/campaign_1/sessions/S-1-001]]: Met the crew at [[campaigns/campaign_1/content/Quay Nine]] and explained how the harbor seal opened the night boom.
- [[campaigns/campaign_1/sessions/S-1-002]]: Delivered [[campaigns/campaign_1/content/Shoal Chart]] after the vote and declined to explain its pencilled tide marks.
