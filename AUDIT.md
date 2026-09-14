# AUDIT.md — Clipbaa Scrapers Enterprise Pipeline

> Local filesystem audit of the `scrapers/` package in `/data/data/com.termux/files/home/clipbaa`.
> Read-only audit: **no source files were modified**. Deliverable is this report only.
> Every issue records: file, function/class, problem, severity, why it matters, recommended fix.

---

## 1. Executive Summary

The `scrapers/` package is a well-structured, pure-Python core (config, IO, metrics, errors,
registry, schemas, matching, reporting) with an optional `scrapling[fetchers]` live layer. Mock
mode works end-to-end: `python3 -m pytest scrapers/tests -q` → **88 passed**, and a full mock
E2E run produced coherent artifacts (`data/runs/20260914T155012Z/manifest.json`, 21 marketplace
products, 17 candidates, 15 winners, 4 near-misses).

However, the package is not release-ready:

- **Critical:** every live-scraper module (`sources/amazon.py`, `meesho.py`, `flipkart.py`,
  `deodap.py`) uses names (`Request`, `Response`, `AsyncStealthySession`, `Any`) that are never
  imported. On Python 3.10–3.13 (the documented `requires-python = ">=3.10"`) these modules raise
  `NameError` at import, so **the CLI does not run on any Python below 3.14**; on 3.14 the modules
  only load because annotations are lazily evaluated, and live mode would `NameError` at runtime
  even with scrapling installed. No test exercises any live path.
- **Critical:** there is no CI for the scrapers package. `.github/workflows/tests.yml` still runs
  the *deleted* SupoClip `backend/`/`frontend/` jobs and pins Python 3.11 — the one major version
  most likely to break. The documented test/lint guarantees have no automated gate.
- **High:** scoring maths distort results — the velocity component of `opportunity_score` is
  fabricated from data no spider collects (constant ~50%), and one fee model (15% referral + flat
  closing/shipping) is applied to Amazon, Meesho and Flipkart, which have materially different fee
  structures.
- **High:** operator docs are stale: `README.md` documents deleted modules
  (`python -m scrapers.pipeline`, `scrapers.matcher`, …), `FIND_ASINS.md` points at a non-existent
  path (`/workspaces/...`) and a `scrape_asins` module that no longer exists, and the root
  `.env.example` documents the entire deleted SupoClip video app with none of the scrapers' settings.
- **Medium/Low:** dead config (`deodap_max_pages` never reaches the spider), dead blocking
  subsystem (never wired), full-file history rewrites, un-packaged `seed_asins.json`, stale
  run artifacts depending on CWD, no flake8 config, and 144 flake8 violations even under the
  plan's own `--max-line-length=100`.

The highest-value next steps are (1) import the missing scrapling names behind guards and add a
stubbed live-path test, (2) add a real scrapers CI job, (3) fix docs to match the shipped CLI,
and (4) make the scoring inputs honest (per-marketplace fees, real velocity data).

## 2. Scope, Method, Environment & Tooling

- **Scope:** the `scrapers/` package (package name `scrapers`, console script `pipeline`), plus
  repo-root integration files (`.env.example`, `.github/workflows/tests.yml`, `.gitignore`),
  run artifacts under `data/`, and design/plan docs under `docs/superpowers/`.
- **Method:** read-only inspection of the local working tree in this order — repo tree → project
  docs (`README.md`, `FIND_ASINS.md`, `pyproject.toml`, `requirements.txt`) → core modules
  (`config`, `errors`, `io`, `logging_setup`, `metrics`, `parsing_utils`, `registry`, `schemas`,
  `cli`) → `matching/*` → `reporting/*` → `sources/*` → environment/docs/tests → design spec and
  implementation plan → data artifacts and run manifests → test suite execution → static checks.
- **Environment:** OS `linux` (Termux/aarch64), CPython `3.14.6`, `pytest 9.1.1`,
  `flake8 7.3.0`, `python-dotenv` installed, `scrapling` **not** installed (so live-scraping
  execution and `gspread`/Sheets execution could not be exercised locally; tests cover the
  documented mock/guard behavior instead).
- **Verification run:** step 15 — `python3 -m pytest scrapers/tests -q` → `88 passed in 1.92s`.
  Step 16 — `flake8` (both default 79-col and the plan's 100-col): not clean (details in
  Sections 4 & 19).

## 3. Repository Snapshot & Version Control Health

- Git `HEAD` = `0efec75 feat(scrapers): add enterprise matching, reporting, CLI orchestrator, and tests`;
  history is the scrapers-reorg built on the old **SupoClip** monorepo.
- `git status` shows large **uncommitted deletions** of the legacy app (`backend/`, `frontend/`,
  `docs/*.md`, `README.md`, `CONTRIBUTING.md`, `LICENSE`, `Makefile`, …). The working tree is
  thus not committable as one clean change.
- Tracked data files modified by the mock run: `data/amazon_movers_raw.json` (M),
  `data/deodap_catalog_raw.json` (M), `data/matched_products.{json,csv}` (M), `data/near_matches.json` (M).
- Untracked run outputs: `data/flipkart_bestsellers_raw.json`, `data/meesho_trending_raw.json`.
  Root `.gitignore` covers `data/runs/`, `data/products.jsonl`, `winners.md`, `matched_products.*`,
  `near_matches.json`, but **not** the raw `data/*_raw.json` files.
- The second run directory `scrapers/data/runs/20260914T162748Z/` contains only an empty
  `run.log` and no manifest — evidence of a live-mode attempt without scrapling, which exits 4 via
  `DependencyError` before any source completes (CWD-sensitive output, see F11/F18).

**Issues:** F13 (git hygiene), F18 (CWD-dependent outputs), F20 (raw files not gitignored).

## 4. Issue Index (master register)

