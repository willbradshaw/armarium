# Command line

`armarium` is the package's command. It has one subcommand, `validate`, which
runs [validation](validate.md) over a path and prints its findings.

## Installation

With Python 3.14 or later, from a checkout of this repository:

```sh
python -m pip install .
```

This installs the `armarium` command on your path.

## `armarium validate`

```text
armarium validate [--vault VAULT] PATH
```

- `PATH` is a record, a directory inside a vault, a vault root, or a
  directory containing vaults; [Validation](validate.md#scope) says what each
  gets.
- `--vault VAULT` names the vault explicitly. Without it the vault is the
  nearest directory above `PATH` containing `reference/types/` and
  `campaigns/`; a single record outside any vault cannot be validated without
  it.
- `--help` prints the usage.

Findings, the counts line and, on failure, a final `ERROR: N files failed
validation` line go to standard error in the
[documented format](validate.md#output); nothing goes to standard output,
and nothing is modified. The exit status is `0` when every record passed,
`1` when any record has an error, and `2` for a usage error such as a
missing `PATH`.

```sh
armarium validate .                                    # the vault in the current directory
armarium validate campaigns/campaign_1/clues           # every Clue of one campaign
armarium validate content/Port\ Briselle.md            # one record
armarium validate ~/notes/quay.md --vault ~/setting    # a record, naming its vault
```
