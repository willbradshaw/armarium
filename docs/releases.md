# Releases

Every PR updates [CHANGELOG.md](../CHANGELOG.md), normally under `Unreleased`.

To prepare a release, update `version` in [pyproject.toml](../pyproject.toml),
rename the `Unreleased` heading to `VERSION (YYYY-MM-DD)`, and add a fresh
`Unreleased` heading above it. Merge the PR to create a draft GitHub release
whose text comes from that version's changelog section. The draft targets the
commit that triggered the workflow. The `draft-release` workflow can also be
run manually for the initial release or to retry draft creation.

Review and publish the draft on GitHub. The `publish` workflow checks out the
release tag, checks that it matches the package version, runs lint, type checks,
tests and vault validation, then builds and publishes to PyPI. Tags use the
package version without a `v` prefix, for example `0.1.0`.

## One-time setup

Create the GitHub Actions environment `pypi`. Configure a
[PyPI Trusted Publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
with these values:

| Field | Value |
| --- | --- |
| PyPI project | `armarium` |
| Repository owner | `willbradshaw` |
| Repository | `armarium` |
| Workflow | `publish.yml` |
| Environment | `pypi` |

No PyPI API token is needed. After publication, users can install with
`uv tool install armarium==0.1.0`.