| ID | Severity | Title | File(s) | Section |
|----|----------|-------|---------|---------|
| F1 | CRITICAL | Undefined scrapling names break import on 3.10–3.13 and live mode everywhere | `sources/{amazon,meesho,flipkart,deodap}.py` | 5 |
| F2 | CRITICAL | No CI for scrapers; `.github/workflows/tests.yml` is stale (deleted dirs, py3.11) | `.github/workflows/tests.yml` | 5 |
| F3 | HIGH | README documents deleted modules/commands; thresholds mismatch config & run | `scrapers/README.md` | 7 |
| F4 | HIGH | FIND_ASINS.md wrong path/command; `run --live` never uses seed ASINs | `FIND_ASINS.md`, `sources/amazon.py` | 7 |
| F5 | HIGH | Opportunity-score velocity component is fabricated constant | `matching/matcher.py`, `matching/scoring.py` | 7 |
| F6 | HIGH | Single 15%-referral fee model for all marketplaces distorts margins/ROI | `matching/scoring.py` | 7 |
| F7 | MEDIUM | `seed_asins.json` not declared as package data; absent from built SOURCES | `pyproject.toml`, `sources/amazon.py` | 8 |
| F8 | MEDIUM | `deodap_max_pages` (Settings) is dead; spider re-reads env directly | `config.py`, `sources/deodap.py` | 8 |
| F9 | MEDIUM | Live partial failures reuse stale raw files → silent stale winners | `cli.py` `run_pipeline` | 8 |
| F10 | MEDIUM | Blocked-detection subsystem is dead code; metrics "blocked" unreachable | `sources/base.py`, `metrics.py`, `cli.py` | 8 |
| F11 | MEDIUM | History append rewrites whole file; `lookback_days` unused; O(n) scans | `matching/history.py` | 8 |
| F12 | MEDIUM | No `.env` template / documented env reference for scraper settings | `.env.example` (root) | 8 |
| F13 | MEDIUM | Uncommitted mass deletion; tracked data churn in tree | repo root | 8 |
| F14 | LOW | `scrape-asins` untested, seed write path fragile in installed wheels | `cli.py` `_cmd_scrape_asins` | 8 |
| F15 | LOW | Lint not clean (113 + 31 even at `--max-line-length=100`); plan gate unmet | whole tree | 8 |
| F16 | LOW | No flake8 config pins style/line length; default 79 col unusable | repo root | 8 |
| F17 | LOW | Test coverage gaps (no live/blocking/scrape-asins/export success paths) | `scrapers/tests/` | 8 |
| F18 | LOW | Outputs land in CWD (`data/`) — run artifacts + empty run.log from cwd runs | `cli.py`, `io.py` | 8 |
| F19 | LOW | `post_webhook` swallows HTTPError status; redaction otherwise sound | `reporting/webhook.py` | 8 |
| F20 | LOW | Raw `data/*_raw.json` outputs not gitignored; `requirements.txt` is comment-only stub | `.gitignore`, `requirements.txt` | 8 |
| F21 | LOW | Schema fallback silently applies marketplace rules to unlabeled records; None→0 coercion | `schemas.py` | 8 |
| F22 | LOW | Stale `.pytest_cache` references removed test; `test_package.py` minimal | `scrapers/tests/` | 8 |

## 5. Findings — CRITICAL

### F1 — Undefined scrapling names break import on Python 3.10–3.13 and break live mode on every version

- **File:** `scrapers/scrapers/sources/amazon.py`, `meesho.py`, `flipkart.py`, `deodap.py`
- **Function/class:** `AmazonMoversSpider.configure_sessions` (L342 `AsyncStealthySession(...)`),
  `start_requests` (L356 `Request(...)`), `parse_list`/`parse`/`parse_product`/`_parse_product`
  (L358/L378/L415/L419/L437 `Response`/`Any` annotations), `SeedAsinsSpider.start_requests`
  (L516 `Request(...)`); `MeeshoSpider.configure_sessions` (L145 `AsyncDynamicSession(...)`),
  `start_requests`/`parse_trending`/`parse_product`/`_parse_product` (L158–192 `Request`/`Response`);
  `FlipkartSpider.configure_sessions` (L156), `start_requests`/`parse_bestsellers`/`_parse_product`
  (L170–204); `DeodapSpider.configure_sessions` (L309 `FetcherSession(...)`),
  `start_requests`/`parse_category`/`parse_product`/`_parse_product` (L323–366 `Request`/`Response`).
- **Problem:** `base.py` alone guards the scrapling imports (falling back to `Request = Any`,
  `Response = Any`, `AsyncStealthySession = Any`, …). The four leaf modules import only
  `MarketplaceSpider` (and in *some* files one session class) from `base`; `Request` and `Response`
  are **never** imported anywhere in them. `amazon.py` also uses `Any` (L378) without importing it
  and `AsyncStealthySession` (L342) without importing it. flake8 reports **28 `F821 undefined name`**
  errors in exactly these files. Verified at runtime on Python 3.14:
  `inspect.signature(AmazonMoversSpider.parse_list)` → `NameError: name 'Response' is not defined`.
- **Severity:** CRITICAL
- **Why it matters:**
  1. `pyproject.toml` declares `requires-python = ">=3.10"`. On 3.10–3.13 function annotations are
     evaluated eagerly at class-body execution, so `import scrapers.sources.amazon` (via
     `scrapers.sources`, via `scrapers.cli`) raises `NameError` — the whole `pipeline` CLI is
     **unusable on every supported Python except 3.14**, where it only works by accident of
     deferred annotation evaluation (PEP 649).
  2. Even on 3.14 with `scrapling[fetchers]` properly installed on a glibc host, the live paths
     crash: `configure_sessions` and `start_requests` *call* names that were never imported →
     `NameError` at crawl time. Live scraping is broken by construction.
  3. No test imports/exercises any of these methods, so the breakage is invisible to the suite.
