# Repository workflow

- Never commit or push directly to `main`.
- Make all changes, including planning and documentation, on a working branch
  and submit them through a pull request.
- The user reviews and merges pull requests; do not merge them on the user's behalf
  without explicit instruction.

# Testing conventions

- Cover every class, function, and method with dedicated tests, including private
  helpers and properties.
- Organize tests into classes named for the class, function, or method under test
  (for example, `TestParseWikilink` or `TestResultFailed`).
- Minimize redundant test code aggressively with `pytest.mark.parametrize`; share
  a test body when cases exercise the same behavior with different inputs.
