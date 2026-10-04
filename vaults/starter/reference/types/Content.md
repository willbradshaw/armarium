---
type: "[[Type]]"
directories: { shared: content, campaign: content }
---
# Content

Content records describe characters, places, groups, objects, dates, or setting lore.
Keep each shared entity in one record under `content/`; campaign-specific entries
live in `campaigns/campaign_1/content/` (or the corresponding campaign folder).
Share an entity that keeps its identity outside any one campaign, such as a city,
a people or a calendar. Keep it with its campaign when it matters only through
that campaign's story, such as one inn, a minor character or a plot object.

Create a record with `armarium add content NAME --subtype SUBTYPE`, adding
`--campaign N` for a campaign-specific one. It starts from [[templates/Content]];
name it for the entity and supply the subtype's required fields.

## Fields

Every Content record requires `type`, `subtype`, and `summary`. The template sets
`type`; choose subtype NPC, PC, Location, Faction, Object, Lore, Date or Gear, or one
an enabled extension adds, as listed in its README under `reference/extensions/`. Write a short
summary of stable identity, or leave it empty for a stub. A summary says what the
entity is, not its present situation: leave out whereabouts, holders and other
state that play will change. `aliases` is optional:
use a list of alternate names, or omit it or leave it empty when there are none.
`content_tags` is optional too: a list of freeform labels for filtering Content,
such as `Healing` or `Warding`.

| Subtype | Additional required fields |
| --- | --- |
| NPC | `stats`: empty, an internal wikilink, or an HTTP/HTTPS URL. |
| PC | `player`: a nonempty wikilink to a Player record. |
| Location | `parent_location`: empty or a wikilink to Location Content. |
| Faction | `members`: empty if unknown, or a list of PC/NPC Content links. An empty list means no recorded members. |
| Object, Gear | `held_by` inside each campaign block: holder link(s) or `GONE`; may be empty before entering play. |
| Gear | `source`: publication or homebrew attribution; empty when unrecorded. Optional `image` and `url`. |
| Lore | None. |
| Date | `reckoning`: a nonempty link to Lore describing the calendar. `scale`: a nonblank calendar-defined string, such as day or year. |

Object describes narrative artifacts; Gear describes equipment with recorded game
mechanics, whether magical or mundane. Gear may add an `image` path relative to
the vault root or an image URL, and an HTTP/HTTPS `url` for its source. These fields
may be omitted or empty. Other rules-specific fields are custom frontmatter.

Dates represent particular days or periods within a calendar. Recurring calendar
concepts, such as a named month or weekday, are Lore rather than Dates.
Calendar-specific fields are custom frontmatter. A custom vault-local schema can constrain date
notation and allowed scales; the standard schema does not impose those constraints.

Use bare `field:` for null and quote YAML wikilinks. Additional custom fields are
allowed. Object and Gear holders are PC, NPC or Faction Content. Shared-party possession
links to the party's Faction. Lists represent split sets. `GONE` means the object
has left play, for example through sale, loss, destruction or consumption.

## Body and campaign history

Gear begins with a `> [!rules]` callout containing its rules text, optionally
followed by an image embed. An empty callout is allowed for a stub.

All subtypes share Notes, Active Clues and Appearances, in that order.

### Notes

Notes contain established, lasting information about the entity, read without
the context of any one Session. Record only what play or the GM's own material
states; never round a record out with plausible detail. Use `- N/A` while
nothing is established.

- Describe the entity, not the scene in which it was met.
- Describe it in absolute terms; a comparison needs its referent stated.
- One incident is not a trait. What a character did or said once belongs in
  that Session's appearance until it recurs or the GM settles it.
- Leave out state that changes with the situation. For Objects and Gear, the
  current holder belongs in `held_by`.
- A Clue is a candidate fact; displaying it under Active Clues does not
  establish it as world canon. Add a Clue's content to Notes only once the Clue
  is Revealed, and link the Clue there.

### Campaign state

Store campaign state in separate `campaign_1:`, `campaign_2:`, etc. blocks. The
initial template includes campaign 1; retain, remove or add blocks according to
the entry's recorded state. Each existing block requires `first_session` and
`last_session`: both empty before appearances, otherwise links to the earliest
and latest Sessions in that campaign's history.

### Appearances

Use one Appearances list across campaigns; the linked Session IDs identify each
entry's campaign. Give each Session in which the entity appeared one item,
saying in a clause what happened to it or through it in that Session. Do not
retell the Session, and leave lasting traits to Notes. Use `N/A` only when
there are no appearances.

| Subtype | Appears in a Session when |
| --- | --- |
| NPC | on stage in a scene: speaking, acting or dealing directly with those present. |
| PC | doing something noteworthy; attendance alone is not an appearance. |
| Location | the party is physically there. |
| Faction | acting as a body, such as a council sitting or a coordinated action. A member acting alone appears on their own record. |
| Object, Gear | handled: acquired, put to use, transferred or accessed. |
| Lore | its particular identity shapes events, such as a being that acts, a language that is read or a doctrine at issue. Background colour is not an appearance. |
| Date | the Session's played events occur within that day or period. |

A mention is not an appearance: an entity only spoken of, reported or narrated
is found through its backlinks. Nor is preparation: a Session that prepares an
entity records nothing on it until play reaches it. Historical information about
a Date belongs in Notes. Keep acquisition and transfer history in Session
records when current possession changes.

### Active Clues

Active Clues contains exactly one Base embed and no additional text. Its scope follows this record’s location: shared
`content/` items include active Clues from all campaigns; items under
`campaigns/campaign_N/` include only that campaign. Only Pending or Hinted Clues
whose canonical `subjects` link to this item appear. Do not split Active Clues
or Appearances into campaign subheadings.

## Schema

A Content record’s frontmatter requires `type`, `subtype`, `summary` and the
subtype fields listed above. Its body contains Notes, Active Clues and
Appearances headings in that order. Each campaign block includes `first_session`
and `last_session`; Object and Gear campaign blocks also include `held_by`.

See the [Content schema](../schemas/content.schema.json).
