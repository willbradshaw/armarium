# Merging records

```sh
armarium merge --from "content/The Ninth.md" --into "content/Quay Nine.md" --vault ../my-vault
```

`armarium merge --from SOURCE --into TARGET` merges the [record](record.md)
`SOURCE` into `TARGET`, for two records that turn out to be one; it repoints every
[link](record.md#links) to `SOURCE` in the [vault](vault.md) and deletes
`SOURCE`. Merge records this way rather than by hand: a file deleted by hand
leaves every link to it broken.

## Choosing the records

Both flags are required, so the command always says which record goes and
which stays. `SOURCE` and `TARGET` are file paths, each chosen as for
[`armarium trace`](trace.md#choosing-the-file): without `--vault`, absolute or
relative to the current directory; with `--vault VAULT`, relative to the vault
root, so a path printed by [`armarium find`](find.md) can be passed as it is.
Make `TARGET` the record whose name you want to keep.

Both must be Content of one subtype, or both Notes; give them one subtype
first if they differ. `TARGET` must be visible wherever `SOURCE` was: shared,
or of the same campaign.

## Links to the source

Every link to `SOURCE` is repointed at `TARGET`, as a
[rename with `--alias`](rename.md#keeping-the-old-name) rewrites it: a body
link with no display alias keeps `SOURCE`'s name as its display text,
`[[The Ninth]]` becoming `[[Quay Nine|The Ninth]]`. A frontmatter list that
would then name `TARGET` twice, such as a Clue's `subjects` or a Faction's
`members`, keeps it once.

Links outside records, and Markdown links, are left as written and reported as
warnings, as [`armarium rename`](rename.md#links-left-as-written) reports
them. As with rename, [nothing is half done](rename.md#nothing-half-done):
every change is worked out before any file is written, and every file is put
back if writing one fails.

## What the merged record holds

| Part | Merged record |
| --- | --- |
| `aliases` | `TARGET`'s, then `SOURCE`'s, then `SOURCE`'s filename |
| a list, such as `content_tags` or `members` | `TARGET`'s items, then `SOURCE`'s that it lacks |
| any other field | the value both give; if one record leaves it out or empty, the other's |
| `first_session` and `last_session` | worked out from the merged Appearances |
| text before Notes, such as a callout | the text both give; if one record has none, the other's |
| Notes | `TARGET`'s, then `SOURCE`'s |
| Active Clues | `TARGET`'s, which lists the Clues about both |
| Appearances | both lists' items, in campaign and session order |
| a Note's body | `TARGET`'s, then `SOURCE`'s |

A field counts as empty when it is null, an empty string, an empty list or an
empty mapping. Every record's Active Clues holds the same Base embed, which
lists the Clues that link to the record, so `SOURCE`'s is dropped: once the
Clues about `SOURCE` are repointed, `TARGET`'s lists them too.

The merged record keeps `TARGET`'s order of fields and sections; a field or
section only `SOURCE` has is added. Read the merged Notes afterwards: the
command does not judge whether they repeat one another, and says so.

## Conflicts

Where the records disagree, only you can say which is right, so the command
lists each disagreement on standard output, one per line, and changes
nothing:

```text
summary: "A pilot of the eastern approaches." (--into) vs "A harbour clerk." (--from)
Appearances: both records have an item for S-1-002; keep one
```

Each line names the field or section where the records disagree, then what
disagrees; a differing value is shown from `TARGET` (`--into`), then from
`SOURCE` (`--from`).

Edit either record so that the two agree, or empty the field or section in
one of them, then merge again. The records conflict when:

- a field holds a different value in each, links compared by the file they
  name;
- both have an Appearances item for one Session, or an item that names no
  Session;
- the text before Notes, or a section other than Notes, Active Clues and
  Appearances, differs;
- both have a block with the same id;
- a link to `SOURCE` names a heading or block that the merged record lacks;
- a frontmatter link between the two would link the merged record to
  itself;
- one of `SOURCE`'s names is already another record's where `TARGET` is
  visible;
- an appearance falls in a campaign for which neither has a `campaign_N`
  block.

## Output

Each change is one line on standard output, with the four tab-separated fields
that [`armarium rename`](rename.md#output) prints:

```text
content/The Ninth.md			merged into content/Quay Nine.md
content/Quay Nine.md	aliases		merged from content/The Ninth.md
campaigns/campaign_1/sessions/S-1-002.md	Notes > Events	65	[[The Ninth]] → [[Quay Nine|The Ninth]]
```

Standard error then lists each file the command changes, and how many.
`--dry-run` checks the merge as a real run would and prints the same lines,
saying what would change, without changing anything.

The command exits with `0` once the records are merged, `1` when they
conflict or cannot be merged, and `2` for a usage error. Run
[`armarium validate`](validate.md) on the vault afterwards.
