# Developing Armarium

For contributors changing Armarium itself. Pull requests run the same checks
as the commands below; a release runs them all again before publishing.

## Setting up

From a checkout, create the development environment with
[uv](https://docs.astral.sh/uv/):

```sh
uv sync --extra dev
```

This installs Armarium in editable mode with its development tools in `.venv/`.
Run every command below through `uv run`, which uses that environment. To have
the checkout's `armarium` on your PATH outside the repository, install it as a
tool instead:

```sh
uv tool install --reinstall-package armarium .
```

## Tests

```sh
uv run python -m pytest -q
```

Tests marked `package` build the distributions and install the wheel in a fresh
environment, so they check what users install rather than the checkout. They
are slower, and CI runs them as a separate job:

```sh
uv run python -m pytest -q -m "not package"
uv run python -m pytest -q -m package
```

`tests/schemas/` tests the starter vault's JSON schemas and views on their own,
and runs in about a second:

```sh
uv run python -m pytest tests/schemas -q
```

Tests for `src/armarium/X.py` go in `tests/test_X.py`; [AGENTS.md](../AGENTS.md)
sets out how they are organised.

## Lint and type checks

```sh
uv run ruff format --check .
uv run ruff check .
uv run mypy --strict src
```

`uv run ruff format .` and `uv run ruff check --fix .` fix what they can.

## Validating the vaults

```sh
uv run armarium validate .
```

This validates the starter and example vaults, which must report no errors.

## Where things live

| Path | Holds |
| --- | --- |
| `src/armarium/` | the package: one module per command, with shared code in `lib.py`, `parse.py` and `index.py`, and checks in `validate.py` |
| `tests/` | the tests, with the schema tests in `tests/schemas/` |
| `vaults/starter/` | the vault `armarium init` copies; the wheel ships it as `armarium/starter` |
| `vaults/example/` | the starter vault with example records, used in tests and docs; only the source distribution ships it |
| `extensions/` | the bundled [extensions](extensions.md); the wheel ships them as `armarium/extensions` |
| `docs/` | these guides |

## Bumping the transcription models

Each week the `model-staleness` workflow compares the defaults in
`src/armarium/transcribe.py` with the Hugging Face listings of
`ggerganov/whisper.cpp` and `ggml-org/whisper-vad`. It flags a newer Silero
version or a higher `ggml-large-vN-turbo-q8_0.bin` by opening an issue, or
updating the open one. Run it at any time with:

```sh
gh workflow run model-staleness.yml
```

To bump a default, change its constant and add a CHANGELOG entry in a PR that
closes the issue. Leave the issue open until then: if it is closed with the
default unchanged, the next run opens another.

A failed run means the check itself broke: a listing could not be fetched, or no
longer holds the pinned default. The run opens an issue saying so, or updates
the open one. Close it once a run succeeds. The check cannot see a Whisper
generation that drops the `large-vN-turbo` naming.

GitHub turns off scheduled workflows after 60 days without repository activity,
and a run that never starts reports nothing. If the workflow has no recent runs
under the repository's Actions tab, enable it there again.

## Keeping the starter and example vaults in sync

The example vault is the starter vault plus records, kept up to date as any
vault is. Every file outside `content/`, `notes/`, `campaigns/`, `assets/` and
`.armarium/` must be the same, byte for byte, in both vaults, and
`tests/test_vaults.py` fails when one differs or is missing. After changing
`vaults/starter/`, bring the example vault up to date:

```sh
uv run armarium update --vault vaults/example
```

Then add or change example records where the change needs them. Until the
update, validation reports the example vault as out of date
(`vault.outdated`).

The example vault also enables the `example` extension, whose installed copy
lives in `vaults/example/reference/extensions/`. After changing
`extensions/example/`, refresh that copy:

```sh
uv run armarium extension update example --vault vaults/example
```

Until then, validation reports the copy as out of date (`vault.outdated`).
