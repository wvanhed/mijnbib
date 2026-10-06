# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, Codex, Cursor,
etc.) when working with code in this repository.

## What this is

`mijnbib` is a Python library that provides an API for [bibliotheek.be](https://bibliotheek.be)
(the Flemish & Brussels public library network). It retrieves loans, reservations
and account info, and can extend loans. There is no official API — **all data is
obtained by web scraping**, so the code is tightly coupled to the structure of
the website's HTML and JSON responses. When the site changes, scraping breaks.

## Commands

Uses `uv` (package manager) and `make`. Common targets:

```bash
make init        # uv sync — install all dev dependencies
make dev         # format + lint + fast tests (the usual inner-loop command)
make all         # clean, init, mdlint, format, lint, full tests, build, biblist
make testfast    # pytest excluding `real` tests + doctests
make test        # full pytest (incl. `real` http tests) + doctests
make lint        # ruff check .
make format      # ruff import-sort + format (mutates files)
make formatcheck # non-mutating import-sort + format check (used in CI)
```

Tests are pytest. To run a subset directly:

```bash
uv run pytest -v                              # all
uv run pytest -k "not real"                   # skip tests hitting the live site
uv run pytest tests/test_parsers.py           # single file
uv run pytest -k "test_name_substring"        # single test by name
```

Tests marked `real` perform live HTTP requests to mijn.bibliotheek.be (see the
`real` marker in `pyproject.toml`); they are excluded from `testfast`/`make dev`.

**Doctests are part of the test suite** and must pass. `mijnbibliotheek.py`,
`parsers.py`, and `models.py` are run through `python -m doctest`. The docstrings
in the parser classes contain real HTML fixtures with expected parsed output —
when changing parsing logic, update these doctests too.

Running the CLI during development:

```bash
uv run mijnbib --version
uv run mijnbib loans          # reads credentials from mijnbib.ini if present
```

## Architecture

The public surface is re-exported from `src/mijnbib/__init__.py`. Users do
`from mijnbib import MijnBibliotheek, Loan, AuthenticationError, ...`.

**`MijnBibliotheek` (`mijnbibliotheek.py`) is the orchestrator/facade.** Its public
methods (`login`, `get_loans`, `get_reservations`, `get_accounts`, `get_all_info`,
`extend_loans`, `extend_loans_by_ids`) own a `requests.Session`, build the right
URLs, fetch pages, and delegate all HTML/JSON parsing to dedicated parser objects.
Methods auto-call `login()` if not yet logged in. The standalone `get_item_info()`
function fetches an item detail page (no session/login needed).

The flow of responsibilities:

- **Login** is delegated to a handler in `login_handlers.py`. `LoginByOAuth` performs
  bibliotheek.be's custom multi-redirect credential exchange (despite the OAuth-ish
  parameter names, it is *not* real OAuth — see the class docstring). The legacy
  `form` login option is removed; it is mapped to `oauth` with a
  `DeprecationWarning`.
- **Parsing** lives entirely in `parsers.py`. Each parser subclasses the `Parser`
  ABC and is built on BeautifulSoup: `LoansListPageParser`, `ReservationsPageParser`,
  `ExtendResponsePageParser`, `ItemDetailParser`. Account/membership data comes from
  JSON endpoints (`/api/my-library/...`) and is parsed by `_parse_api_memberships()`
  inside `mijnbibliotheek.py`, which handles two different JSON shapes (region-based
  vs. library-based) depending on the library system.
- **Models** (`models.py`) are plain dataclasses (`Loan`, `Reservation`, `Account`,
  `ItemInfo`). Their fields mirror what the website exposes rather than a normalized
  schema. Note: a `Loan` has no unique loan ID — identify a loan by the combination
  of item `id` + `loan_from` + `account_id`. `Reservation` has no ID at all
  (use `url`).
- **Errors** (`errors.py`) all derive from `MijnbibError`. Parsing failures raise
  `IncompatibleSourceError` (which carries the offending `html_body` for debugging);
  transient site failures raise `TemporarySiteError`; bad credentials raise
  `AuthenticationError`. Scraping/parsing code catches broad exceptions and re-raises
  as these typed errors so callers have a stable contract even as the site shifts.
- **CLI** (`cli.py`, invoked via `__main__.py`) is a thin argparse wrapper over `MijnBibliotheek`.
  It reads defaults from a `mijnbib.ini` file (`[DEFAULT]` section) so
  credentials need not be passed on the command line.

### Key parsing conventions

- Parsers are defensive: nearly every field is wrapped in try/except so a
  missing or changed element degrades to a default (empty string / `None`) plus
  a `_log.warning`, rather than crashing the whole parse. Preserve this style
  when editing parsers.
- Loan extension success is genuinely ambiguous from the server's responses
  (it often returns HTTP 500 even on partial success). `extend_loans()` combines
  the HTTP status with parsed page content to *guess* success — read its
  docstring before touching it.
- `extend_loans`/`extend_loans_by_ids` take an `execute` flag that defaults to `False`
  (simulation/dry-run); real extension only happens when `execute=True`.

## Conventions

- Linting/formatting is `ruff` (line length 95). Config and the enabled rule
  set (bugbear, security/bandit `S`, naming, pytest, pathlib, no-print `T2`,
  etc.) are in `pyproject.toml`. Run `make format` before committing.
- `print()` is disallowed by lint everywhere except `cli.py` (file-level
  `noqa`), `examples/` and `tests/` (per-file ignores). In library code, use
  `_log` instead.
- `libraries.md` is generated by `update_biblist.py` (via `make biblist`) — do not
  hand-edit it.

## Releasing

See the "Development" section of `README.md`. In short: update `changelog.md`
(uncommitted), run `make all`, then `uvx uv-ship next patch` (bumps version, tags,
pushes), then `make publish`, then create the GitHub release from the tag.
