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
