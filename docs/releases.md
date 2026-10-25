# Releases

Every PR updates [CHANGELOG.md](../CHANGELOG.md), normally under `Unreleased`.

To prepare a release, update `version` in [pyproject.toml](../pyproject.toml),
rename the `Unreleased` heading to `VERSION (YYYY-MM-DD)`, and add a fresh
`Unreleased` heading above it. Merge the PR to create a draft GitHub release
whose text comes from that version's changelog section. The draft targets the
commit that triggered the workflow. The `draft-release` workflow can also be
run manually to retry draft creation.

Changes to `pyproject.toml` or `CHANGELOG.md` trigger the workflow. It skips
draft creation unless the changelog has a versioned heading matching the package
version, and skips versions that already have a GitHub release. PR titles do
not affect release creation.

Review and publish the draft on GitHub. The `publish` workflow checks out the
release tag, checks that it matches the package version, runs lint, type checks,
tests and vault validation, then builds and publishes to PyPI. Tags use the
package version without a `v` prefix, for example `0.1.0`.

## What a version promises

From 1.0, versions follow [semantic versioning](https://semver.org/). A
breaking change, which needs a new major version, is one that makes a valid
vault invalid or a working script fail: removing or renaming a type, field,
vault folder, command or option; changing a command's tab-separated output, the
layout of validation findings, a rule ID or an exit status; or adding a check
that fails records the previous version accepted. New types, optional fields
and options are not breaking, nor are new warnings or changes to message
wording and log lines. Armarium's Python modules are not a public interface and
may change in any release. Within a major version, `armarium update` and
`armarium extension update` bring a vault up to date without edits to its
records; a major version's changelog lists the record edits it requires.
