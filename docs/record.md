# Records

Every Markdown file in a [vault](vault.md) is a record: YAML frontmatter that
declares its type, followed by a Markdown body. What every record shares is
below; each type's fields, body and rules are documented in [Types](type.md).

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
Keys must be unique strings and values representable in JSON, so dates are
written as `YYYY-MM-DD` strings. A record without frontmatter has no type and
is invalid. Fields beyond a type's schema are allowed on every type.

**`type`** is the one field every record must have: a canonical
[wikilink](#links) to the record's Type record, `[[types/Content]]` or
`[[Content]]`, with no alias or anchor. The last path segment names the type,
and `reference/types/Content.md` must exist.

**The body** is everything after the closing `---`: CommonMark with tables,
as Obsidian renders it. Headings divide it into sections, nested by level; a
paragraph or list item may end in an Obsidian block id (`^seat`). Each type
fixes which headings its body must have; the rest is free Markdown.

**Templates** in `reference/templates/` are starting points, not records:
their placeholder values need not follow the rules. Copy one to start a record.

## Links

Records link to each other with Obsidian
[internal links](https://help.obsidian.md/links): `[[Quay Nine]]`,
`[[Quay Nine|the quay]]`, `[[S-1-002#Events]]`, `[[The Bell Accord#^hearing]]`,
`![[…]]` to embed. Armarium adds these rules:

- Every link must resolve to exactly one file. A target matches any trailing
  part of a file's path, case-insensitively and with `.md` optional, so the
  shortest spelling that is unique is enough; when two files share a name,
  spell enough of the path to tell them apart.
- A heading or block anchor must exist in the linked record. Anchors on files
  that are not records (`![[reference/views/clue-index.base#Active]]`) are
  not validated.
- In frontmatter a link must be **canonical**: quoted, `"[[target]]"`, with no
  alias or anchor. A frontmatter field may not name the same file twice.
- Inside a Markdown table, a `|` within a link is written `\|` to avoid
  splitting the link between cells.

## Types, statuses and schemas

The type system lives in `reference/`:

- A **Type** record in `reference/types/` defines a type: its name is the
  filename, and its `directories` field says
  [where its records live](vault.md#where-records-live).
- A **schema**, `reference/schemas/<type>.schema.json`, describes each record
  of the type as `{frontmatter, body}` in JSON Schema draft 2020-12: the
  frontmatter as parsed, the body as one string. Every Type has a schema and
  every schema a Type.
- A **Status** record in `reference/statuses/` defines a lifecycle state for
  one type, named in `applies_to`. A record's `status` must be a Status whose
  `applies_to` is the record's type. The six shipped statuses apply to Clues.
