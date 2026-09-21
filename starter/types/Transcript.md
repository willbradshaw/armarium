Pages with `type: "[[types/Transcript]]"` are cleaned play-session transcripts, with speaker labels and content sections. Each links to its session through the session frontmatter field.

Use [[templates/Transcript]] in `campaign_N/transcripts/`, named
`S-N-NNN Transcript.md` for its session (for example, campaign 1's
`S-1-001 Transcript.md`). Replace the blank `session` property with a quoted,
vault-relative link such as `"[[campaign_1/sessions/S-1-001]]"`.

Write one cleaned, attributed utterance per line under meaningful `##` content
headings. Rename `Scene` to describe the content, add sections as needed, and
omit unused sections. The empty template contains no invented speech.

Use `[GM]` for the game master (generalizing the Isles source's `[DM]`), a PC
name such as `[Mira]` when known, `[Mira?]` when probable, `[Player?]` for
unattributed player speech, and `[Table]` for out-of-game talk worth keeping.
Mark uncertain hearings inline with `[?]`. Preserve uncertainty rather than
guessing a speaker or silently resolving unclear words.
