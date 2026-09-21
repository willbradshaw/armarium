# Two campaigns sharing one setting

All narrative material here is original test/example content. It is kept outside
the empty starter. Create an example at a fresh path, then overlay `content/`:

```sh
python3 scripts/create_vault.py /tmp/armarium-example --name "The Lantern Coast" \
  --campaign expedition "The Survey" --campaign homecoming "The Return"
cp -R examples/two-campaigns/content/. /tmp/armarium-example/
```

Open `/tmp/armarium-example` as an Obsidian vault. Start at Home, then inspect each
campaign's session index, the shared Old Observatory and Mira Vale pages, and the
clue indexes. A view-rendering checklist is in `docs/starter-vault.md` in Armarium.

The first campaign surveys a sealed observatory; years later, another campaign
visits its public reading room. Their shared entities retain separate histories.
An abandoned candidate passage clue is never asserted as true on the location page.