- **Recommended fix:** import `Request`, `Response`, and the session classes from `scrapers.sources.base`
  in each leaf module (they already resolve to `Any` fallbacks when scrapling is missing); add
  `from __future__ import annotations` as a safety net for annotations; add a unit test that
  subclasses/stubs `Request`/`Response` and drives `start_requests`/`parse_list`/`parse_product`
  against canned DOM to cover the live path without a browser.

### F2 — No CI for the scrapers package; existing workflow tests a deleted app on Python 3.11

- **File:** `.github/workflows/tests.yml`
- **Function/class:** jobs `backend`, `frontend`, `e2e` (steps `cd backend && ...`,
  `cd frontend && ...`; services postgres/redis; env `DATABASE_URL=postgresql+asyncpg://...`)
- **Problem:** the workflow is the SupoClip-era file. Every job steps into `backend/` or
  `frontend/`, which are deleted from the working tree; it pins `python-version: "3.11"` (a
  version on which F1 breaks imports); there is **no job for `scrapers/`** at all.
- **Severity:** CRITICAL
- **Why it matters:** the project's single CI gate cannot pass and cannot be triggered by
  `scrapers/` changes. The entire test/lint verification burden falls on a human; regressions
  like F1 go to production silently. The workflow as-is is actively misleading (green-bar myth).
- **Recommended fix:** replace with a `scrapers` job: checkout → `setup-python` matrix
  (`"3.11"` **and** `"3.14"` — forcing the portability bug to surface) → `pip install -e ".[dev]"`
  → `python3 -m pytest scrapers/tests -q` → `flake8` with an explicit config file (see F16);
  drop the backend/frontend/e2e jobs for the deleted app.

## 6. Findings — (none graded CRITICAL beyond 5; see 7)

## 7. Findings — HIGH

### F3 — README.md documents deleted modules and contradicts shipped CLI config

- **File:** `scrapers/README.md`
- **Function/class:** whole document — `Installation`, `Quick Start`, `Environment variables`,
  `Thresholds for Action`
- **Problem:** quick start uses `python -m scrapers.pipeline`, `python -m scrapers.amazon_movers_spider`,
  `python -m scrapers.matcher` — all deleted in the reorg (Task 0); the env table does not list the
  actual `Settings` keys (`SCRAPLING_ALLOW_MOCK_FALLBACK`, `LOG_LEVEL`, `LOG_FORMAT`, `OUTPUT_DIR`,
  `MIN_*`, `MAX_*`, `REPORT_TOP_N`, `SHEETS_*`, `WEBHOOK_*`); `Installation` tells users to
  `pip install -r requirements.txt`, but that file is a comment-only stub (F20). "Thresholds for
  Action" (₹40 margin / 65% confidence / 65 opportunity / …) contradict code defaults in
  `config.py` (₹200 / 0.5 / 200) and the actual E2E run manifest (`min_absolute_margin: 80.0`,
  `min_ticket_price: 100.0`).
- **Severity:** HIGH
- **Why it matters:** three mutually inconsistent sources of truth for thresholds; any operator
  following the README hits `ModuleNotFoundError`. This is the user-facing surface of the product.
- **Recommended fix:** rewrite `Quick Start` to the real CLI (`pipeline --output-dir data run --mock`,
  `pipeline run --live`, `pipeline match|history|export|list-sources|validate-config|scrape-asins`),
  document the full settings surface (pointing at `scrapers/scrapers/config.py`), fix `Installation`
  to `pip install -e ".[dev]"` / `".[fetchers]"`, and delete or reconcile `Thresholds for Action`
  with the code defaults. This was plan Task 20, Step 1 and was **not** delivered.

### F4 — FIND_ASINS.md references non-existent paths/modules and mis-describes the seed flow

- **File:** `scrapers/FIND_ASINS.md`; `scrapers/scrapers/sources/amazon.py` (`SEED_FILE` L298,
  `load_seed_asins` L311, `AmazonMoversSpider.start_requests` L354)
- **Function/class:** doc commands; `AmazonMoversSpider`
- **Problem:** documents `/workspaces/clipbaa/scrapers/seed_asins.json` (actual:
  `scrapers/scrapers/sources/seed_asins.json`) and `python -m scrapers.scrape_asins`
  (actual: `pipeline scrape-asins`). It claims `pipeline run --live` "will use your seed ASINs
  instead of mock data" — **false**: `AmazonMoversSpider.start_requests` crawls the hardcoded
  `BESTSELLERS_URLS`; seed ASINs are read only by `scrape-asins` and the standalone `SeedAsinsSpider`.
- **Severity:** HIGH
- **Why it matters:** operators will trust the doc and either edit the wrong file or expect
  seed-driven crawls that never happen; the seed list (5 ASINs) is effectively dead weight in
  `pipeline run`.
- **Recommended fix:** update path/command to real values (plan Task 20, Step 2 — not delivered);
  either wire seeds into `start_requests` (append seed ASIN enrichment to the bestsellers crawl) or
  clearly document that seeds are only used by `pipeline scrape-asins`.

### F5 — Opportunity-score velocity component is fabricated from data no spider collects

- **File:** `scrapers/scrapers/matching/matcher.py` (`_score_match` L134–139),
  `scrapers/scrapers/matching/scoring.py` (`velocity_score` L116–119)
- **Function/class:** `DeodapMatcher._score_match`, `velocity_score`
- **Problem:** no spider emits `bsr_30d_avg`. The matcher therefore computes
  `bsr_avg = (bsr_current or 10000) * 2`, giving `velocity = (bsr_avg - bsr_current) / bsr_avg * 100
  = 50%` for **every** product (amazon and non-amazon alike: non-amazon `bsr_current` defaults to
  10000). The 20%-weighted velocity component of `opportunity_score` is thus a constant +10 added
  to all candidates — it ranks nothing and inflates every score.
- **Severity:** HIGH
- **Why it matters:** "Velocity: % BSR drop over 30 days" (READEME F3) is not actually
  computed; opportunity scores and the derived winners list are partially arbitrary; decisions
  (which SKUs to stock) rest on a fabricated input.
