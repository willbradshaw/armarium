# Records

Every Markdown file in a [vault](vault.md) is a record: YAML frontmatter that
declares its type, followed by a Markdown body. [`armarium validate`](cli.md)
parses each record, validates it against its type's schema, and checks its
links and cross-record rules. The rules every record shares are below; each
type's own fields, body and conventions are in [Types](type.md).

## Anatomy

```markdown
---
type: "[[types/Content]]"
subtype: NPC
summary: Harbour pilot who witnesses petitions.
aliases: [Mara]
campaign_1:
  first_session: "[[S-1-001]]"
  last_session: "[[S-1-002]]"
---
## Notes
Mara holds a seat for the eastern approaches. ^seat
```

**Frontmatter** is a YAML mapping between the opening and closing `---` lines.
Keys are unique strings; values must be representable in JSON, so dates read as
`YYYY-MM-DD` strings, and YAML anchors may be shared but not recursive. A
record with no frontmatter has an empty mapping, which fails the `type` rule
below. Fields beyond a type's schema are allowed on every type.

**`type`** is required on every record and holds one canonical wikilink to the
record's Type record: `[[types/Content]]` (or `[[Content]]`), with no alias or
anchor. The last path segment names the type; `Content.md` under
`reference/types/` must exist and have `type: "[[Type]]"` itself.

**The body** is everything after the closing `---`, parsed as CommonMark with
tables. Headings divide it into sections, nested by level; a paragraph or list
item may end in an Obsidian block id (`^seat`). Each type's schema fixes which
headings the body must have; anything the schema does not mention is free
Markdown.

**Templates** in `reference/templates/` are parsed but not validated, so their
placeholder values may break the rules. Copy one to start a record.

## Links

A wikilink names another file in the vault: `[[Quay Nine]]`,
`[[content/Quay Nine]]`, `[[Quay Nine.md]]`. The target is matched against
every trailing path of every file, case-insensitively and with `.md` optional,
so the shortest spelling that is unique works; when two files share a name,
spell enough of the path to tell them apart. A link may carry a display alias
(`[[Quay Nine|the quay]]`), a heading path (`[[S-1-002#Events]]`,
`[[Note#A#B]]`) or a block id (`[[The Bell Accord#^hearing]]`); `[[#Events]]`
points inside the same record, and `![[…]]` embeds. Every link, in frontmatter
or body, must resolve to exactly one file, and a heading or block anchor must
exist in the linked record. Links inside code are read as links too.

In frontmatter, links are **canonical**: `"[[target]]"` quoted, with no alias
or anchor. Fields that must link to a particular kind of record are checked
for it, and for scope: a *local* target must sit in the linking record's
campaign, or in shared `content/` when the target is Content.

| Record | Field | Must link to |
| --- | --- | --- |
| any | `type` | a Type record |
| any | `status` | a Status record whose `applies_to` names this record's type |
| Status | `applies_to` | a Type record |
| Content (PC) | `player` | a Player, local |
| Content (Location) | `parent_location` | Location Content, local |
| Content (Faction) | `members` | PC or NPC Content, local |
| Content | `campaign_N.first_session`, `campaign_N.last_session` | a Session in campaign N |
| Content (Object) | `campaign_N.held_by` | PC, NPC or Faction Content in campaign N |
| Player | `plays` | PC Content, local |
| Transcript | `session` | a Session, local |
| Clue | `text` (its links), `subjects` | Content, local |
| Clue | `first_session`, `last_session` | a Session, local |
| Clue | `superseded_by` | a Clue, local |
| Session | `campaign` | the containing campaign's `reference/Campaign.md` |
| Session | `players_absent` | Players, local |
| Session | `prepared_clues`, `prepared_locations`, `prepared_npcs` | Clues, Location Content, NPC Content, local |

A list field may not name the same file twice under different spellings. In a
Markdown table, a `|` inside a wikilink must be written `\|`, or the cell is
split. Links to non-record files (`[[harbor-pass.txt]]`,
`![[reference/views/clue-index.base#Active]]`) resolve like any other; their
anchors are not checked.

## Types, statuses and schemas

The type system lives in `reference/`:

- A **Type** record in `reference/types/` defines a type: its name is the
  filename, and its `directories` field says [where its records live](vault.md#where-records-live).
- A **schema**, `reference/schemas/<type>.schema.json`, validates each record
  of the type as `{frontmatter, body}` with JSON Schema draft 2020-12: the
  frontmatter as parsed, the body as one string. Every Type has a schema and
  every schema a Type. A record whose type has no schema is unsupported.
- A **Status** record in `reference/statuses/` defines a lifecycle state for
  one type, named in `applies_to`; a record's `status` must be one of them.
  The six shipped statuses apply to Clues.

Filenames carry identity for three types — Clues, Sessions and Transcripts
follow the patterns in [Vault layout](vault.md#where-records-live), and a
Session's `session_number` must match its filename — and the filename rules
there apply to all.
