# Contributing to `lg2m`

Thanks for your interest in `langgraph_to_from_mermaid`. This is a pre-alpha project under
active development on `main`. The design is settled in [`docs/design.md`](docs/design.md); read it (and
[`CLAUDE.md`](CLAUDE.md) for the architecture) before a substantial change.

## 1. Open an issue first

Every change starts with an issue:

- **Bug report:** what you ran, what you expected, what happened, and the Python /
  LangGraph versions involved.
- **Feature request:** the problem you want solved and, if you can, how it fits the design
  in `docs/design.md`. The roadmap in the README is the natural first-issues list.

Open the issue before sending a pull request, so the work can be discussed and is not
duplicated.

## 2. Local setup

Requires Python 3.10 or newer.

```bash
git clone https://github.com/psenger/langgraph_to_from_mermaid.git
cd langgraph_to_from_mermaid
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"                # foundation layer: stdlib only + pytest/ruff
# pip install -e ".[langgraph,dev]"    # add the framework, for introspector work
```

Run the checks before every push:

```bash
python -m pytest -q       # the suite must pass; enforces the 90% coverage gate
ruff check src tests      # the lint must be clean
```

`tests/conftest.py` adds `src/` to `sys.path`, so the suite runs even without the editable
install, but installing is recommended. To run a single file or test, add `--no-cov` so the
coverage gate does not trip on the partial run, e.g.
`python -m pytest tests/test_router.py --no-cov -q`.

## 3. Branch and pull request

`main` is the development branch and the source of every release.

1. Cut a branch from `main` (one branch per issue, e.g. `fix/<issue>-short-slug` or
   `feat/<issue>-short-slug`).
2. Make the change with tests, keep the diff focused, and follow the standards below.
3. Open a pull request **against `main`** and link the issue it closes.

A PR is ready when the suite passes, `ruff check src tests` is clean, and every changed
line traces to its issue. Keep PRs small and reviewable.