- **Recommended fix:** collect a real 30-day average (second product-page pass or `history`
  aggregation over BSR snapshots) or remove the velocity term until a real signal exists and
  document that; alternatively use `review_velocity_30d` (already scraped on amazon) as a proxy
  and be explicit about the substitution.

### F6 — One fee model for three marketplaces distorts margins, ROI and winners

- **File:** `scrapers/scrapers/matching/scoring.py` (`calculate_margin` L84–103)
- **Function/class:** `calculate_margin`
- **Problem:** flat 15% referral fee for Amazon, Meesho and Flipkart alike, plus flat closing fee
  (₹5 ≤250 / ₹10 >250) and flat shipping tiers, plus 18% GST on fees and 18% GST on DeoDap cost
  (`deodap_cost * 1.18`). Amazon.in referral fees are category-tiered (~5–20%), Flipkart differs,
  and Meesho charges no referral on many listings. GST is applied to the cost regardless of whether
  the cost is already GST-inclusive.
- **Severity:** HIGH
- **Why it matters:** net margin and ROI are the core "why this is a winner" signal; a wrong fee
  model will both over-reject unprofitable-looking Amazon/Flipkart items and under-reject Meesho
  items, and the printed ₹ margins in `winners.md`/`matched_products.csv` do not reflect what lands
  in the account.
- **Recommended fix:** per-marketplace fee calculators: Amazon.in category-tier referral + closing +
  weight-based shipping; Flipkart fee schedule; Meesho (0%/low referral); make GST-on-cost an
  explicit input/flag; document assumptions in code and README.

## 8. Findings — MEDIUM

### F7 — `seed_asins.json` is not declared as package data

- **File:** `scrapers/pyproject.toml`, `scrapers/scrapers/sources/amazon.py` (`SEED_FILE` L298)
- **Problem:** no `[tool.setuptools.package-data]`; `scrapers.egg-info/SOURCES.txt` does not list
  `scrapers/sources/seed_asins.json`. Built wheels/sdists will omit it.
- **Severity:** MEDIUM
- **Why it matters:** after `pip install .` (non-editable) `load_seed_asins()` returns `[]` (guarded,
  so silent) and `_cmd_scrape_asins` attempts an `atomic_write_json` into site-packages — the seed
  workflow breaks in deployed installs while working in a source checkout.
- **Recommended fix:** add
  `[tool.setuptools.package-data]\nscrapers = ["sources/*.json"]` (or `include-package-data = true`
  + MANIFEST.in) and verify the wheel contains the file.

### F8 — `deodap_max_pages` setting is dead; spider re-reads env directly

- **File:** `scrapers/scrapers/config.py` (L94, L143), `scrapers/scrapers/sources/deodap.py`
  (L282 `MAX_COLLECTION_PAGES = int(os.environ.get("DEODAP_MAX_PAGES", "3"))`)
- **Function/class:** `Settings.deodap_max_pages`, `DeodapSpider`, `_deodap_kwargs`
- **Problem:** `Settings.deodap_max_pages` is validated but never passed to (or read by) the spider;
  the spider reads the same env var into a module global. Two sources of truth; config-driven
  defaults in `validate-config`/"manifest settings" have no effect on the crawl.
- **Severity:** MEDIUM
- **Why it matters:** operators setting `DEODAP_MAX_PAGES` through `.env`/manifest see it snapshotted
  but the spider silently uses a different value; `deodap_max_pages` becomes dead config surface.
- **Recommended fix:** pass `max_pages=settings.deodap_max_pages` into `DeodapSpider` via
  `_deodap_kwargs` and delete the module-global env read.

### F9 — Live partial failures reuse stale raw files, producing silent stale winners

- **File:** `scrapers/scrapers/cli.py` (`run_pipeline` L156–175), `matching/matcher.py`
  (`load_marketplace_products` L197–210)
- **Function/class:** `run_pipeline`, `load_marketplace_products`
- **Problem:** on `status == "failed"` the raw file for that source is not written/cleared, but
  `run_matching` reads whatever currently exists on disk. A failed live source silently re-matches
  on the **previous** run's data.
- **Severity:** MEDIUM
- **Why it matters:** sellers would see winners built on stale pricing/inventory after a partial
  crawl; nothing in the manifest or report labels data as stale.
- **Recommended fix:** write an empty/`[]` (or a `{"stale": true}` tombstone) raw file for failed
  sources, or record per-source data timestamps and exclude stale files from matching.

### F10 — Blocked-detection subsystem is dead code; metrics "blocked" unreachable

- **File:** `scrapers/scrapers/sources/base.py` (`is_blocked` L113, `BOT_SIGNATURES`,
  `BOT_CHALLENGE_SELECTORS`, `max_blocked_retries` L82), `scrapers/scrapers/metrics.py`
  (`SourceMetrics.blocked`, `RunMetrics.exit_code` L55), `cli.py` (`_crawl_source` L84)
- **Function/class:** `MarketplaceSpider.is_blocked`, `run_spider`, `SourceMetrics.blocked`
- **Problem:** `is_blocked` is defined but never called; `max_blocked_retries`/`autothrottle*`
  attributes are documented but unused; `SourceMetrics.blocked` is never incremented; the only
  statuses produced are `mock`, `ok`, `mock-fallback`, `failed` (never `blocked`), so
  `RunMetrics.exit_code()`'s “all blocked → 3” branch is unreachable via the CLI.
- **Severity:** MEDIUM
- **Why it matters:** the README advertises blocked-request detection + automatic retries as a core
  feature; it currently does nothing. Metrics/exit codes will misreport why a live crawl failed.
- **Recommended fix:** wire `is_blocked` into `run_spider`/spider retry loop, set status
  `blocked` and increment counters when detected, and test both `exit_code` branches from a real
  (stubbed) crawl path.

### F11 — History file rewritten wholesale each run; `lookback_days` unused

- **File:** `scrapers/scrapers/matching/history.py` (`append_history` L55, `compute_velocity` L65,
  `compute_alerts` L82)
- **Function/class:** `append_history`, `compute_velocity`, `compute_alerts`
- **Problem:** `append_history` re-reads the entire JSONL and rewrites it (atomic full-file write)
  every run; velocity/alerts scan all rows with no date filtering; the `lookback_days` parameter is
  accepted and ignored.
- **Severity:** MEDIUM
- **Why it matters:** as runs accumulate, each run becomes O(total history) for a single O(changes)
  append; alerts/velocity are computed off an ever-growing window, so “14-day lookback” semantics
  are absent and velocity numbers drift.
- **Recommended fix:** append-only file via `open(..., "a")` (fsync on flush) or rotate by day; use
  `lookback_days` and `ts` to window rows before aggregating; add tests for >2 rows and windowing.

### F12 — No env template or settings reference for the scrapers package

- **File:** repo root `.env.example`
- **Problem:** `.env.example` is 100% the deleted SupoClip video pipeline (AssemblyAI, OpenAI/Pexels,
  Stripe, Postgres/Redis, Better Auth, …) and contains none of the scrapers' variables; it also
  ships dev secrets (see Section 10). There is no documented reference for `WEBHOOK_SECRET`,
  `SHEETS_SERVICE_ACCOUNT`, `MIN_*`, etc.
- **Severity:** MEDIUM
- **Why it matters:** the two operational integrations that need secrets (Sheets export, webhook)
  are undocumented; `pipeline export --webhook --sheets` is the only feature a fresh user cannot
  configure from the docs.
- **Recommended fix:** replace root `.env.example` with a scrapers-specific template
  (`LOG_LEVEL`, `OUTPUT_DIR`, `MIN_CONFIDENCE`, `MIN_ABSOLUTE_MARGIN`, `MIN_MARGIN_PCT`,
  `MIN_TICKET_PRICE`, `MAX_SELLERS`, `MAX_FBA_SELLERS`, `REPORT_TOP_N`, `SCRAPLING_*`,
  `SHEETS_SERVICE_ACCOUNT`, `SHEETS_SPREADSHEET_ID`, `WEBHOOK_URL`, `WEBHOOK_SECRET`, `HISTORY_DIR`,
  `ALLOW_MOCK_FALLBACK`).

### F13 — Uncommitted mass deletion and tracked-data churn

- **File:** repo root (git index)
- **Problem:** `git status` shows ~hundreds of deletions (legacy `backend/`, `frontend/`, docs,
  licenses) plus modified tracked data artifacts (`data/*_raw.json`, `matched_products.*`). The
  scrapers reorg commits are clean, but the tree was never committed as the “strip-to-scrapers”
  change.
- **Severity:** MEDIUM
- **Why it matters:** a single careless `git add -A` would commit runtime artifacts and second-guess
  the intended history; archaeology is hard (legacy files still in index); reviewers can't see the
  intended final repo shape.
- **Recommended fix:** decide the final tree, stage the deletion explicitly, add the raw outputs to
  `.gitignore` (F20), and commit the repository restructuring as its own change.

## 9. Findings — LOW / Cosmetic

### F14 — `scrape-asins` subcommand has no test coverage and fragile write path

- **File:** `scrapers/scrapers/cli.py` (`_cmd_scrape_asins` L306–321)
- **Problem:** not covered by any test; in a non-editable install it writes to a (possibly
  read-only) site-packages path (ties into F7); the merge `sorted(set(...) | set(...))` rewrites
  the file non-atomically for the JSON (atomic, but `SEED_FILE` may not exist → `load_json(...)`
  default path taken, fine, but the workflow is undocumented).
- **Severity:** LOW
- **Why it matters:** it is the one command that mutates repo-owned package data; failures there
  corrupt the seed list or crash without a friendly error.
- **Recommended fix:** write tests; guard writes behind a try/except with clear `ExportError`;
  consider relocating seeds to `OUTPUT_DIR`.

### F15 — Lint gate not met (plan explicitly required "flake8 clean")

- **File:** all `scrapers/scrapers/**/*.py`, `scrapers/tests/**/*.py`
- **Problem:** with default flake8: 354 issues on the tree (274 `E501`, 46 `W292`, 28 `F821`,
  5+4 `F401`, 1 `E305`). Using the plan's own command `--max-line-length=100`:
  `scrapers/scrapers` **113** (58 `E501`, 28 `F821`, 24 `W292`, 2 `F401`, 1 `E305`),
  `scrapers/tests` **31** (6 `E501`, 3 `F401`, 22 `W292`).
- **Severity:** LOW
- **Why it matters:** plan Task 20 Step 4 said “all tests pass; flake8 clean”. The F821 cases are
  latent `NameError`s (see F1); W292 (no trailing newline) and unused imports are trivial but make
  the “clean” claim false and trips reviewers.
- **Recommended fix:** fix F821 first (F1), then run `ruff`/autofix for `W292`/`F401`/`E305`,
  then configure line length (F16) and wire into CI (F2).

### F16 — No flake8/ruff config pins the intended style

- **File:** repo root (no `setup.cfg`, `tox.ini`, `.flake8`, or `[tool.flake8]`/`[tool.ruff]`)
- **Problem:** the only dev lint tool (flake8 in `dev` extra) runs at the 79-col default, which is
  inconsistent with the plan's `--max-line-length=100`; devs and CI can't reproduce the same gate.
- **Severity:** LOW
- **Why it matters:** style churn and irreproducible lint results; blocks adopting F15 fixes.
- **Recommended fix:** add a config file (e.g. `.flake8` with `max-line-length = 100`,
  `extend-ignore = E203,W503`) or move to ruff with a `[tool.ruff]` section.

### F17 — Test coverage gaps in otherwise solid suite