**Only the maintainer merges to `main`.** `main` is protected: contributors open PRs and
the maintainer ([@psenger](https://github.com/psenger)) reviews and merges. Please do not
push directly to `main`.

## 4. Coding standards

- The package is **framework-free** except the (future) LangGraph introspector. Importing
  `lg2m` must not import `langgraph` or `langchain_core`; only
  `introspect/langgraph_adapter.py` may, behind the `[langgraph]` extra. Do not add a
  framework import anywhere else.
- Match the existing style: `from __future__ import annotations`, `X | None` unions, frozen
  dataclasses for the IR, and the identity rules documented in `ir.py`.
- The project is written against the standards in [`agent-os/standards/`](agent-os/standards/)
  (SOLID, clean code, TDD). New behaviour comes with tests; see [`docs/design.md`](docs/design.md)
  Section 14 for the test strategy.
- **Coverage standard:** the suite enforces a **90%** line-coverage gate on the `lg2m`
  package, configured in `pyproject.toml` (`addopts = "--cov=lg2m --cov-report=term-missing
  --cov-fail-under=90"`). This raises the 80% baseline in
  [`agent-os/standards/testing/testing.md`](agent-os/standards/testing/testing.md). `python
  -m pytest` runs it automatically (currently ~95%); a change must not drop the total below
  90%, and should cover error paths, not just the happy path.
- `ruff` is configured in `pyproject.toml` (line length 100, rules `E,F,I,UP,B`). Lint
  `src` and `tests`; the files under `examples/` import the frameworks on purpose and are
  not part of the lint target.

## 5. Releases and publishing (maintainer only)

Releases are cut from `main` as Git tags and GitHub Releases, and the package is published
to [PyPI](https://pypi.org/) under the name `langgraph-to-from-mermaid`. Anyone can then
install it with `pip install langgraph-to-from-mermaid`. The build backend is `hatchling`
and the version is the static `version` field in `pyproject.toml`.

### 5.1 One-time setup

**Install the build tools** (do this once, outside the project venv if you prefer):

```bash
pip install build twine
```

**Create a PyPI API token** (do this once per account):

1. Log in to [pypi.org](https://pypi.org) and go to Account Settings > API tokens.
2. Click "Add API token", give it a name (e.g. `lg2m-publish`), scope it to this project
   once the project exists on PyPI (first upload must use an account-scoped token).
3. Copy the token immediately; PyPI will not show it again.
4. Store it in `~/.pypirc` so `twine` picks it up automatically:

   ```ini
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   username = __token__
   password = pypi-<your-token-here>

   [testpypi]
   username = __token__
   password = pypi-<your-test-token-here>
   ```

   Set permissions so only your user can read it: `chmod 600 ~/.pypirc`.

You also need a **TestPyPI** account and token for staging (see section 5.3). Register at
[test.pypi.org](https://test.pypi.org) (separate account from PyPI) and repeat the token
steps above.

### 5.2 GitHub-only release (alpha / pre-release)

Use this path for alpha and pre-release versions. No PyPI account or build tooling
required; users install directly from the tagged commit (see [Installation](README.md)).

**Version format:** PEP 440 pre-release suffixes — `a1`, `a2` (alpha), `b1` (beta),
`rc1` (release candidate) — appended to the base version, e.g. `0.1.0a1`.

Run the checks:

```bash
source .venv/bin/activate
python -m pytest -q          # all tests must pass, coverage >= 90%
ruff check src tests         # lint must be clean
```

Then:

1. **Bump the version** in `pyproject.toml`:
   ```toml
   version = "0.1.0a1"
   ```
2. **Commit and tag:**
   ```bash
   git add pyproject.toml
   git commit -m "chore: bump version to 0.1.0a1"
   git tag v0.1.0a1
   git push origin main
   git push origin v0.1.0a1
   ```
3. **Create the GitHub Release** with `gh`:
   ```bash
   gh release create v0.1.0a1 \
     --title "v0.1.0a1 — alpha" \
     --notes "Alpha release. Install with:
   pip install git+https://github.com/psenger/langgraph_to_from_mermaid.git@v0.1.0a1" \
     --prerelease
   ```
   The `--prerelease` flag marks it correctly on GitHub and signals to users that this
   is not a stable release. Adjust `--title` and `--notes` for each release.

Users install the tagged version with:

```bash
pip install "git+https://github.com/psenger/langgraph_to_from_mermaid.git@v0.1.0a1"
# with the langgraph extra:
pip install "langgraph-to-from-mermaid[langgraph] @ git+https://github.com/psenger/langgraph_to_from_mermaid.git@v0.1.0a1"
```

### 5.3 Release checklist (PyPI)

Run this before every PyPI publish:

```bash
source .venv/bin/activate
python -m pytest -q          # all tests must pass, coverage >= 90%
ruff check src tests         # lint must be clean
```

Then:

1. **Bump the version** in `pyproject.toml` (`version = "X.Y.Z"`). The project follows
   `MAJOR.MINOR.PATCH` (semver). While in pre-alpha, increment the patch for every
   release.
2. **Commit the version bump** on `main`:
   ```bash
   git add pyproject.toml
   git commit -m "chore: bump version to X.Y.Z"
   ```
3. **Tag the commit** and push the tag:
   ```bash
   git tag vX.Y.Z
   git push origin main
   git push origin vX.Y.Z
   ```
4. **Create a GitHub Release** from that tag:
   ```bash
   gh release create vX.Y.Z \
     --title "vX.Y.Z" \
     --notes "Paste changelog notes here."
   ```

### 5.4 Build and stage on TestPyPI first

Always do a dry run on TestPyPI before touching production.

```bash
# Remove any stale build artifacts
rm -rf dist/

# Build source distribution and wheel
python -m build
# Produces: dist/langgraph_to_from_mermaid-X.Y.Z.tar.gz
#           dist/langgraph_to_from_mermaid-X.Y.Z-py3-none-any.whl

# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Verify the install from TestPyPI in a throwaway venv
python3 -m venv /tmp/test-lg2m && source /tmp/test-lg2m/bin/activate
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            langgraph-to-from-mermaid
python -c "import lg2m; print(lg2m.__version__)"
deactivate
rm -rf /tmp/test-lg2m
```

The `--extra-index-url` is needed because TestPyPI does not mirror all of PyPI's
dependencies; it lets pip fall back to the real index for packages like `typer`.

### 5.5 Publish to PyPI (production)

Once TestPyPI looks correct:

```bash
twine upload dist/*
```

Verify the live page at `https://pypi.org/project/langgraph-to-from-mermaid/` and do a
final sanity check:

```bash
python3 -m venv /tmp/check-lg2m && source /tmp/check-lg2m/bin/activate
pip install langgraph-to-from-mermaid
python -c "import lg2m; print(lg2m.__version__)"
deactivate
rm -rf /tmp/check-lg2m
```

### 5.6 Future: Trusted Publishing (GitHub Actions)

Once the CLI ships, the preferred path is PyPI
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/): a tagged GitHub Actions
workflow authenticates via OIDC and uploads the build automatically, so no API token ever
lives on a laptop. The manual `twine` flow above is the fallback until that workflow is
wired up.

Once `cli.py` and its `[project.scripts]` entry land, installing the published package
puts the `lg2m` command on the user's `PATH`.