- **File:** `scrapers/tests/` (17 files)
- **Problem:** no tests for: `_cmd_scrape_asins`, `_cmd_history`, `_cmd_export --webhook` success
  path (only config-guard), Sheets success (needs gspread mock), any live/annotated method (see F1),
  `is_blocked`/blocking retries (see F10), `dedupe_items` full+full merge branch, `history`
  windowing, `_score_match` with real amazon fields, `SEED_FILE`/`load_seed_asins`. No coverage
  measurement configured.
- **Severity:** LOW
- **Why it matters:** the 88 tests give a false sense of safety around exactly the paths that are
  most broken (live mode, blocking, exports).
- **Recommended fix:** add the above tests; add `[tool.coverage]` + `pytest --cov`.

### F18 — Outputs and run dirs are CWD-relative; artifacts scatter across dirs

- **File:** `scrapers/scrapers/cli.py` (`run_pipeline`), `scrapers/scrapers/io.py`
  (`write_manifest`), reproducible artifact `scrapers/data/runs/20260914T162748Z/`
- **Problem:** `OUTPUT_DIR` default is the literal `"data"` resolved against CWD. The mock E2E ran
  from repo root → `data/…`; a later run from `scrapers/` created `scrapers/data/runs/20260914T162748Z/`
  with an empty `run.log` and no manifest (live attempt → `DependencyError` exit 4 before any
  source-level log line). No doc tells users to run from repo root.
- **Severity:** LOW
- **Why it matters:** operators get confusing dual output trees and missing manifests; scraping a
  wrong CWD silently produces nothing where expected.
- **Recommended fix:** default `OUTPUT_DIR` relative to the repo root (e.g., resolve against the
  package root or a `.pipeline-root` marker) and document "run from repo root"; at minimum clarify
  in README.

### F19 — `post_webhook` swallows HTTP status detail; redaction otherwise sound

- **File:** `scrapers/scrapers/reporting/webhook.py` (`post_webhook` L20–29)
- **Problem:** `except Exception` wraps `HTTPError` too, so 4xx/5xx replies lose their status/body;
  debugging webhook failures (e.g., 401 from a wrong `WEBHOOK_SECRET`) is harder than it should be.
  (Positive: HMAC-SHA256 signature header is correct and short timeout is sensible.)
- **Severity:** LOW
- **Why it matters:** 401/403 from misconfigured secrets are the most common operator error and the
  current error hides that signal.
- **Recommended fix:** re-raise `HTTPError` with its status included in the message (and keep
  ignoring `URLError` timeout cases), or return the status code and let `_cmd_export` report it.

### F20 — Raw outputs not gitignored; `requirements.txt` is a comment-only stub

- **File:** repo root `.gitignore` (L20–26), `scrapers/requirements.txt`
- **Problem:** `.gitignore` covers derived artifacts but not `data/amazon_movers_raw.json`,
  `deodap_catalog_raw.json`, `flipkart_bestsellers_raw.json`, `meesho_trending_raw.json` (two are
  currently untracked, two tracked and modified by runs); `pip install -r requirements.txt`
  installs nothing and README instructs it.
- **Severity:** LOW
- **Why it matters:** accidental commits of run artifacts (F13); the documented install path is a
  no-op for new users.
- **Recommended fix:** add `data/*_raw.json` (or `data/` whole) to `.gitignore`; change README
  install to `pip install -e ".[dev]"`.

### F21 — Schema record fallback silently mis-validates unlabeled records

- **File:** `scrapers/scrapers/schemas.py` (`validate_record` L41–60, `normalize_record` L31–38)
- **Problem:** unknown/absent `source` falls through to marketplace rules (requires `current_price > 0`,
  `product_url`, marketplace id) but `normalize_record` coerces missing `None`/blank fields to `0.0`
  (e.g. `stock`, `rating`) — a deodap-style record without a `source` label is rejected with a
  confusing message; conversely a missing `stock` (0) would silently fail `eligible_deodap`'s
  `stock >= 20` check in live data that omits it.
- **Severity:** LOW
- **Why it matters:** silent drops/over-filtering of valid data degrade match quality without a log
  that explains the real cause.
- **Recommended fix:** require an explicit `source` (no fallback), or log the fallback; keep `None`
  distinct from numeric coercion where the field is optional.

### F22 — Stale pytest cache references a removed test; minimal smoke file

- **File:** `scrapers/tests/test_package.py` (8 lines), `scrapers/.pytest_cache` (`lastfailed`
  references `test_cli_placeholder_runs`, which no longer exists)
- **Problem:** cache drift is cosmetic, but `test_package.py`'s `test_cli_entrypoint_runs` calling
  `main(["list-sources"])` mutates global registry state shared across the suite (side-effect free
  here, but fragile).
- **Severity:** LOW
- **Why it matters:** smokers tolerating early deep-import of every source will start failing the
  moment F1-style regressions appear at import time (good), but the indirection hides which module
  broke.
- **Recommended fix:** keep (it's a useful smoke), consider `tests/test_package.py` asserting
  `import scrapers.sources.amazon` directly to catch import-time `NameError` regressions from F1.

## 11. Security & Secrets Review

- **Verdict:** the scrapers package itself handles secrets correctly: `Settings.to_dict(redact=True)`
  masks `webhook_secret` and strips proxy URL userinfo before manifest write
  (`config.py` L157–169), and `test_run_mock_e2e` asserts `webhook_secret in (None, "***")`.
  `redact_url` (`logging_setup.py` L60) strips credentials from logged URLs. HMAC-SHA256 webhook
  signing (`webhook.py`) is correct (prefix `sha256=`).
- **Findings in scope:** F19 (HTTPError swallowed) — minor; the **stale root `.env.example` ships
  dev secrets** (`BETTER_AUTH_SECRET=supoclip_dev_secret_change_in_production`,
  `BACKEND_AUTH_SECRET=change_me_backend_auth_secret`, `POSTGRES_PASSWORD=supoclip_password`,
  `APP_SETTINGS_ENCRYPTION_KEY=change_me_settings_encryption_secret`) from the deleted app; and CI
  (`tests.yml`) hardcodes test secrets. These are SupoClip-era and should be removed with the
  deletion commit (F13/F12). No secrets were found in `scrapers/` source or tests.
- **Supply-chain note:** the `fetchers` extra pulls Playwright-based `scrapling` (large browser
  attack surface) and `sheets` pulls `gspread`; both are optional, which is the right design. There
  is no dependency pinning or lockfile, so reproducibility of the live extras is not guaranteed.

## 12. Data & Artifact Integrity

- The reference mock run is internally consistent: manifest `matching` block (21 marketplace
  products, 17 candidates, 15 winners, 4 near-misses, 7 high-opportunity) matches
  `matched_products.json` (`marketplace_total: 21`) and the CSV's 15 winner rows; `near_matches.json`
  entries have confidence in [0.40, 0.50) i.e. below `min_confidence 0.5`, consistent with the
  near-miss floor `0.35`.
- Confirmed inconsistencies to carry forward: `winners.md`/`manifest` were produced with
  `min_absolute_margin: 80.0` and `min_ticket_price: 100.0` — **not** the code defaults (200/300),
  so artifacts shown to users encode different thresholds than a fresh run would (F3, Section 10).
- Data artifacts are version-controlled partially and gitignored partially (F13/F20); a fresh user
  cloning the repo will not get `data/*` (mirror outputs) and cannot see the demo winners without
  running a mock E2E; that's acceptable, but README doesn't say so.
- The `matcher` multiplies fabricated BSR (F5) into the artifacts; treat all opportunity scores in
  the shipped outputs as inflated.

## 13. Configuration & Environment Hygiene

- Real settings surface (`config.py`): `LOG_LEVEL`, `LOG_FORMAT`, `OUTPUT_DIR`, `HISTORY_DIR`,
  `SCRAPLING_ALLOW_MOCK_FALLBACK`, `SCRAPLING_ADAPTIVE(_PERCENTAGE)`, `SCRAPLING_CRAWL_DIR`,
  `SCRAPLING_PROXY`, `AMAZON_MOVERS_URL`, `AMAZON_BESTSELLERS_URLS`, `AMAZON_NODE_CATEGORIES`,
  `MEESHO_TRENDING_URL`, `FLIPKART_BESTSELLERS_URL`, `DEODAP_BASE_URL`, `DEODAP_CATEGORIES`,
  `DEODAP_MAX_PAGES`, `MIN_CONFIDENCE`, `MIN_ABSOLUTE_MARGIN`, `MIN_MARGIN_PCT`, `MIN_TICKET_PRICE`,
  `MAX_SELLERS`, `MAX_FBA_SELLERS`, `REPORT_TOP_N`, `SHEETS_SERVICE_ACCOUNT`, `SHEETS_SPREADSHEET_ID`,
  `WEBHOOK_URL`, `WEBHOOK_SECRET`.
- Mismatches: `DEODAP_MAX_PAGES` is dead for the spider (F8); `SCRAPLING_ALLOW_MOCK_FALLBACK` env
  name vs flag `--allow-mock-fallback` (both exist, flag wins — fine); `.env.example` lacks all of
  the above (F12); README's env table overlaps only 4 keys (F3).
- Validation is good: `_validate` rejects bad log level/format, percentage bounds, non-empty
  bestseller URLs, proxy scheme; `validate-config` is a useful command and is covered by tests.

## 14. Documentation Accuracy

- `scrapers/README.md`: stale CLI/module references, thin env table, contradictory thresholds (F3).
- `scrapers/FIND_ASINS.md`: wrong absolute path, wrong module invocation, overclaim about seed use (F4).
- `scrapers/requirements.txt`: comment-only stub (F20).
- Plan/spec (`docs/superpowers/…`): internal docs are accurate and detailed; the plan is the source
  of truth for what was supposed to be delivered, and the audit uses it as the compliance baseline
  (Section 16).
- Missing: any note that live mode requires a glibc host (only exists inside the `DependencyError`
  message), and any listing of the run output layout for operators.

## 15. Dependencies & Packaging

- Core deps: `python-dotenv>=1.0` only — genuinely pure-Python, Termux-compatible (verified: core
  imports fine here). Good.
- Extras: `fetchers = scrapling[fetchers]>=0.4.15`, `sheets = gspread>=6`, `dev = pytest>=8, flake8>=7` —
  sensible separation. No version bumps/pins beyond minimums; no lockfile for the live stack (F19
  section risk).
- Entry point `pipeline = scrapers.cli:main` present and working (test `test_cli_entrypoint_runs`).
- Packaging gaps: package data for `seed_asins.json` missing (F7); `scrapers.egg-info/SOURCES.txt`
  confirms omission; `requirements.txt` stub (F20).
- Python support: declared `>=3.10`, effectively **3.14-only** until F1 is fixed (Section 5).

## 16. Test Suite & Coverage

- **Run:** `python3 -m pytest scrapers/tests -q` → **88 passed in 1.92s** (pytest 9.1.1, CPython 3.14.6).
- Strengths: atomic-IO crash safety, manifest contents, redaction, exit-code mapping, config
  validation/fail-fast, scoring tiers/margin formula, similarity normalization, history alerts,
  registry duplicate rejection, mock catalog completeness, dedupe (partial), webhook signing,
  writer columns unchanged, CLI e2e mock run with tmp_path isolation, live-without-scrapling exit 4.
- Coverage gaps (all mapped to findings): live/annotated methods (F1), blocking/retries (F10),
  `scrape-asins` (F14), history windowing (F11), sheets/webhook success (F17), seed loading (F17).
- **Item moved forward into Section 19 (verification record):** the suite passes **only because
  every test runs on 3.14**; on 3.11 (what CI pins) collection itself would fail (F1/F2).

## 17. Spec & Plan Delivery Compliance

Baseline: `docs/superpowers/specs/2026-09-14-scrapers-enterprise-design.md` and
`docs/superpowers/plans/2026-09-14-scrapers-enterprise.md`.

| Requirement (plan) | Status | Evidence |
|--------------------|--------|----------|
| Layered reorg + source registry + CLI subcommands | ✅ Delivered | `scrapers/` layout, `registry.py`, `cli.py` |
| Pure-Python core; guarded scrapling imports | ⚠️ Partial | guarded in `base.py` only; leaf modules reference names unguarded → F1 |
| No silent mock fallback; `mock-fallback` labeled | ✅ | `--allow-mock-fallback`, status `mock-fallback` in logs/metrics |
| Preserve CSV columns & output field names | ✅ | `CSV_COLUMNS` unchanged; `test_csv_columns_unchanged` |
| Preserve bundled mock catalog values | ✅ | stability assertions in source tests |
| Secrets redacted from logs/manifest | ✅ | `to_dict(redact=True)`; test asserts |
| Task 20 Step 1: rewrite README quickstart | ❌ Not delivered | README still references deleted modules (F3) |
| Task 20 Step 2: update FIND_ASINS.md | ❌ Not delivered | wrong path/module remain (F4) |
| Task 20 Step 3: create `scrapers/.gitignore` | ✅ | present (also adds `.pytest_cache/`) |
| Task 20 Step 4: full suite + flake8 clean | ❌ Not met | 88 pass, but flake8 = 113 + 31 issues even at 100-col (F15) |
| Task 20 Step 6 / "git commit" per task | ❌ | no docs commit in `git log` |
| Task 21 E2E deliverable (mock run, manifest, ranked list) | ✅ (operator-run) | `data/runs/20260914T155012Z/…`, `winners.md`, exists on disk |

## 18. Live-Mode Operational Readiness

- **Readiness: NOT ready.** Live mode requires: (a) fixing F1 (undefined names → NameError even with
  scrapling installed); (b) a glibc host with `pip install -e ".[fetchers]"` + `scrapling install` —
  correctly surfaced via `DependencyError` exit 4 (verified); (c) wiring the dead block-detection
  subsystem (F10); (d) resolving the stale-file reuse on partial failure (F9); (e) honest fee/velocity
  inputs (F5/F6) before the winners list is trustworthy.
- The empty `scrapers/data/runs/20260914T162748Z/run.log` (no manifest) in the tree is the trace of
  an attempted live run on this host and matches the expected `DependencyError` exit-4 path.
- Amazon/Flipkart selectors target specific, undocumented DOM (e.g. `._cDEzb_p13n-sc-css-line-clamp-3_g3dy1`,
  `a[href*='/p/']`); the adaptive store (`.scrapling/`) exists only after a successful live run and
  is gitignored — environment-dependent behavior should be called out in ops docs.

## 19. Prioritized Remediation Roadmap & Verification Record

**Recommended order (dependency-driven):**

1. **Fix F1** (import scrapling names in leaf modules + `from __future__ import annotations`), add a
   stubbed live-path test. This unblocks Python 3.10–3.13 and live mode. *(defect-to-fix)
2. **Fix F2** — replace the stale `.github/workflows/tests.yml` with a `scrapers` job on 3.11+3.14
   running pytest + flake8; this makes every later fix verifiable.
3. **Fix F3/F4/F12/F14 docs + env template** — align README/FIND_ASINS to the real CLI, add an env
   template, document seed flow.
4. **Fix F5/F6 scoring honesty** — real velocity or remove term; per-marketplace fee schedules.
5. **Fix F7/F8/F9/F10 data/packaging/dead-code** — package data, `deodap_max_pages` plumbing,
   stale-file tombstones, wire block detection.
6. **Fix F11/F13/F15/F16/F17/F18/F20–22** — history windowing, git restructure + gitignore, lint
   config + cleanup, coverage, CWD handling, small fixes.
7. Re-run: full pytest, flake8 (config-pinned), and a fresh `pipeline --output-dir data run --mock`
   E2E; update this report's verification block.

**Verification Record (executed during this audit, evidence captured):**

- `python3 -m pytest scrapers/tests -q` → **88 passed in 1.92s** (pytest 9.1.1, CPython 3.14.6).
- `python3 -m flake8 scrapers/scrapers scrapers/tests` (default 79-col) → **354** issues
  (E501 274, W292 46, F821 28, F401 9, E305 1).
- `python3 -m flake8 scrapers/scrapers --max-line-length=100` → **113** (E501 58, F821 28, W292 24,
  F401 2, E305 1); `python3 -m flake8 scrapers/tests --max-line-length=100` → **31** (E501 6, F401 3,
  W292 22).
- Reproduced `inspect.signature(AmazonMoversSpider.parse_list)` → `NameError: name 'Response' is not defined`
  (proof of F1 on 3.14; eager-annotation failure on ≤3.13 is definitional).
- `import scrapers; import scrapers.sources.amazon` succeeds only on 3.14 deferred annotations.
- Reference E2E artifacts inspected and cross-checked: `data/runs/20260914T155012Z/manifest.json`
  (mode=mock; 21 marketplace / 17 candidates / 15 winners / 4 near-misses), `winners.md` (15 rows),
  `matched_products.csv` (16 lines), `matched_products.json`, `near_matches.json`, `products.jsonl`
  (36 rows), `scrapers/data/runs/20260914T162748Z/run.log` (empty, no manifest → live attempt exit 4).

---

**AUDIT COMPLETE**
**Tests: 88 passed (python3 -m pytest scrapers/tests -q on CPython 3.14.6 / pytest 9.1.1); lint NOT clean — 113 (scrapers/scrapers) + 31 (scrapers/tests) flake8 issues even with --max-line-length=100**
**Files changed: AUDIT.md**