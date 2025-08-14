# TASK.md

> **Prompt to AI:** "Use this TASK document as the single source of truth for MVP progress. Each ticket must follow TDD: write failing tests first, then implement minimal code, then refactor. No ticket is complete until tests pass and acceptance criteria are met."

---

## 1 · Sprint 1 (Setup & Directory Scanning)
**Purpose:** Establish project foundation, CLI entrypoint, and directory scanning logic.

### 1.1 Init Project
* **Goal:** Bootstrap Python package, dependencies, and CLI entrypoint.
* **Tests to Write:**
  - `tests/test_init_project.py::test_package_structure`
  - `tests/test_init_project.py::test_requirements_file`
  - `tests/test_cli_entrypoint.py::test_cli_imports`
* **Steps:**
  1. Create package folder `mpv_scraper/` with `__init__.py`.
  2. Add `requirements.txt` listing `requests`, `Pillow`, `lxml`, `click`.
  3. Create `mpv_scraper/cli.py` with stub `@click.group()` and `run` command.
* **Done when:** All above tests fail initially then pass after implementation.

### 1.2 Directory Scanning
* **Goal:** Discover show subdirectories and movie files under `/mpv`.
* **Tests to Write:**
  - `tests/test_scanner.py::test_scan_directory_returns_shows_and_movies`
  - `tests/test_scanner.py::test_scan_empty_directory`
* **Steps:**
  1. Implement `scan_directory(path: Path) -> dict` returning `{shows: [...], movies: [...]}`.
  2. Ensure `/mpv/Movies` is identified separately from show folders.
  3. Write fixtures representing nested folder structures.
* **Done when:** Tests confirm correct data structures for sample fixtures.

---

## 2 · Sprint 2 (Filename Parsing)
**Purpose:** Parse TV and movie filenames, including anthology spans.

### 2.1 Parse TV Filenames
* **Goal:** Extract show name, season, episode range, and titles.
* **Tests to Write:**
  - `tests/test_parser.py::TestParseTvFilename::test_single_episode`
  - `tests/test_parser.py::TestParseTvFilename::test_anthology_span`
* **Steps:**
  1. Write `parse_tv_filename(filename: str) -> TVMeta` with fields: `show`, `season`, `start_ep`, `end_ep`, `titles`.
  2. Use regex to detect `SxxEyy(-Ezz)?` patterns and split titles on ` - `.
  3. Return `end_ep = start_ep` when no span.
* **Done when:** Both tests pass and cover edge cases (e.g., `S01E09-E10`).

### 2.2 Parse Movie Filenames
* **Goal:** Extract title and year from `Title (Year).ext`.
* **Tests to Write:**
  - `tests/test_parser.py::TestParseMovieFilename::test_standard_movie`
  - `tests/test_parser.py::TestParseMovieFilename::test_missing_year`
* **Steps:**
  1. Write `parse_movie_filename(filename: str) -> MovieMeta` with `title`, `year`.
  2. Regex match `(.+) \((\d{4})\)`; default `year=None` if missing.
* **Done when:** Tests verify correct parsing and fallback.

---

## 3 · Sprint 3 (TVDB Integration)
**Purpose:** Authenticate with TVDB and fetch show/episode metadata.

### 3.1 TVDB Authentication & Search
* **Goal:** Obtain JWT token and search for series by name. The user's choice for ambiguous results will be for the **current session only** and will not be persisted.
* **Tests to Write:**
  - `tests/test_tvdb.py::test_authenticate_raises_on_missing_key`
  - `tests/test_tvdb.py::test_search_show_returns_candidates`
  - `tests/test_tvdb.py::test_interactive_disambiguation_prompt` (using mocks for `click.prompt`)
* **Steps:**
  1. Load `TVDB_API_KEY` from env; raise if unset.
  2. Implement `authenticate_tvdb() -> token` calling login endpoint.
  3. Write `search_show(name: str, token: str) -> List[Series]`.
  4. Implement an interactive prompt when search returns multiple results.
* **Done when:** Calls succeed in tests using HTTP mocks and user interaction is correctly simulated.

### 3.2 Fetch Series & Episodes
* **Goal:** Retrieve full series record, including all episode data, in a single API call.
* **Tests to Write:**
  - `tests/test_tvdb.py::test_get_series_extended_returns_full_record`
  - `tests/test_tvdb.py::test_get_series_extended_handles_not_found`
* **Steps:**
  1. Implement `get_series_extended(series_id, token)` to call the `/series/{id}/extended` endpoint.
  2. The function should cache the entire response JSON to avoid repeated calls.
  3. Implement a simple rate-limiter (e.g., a short sleep) after each API call to respect API limits.
* **Done when:** Tests confirm the full series record is fetched and cached correctly.

---

## 4 · Sprint 4 (TMDB Integration & Documentation)
**Purpose:** Search TMDB, fetch movie metadata, and perform a full documentation sweep.

### 4.1 TMDB Movie Search
* **Goal:** Find movie by title and year, mirroring the TVDB client's architecture.
* **Tests to Write:**
  - `tests/test_tmdb.py::test_search_movie_raises_on_missing_key`
  - `tests/test_tmdb.py::test_search_movie_by_title_year`
  - `tests/test_tmdb.py::test_search_movie_caches_results`
* **Steps:**
  1. Create `src/mpv_scraper/tmdb.py`.
  2. Load `TMDB_API_KEY` from env; raise if unset.
  3. Implement `search_movie(title: str, year: Optional[int])` using the `/search/movie` endpoint.
  4. Implement caching and rate-limiting identical to the TVDB client.
* **Done when:** Tests pass with mocked TMDB responses.

### 4.2 Fetch Movie Details
* **Goal:** Extract overview, release date, rating, and poster path.
* **Tests to Write:**
  - `tests/test_tmdb.py::test_fetch_movie_details`
* **Steps:**
  1. Implement `get_movie_details(movie_id: int)`.
  2. Convert `vote_average` to a 0–1 float.
  3. Cache the response.
* **Done when:** Tests validate meta mapping and caching.

### 4.3 Documentation Sweep
* **Goal:** Ensure all modules are documented and create a user-facing Quick Start Guide.
* **Tests to Write:** N/A (Documentation task)
* **Steps:**
  1. Review all modules in `src/mpv_scraper` and ensure docstrings are clear and complete.
  2. Add module-level docstrings explaining the purpose of each file.
  3. Create `docs/QUICK_START.md` with simple, step-by-step instructions for a new user. **This must include how to acquire TVDB and TMDB API keys.**
  4. Update `README.md` to link to the new documentation files.
* **Done when:** All code is documented and the Quick Start Guide is clear and accurate.

---

## 5 · Sprint 5 (Image Processing)
**Purpose:** Download, convert, and optimize artwork.

### 5.1 Download & Convert to PNG
* **Goal:** Save remote images as local PNG files.
* **Tests to Write:**
  - `tests/test_images.py::test_download_and_convert_png`
* **Steps:**
  1. Implement `download_image(url, dest: Path) -> None`.
  2. Use Pillow to convert any format to PNG.
* **Done when:** PNG files are created and tests pass.

### 5.2 Resize & Compress
* **Goal:** Ensure images < 600 KB.
* **Tests to Write:**
  - `tests/test_images.py::test_resize_under_threshold`
* **Steps:**
  1. Check file size; if >600 KB, resize proportionally to max width 500px.
  2. Re-save PNG and verify size.
* **Done when:** Tests confirm all sample images below threshold.

### 5.3 Documentation Sweep
* **Goal:** Document image-processing utilities and update user docs if new flags or behaviors were introduced during Sprint 5.
* **Tests to Write:** N/A
* **Steps:**
  1. Ensure `images.py` (or equivalent) has clear docstrings.
  2. Update `README.md` and `docs/QUICK_START.md` with any new prerequisite tools or usage notes (e.g., Pillow install, CLI flags).
* **Done when:** Documentation matches implemented functionality.

---

## 6 · Sprint 6 (XML Generation & CLI Integration)
**Purpose:** Write gamelist XML and expose CLI commands.

### 6.1 Generate Gamelist XML
* **Goal:** Create `gamelist.xml` with `<folder>` and `<game>` entries.
* **Tests to Write:**
  - `tests/test_xml.py::test_write_top_gamelist`
  - `tests/test_xml.py::test_write_show_gamelist_with_span`
* **Steps:**
  1. Implement `write_top_gamelist(data, dest)` producing folder entries.
  2. Implement `write_show_gamelist(show_data, dest)` with game entries.
  3. Validate well-formed XML via parser in tests.
* **Done when:** Knulli UI displays correct entries in local demo.

### 6.2 CLI Commands & Documentation
* **Goal:** Expose `scan`, `scrape`, `generate`, and `run` commands; document in README.
* **Tests to Write:**
  - `tests/test_cli_commands.py::test_run_combined_workflow`
* **Steps:**
  1. Add commands in `mpv_scraper/cli.py` using Click decorators.
  2. Wire up commands to call scanning, scraping, and XML generation.
  3. Update `README.md` with usage examples and flags.
* **Done when:** `mpv-scraper run /mpv` completes end-to-end in demo.

### 6.3 Documentation Sweep
* **Goal:** Verify XML generation and CLI sections are fully documented.
* **Tests to Write:** N/A
* **Steps:**
  1. Ensure new CLI commands and XML helpers include comprehensive docstrings.
  2. Update `README.md` usage examples and any option tables.
* **Done when:** Docs accurately reflect CLI behavior and XML schema.

---

## 7 · Sprint 7 (Undo & Rollback Functionality)
**Purpose:** Implement a system to track and revert file changes made by the scraper.

### 7.1 Transaction Logging
* **Goal:** Record all file operations (creations, modifications) performed during a scraper run.
* **Tests to Write:**
  - `tests/test_undo.py::test_log_file_creation`
  - `tests/test_undo.py::test_log_file_modification`
* **Steps:**
  1. Design a transaction log format (e.g., JSON).
  2. Create a `TransactionLogger` class to manage writing to the log.
  3. Integrate logging into the image download and XML generation steps.
* **Done when:** A `transaction.log` file is correctly generated after a `run` command.

### 7.2 Implement `undo` Command
* **Goal:** Create a CLI command to revert the changes from the most recent transaction log.
* **Tests to Write:**
  - `tests/test_undo.py::test_undo_reverts_created_files`
  - `tests/test_undo.py::test_undo_restores_modified_files`
* **Steps:**
  1. Add an `undo` command to `cli.py`.
  2. Implement logic to parse the transaction log and reverse the operations (e.g., delete created files, restore previous versions of modified files from a temporary backup).
  3. The `undo` command should consume the log file upon successful completion.
* **Done when:** Running `mpv-scraper undo` successfully restores the file system to its pre-run state.

### 7.3 Documentation Sweep
* **Goal:** Document the rollback system and provide usage examples.
* **Tests to Write:** N/A
* **Steps:**
  1. Add docstrings to `TransactionLogger` and `undo` command implementation.
  2. Update `README.md` with a section on “Reverting Changes”.
* **Done when:** Users can understand and confidently use the undo capability.

## 8 · Sprint 8 (Integration & Regression Testing)
**Purpose:** Validate the complete scraper workflow and guard against regressions before release.

### 8.1 End-to-End Pipeline Test
* **Goal:** Ensure `scan → scrape (mocked) → generate` produces correct outputs for a realistic library.
* **Tests to Write:**
  - `tests/e2e/test_pipeline.py::test_full_pipeline_generates_expected_files`
* **Steps:**
  1. Copy `mocks/mpv` into a temp directory in the test.
  2. Monkeypatch TVDB/TMDB calls to return canned JSON (use `responses` or `pytest-mock`).
  3. Invoke `cli.run` on the temp directory with `CliRunner`.
  4. Assert:
     * Top-level and per-show `gamelist.xml` files exist and are well-formed.
     * All referenced image files exist and are ≤ 600 KB.
* **Done when:** Test passes without network access and within CI time limits.

### 8.2 Regression Test – Undo Safety
* **Goal:** Confirm that `undo` restores the filesystem exactly to its pre-run state.
* **Tests to Write:**
  - `tests/regression/test_undo_state.py::test_run_then_undo_restores_checksum`
* **Steps:**
  1. Use a temp copy of `mocks/mpv`.
  2. Capture checksum / listing of the directory.
  3. Run `cli.run` (with APIs mocked) to generate files & `transaction.log`.
  4. Run `cli.undo`.
  5. Re-calculate checksum; expect it to match the original.
* **Done when:** Directory state is identical and `transaction.log` is removed.

### 8.3 CLI Smoke Test Matrix
* **Goal:** Verify every CLI command exits 0 with minimal runtime.
* **Tests to Write:**
  - `tests/smoke/test_cli_commands.py` parametrized for `scan`, `generate`, `run`, `undo`.
* **Steps:**
  1. Use `CliRunner()` with the mock library.
  2. Assert `result.exit_code == 0` for each command.
* **Done when:** All smoke tests green.

### 8.4 Continuous Integration Updates
* **Goal:** Ensure new tests run in GitHub Actions.
* **Steps:**
  1. Update `.github/workflows/ci.yml` to install any extra dev dependencies (e.g., `responses`).
  2. Ensure the workflow caches wheels and runs `pytest` on every push/PR.
* **Done when:** CI passes with the new integration suite.

## 8.5 Documentation Sweep – Testing Guides
**Purpose:** Add clear guidance on how to run the new integration / regression tests and keep QUICK START fully up-to-date.

### Goal
Document the test framework, mock media setup, and CI expectations so contributors can run the full suite locally and understand the Sprint 8 tests.

### Tests to Write
N/A (pure documentation)

### Steps
1. **Add “Running the Test Suite” section to `docs/QUICK_START.md`**
   * Explain:
     * Activating the venv (`source .venv/bin/activate`)
     * Installing dev dependencies: `pip install -r requirements-dev.txt`
     * Running the full matrix: `pytest -q`
     * Filtering: `pytest -k e2e` or `-k smoke`

2. **Create `docs/TESTING.md`**
   * Describe directory structure of `mocks/mpv`.
   * Show how TVDB/TMDB HTTP calls are mocked with `responses`.
   * Detail how `transaction.log` is checked in rollback tests.
   * Provide troubleshooting tips (e.g., clearing cache, regenerating mocks).

3. **Update README**
   * Add a bullet under “CLI Usage”: “See `docs/TESTING.md` for running the test suite.”
   * Verify all command examples (`scan`, `generate`, `run`, `undo`) remain correct.

4. **Cross-check links**
   * Ensure README → QUICK_START → TESTING hyperlinks render in GitHub.
   * Confirm CI badge or status references still resolve.

5. **Run pre-commit hooks**
   * Let hooks format markdown / fix trailing newlines if needed.

### Done when
* QUICK_START contains a concise “Running the Tests” section.
* A standalone `docs/TESTING.md` exists with full instructions.
* README references the new guide.
* `pytest -q` passes and all links render correctly on GitHub.

---

## 9 · Sprint 9 (Extended Metadata & Artwork)
**Purpose:** Enrich gamelists with ratings, long descriptions, and marquee artwork.

### 9.1 XML Tag Support
* **Goal:** Extend `xml_writer` to write optional `<desc>`, `<rating>`, `<marquee>` tags.
* **Tests to Write:**
  - `tests/test_xml.py::test_write_game_extended_tags`
* **Steps:**
  1. Update helper functions to accept `rating`, `marquee` fields.
  2. Validate rating written as decimal 0–1.
* **Done when:** New unit test passes and XML conforms to EmulationStation schema.

### 9.2 Normalize Ratings
* **Goal:** Convert TVDB/TMDB vote averages (0–10) to 0–1 floats.
* **Tests to Write:**
  - `tests/test_tvdb.py::test_rating_normalization`
  - `tests/test_tmdb.py::test_rating_normalization`
* **Steps:**
  1. Add util `normalize_rating(raw: float) -> float`.
  2. Integrate into TVDB/TMDB clients.
* **Done when:** Ratings are normalized and cached.

### 9.3 Fetch Long Descriptions
* **Goal:** Store series/episode/movie overviews; fall back to shorter synopsis.
* **Tests to Write:**
  - `tests/test_tvdb.py::test_episode_description`
  - `tests/test_tmdb.py::test_movie_description`
* **Steps:**
  1. Update API helpers to extract `overview`.
  2. Persist in cache for later generate step.
* **Done when:** Descriptions >140 chars handled without truncation.

### 9.4 Logo (Marquee) & Screenshot Artwork
* **Goal:** Download alpha-channel series/movie **logo** (TVDB *clearLogo*, TMDB *logo*) for the `<marquee>` tag plus optional screenshots; ensure each image ≤600 KB.
* **Tests to Write:**
  - `tests/test_images.py::test_download_marquee_png`
* **Steps:**
  1. For TV shows pull the first English `clearLogo` from TVDB; for movies fetch the English (or “null”) logo from TMDB.
  2. Save as PNG under `images/<logo>.png` and reference it via `<marquee>`.
  3. (Optional) add screenshot handling similar to posters.
* **Done when:** Logo artwork is downloaded, optimized, stored, and referenced in XML; size limits respected.

### 9.5 CLI Integration
* **Goal:** Wire new metadata into `generate` workflow.
* **Tests to Write:**
  - `tests/smoke/test_cli_extended.py::test_generate_includes_extended_tags`
* **Steps:**
  1. Modify `generate` to read cached metadata and populate new XML fields.
  2. Ensure transaction logging covers new files.
* **Done when:** Smoke test passes and files created during run include extended metadata.

### 9.5.1 Testing Enhancements
**Purpose:** Close coverage gaps introduced by Sprints 9.3–9.5 and strengthen CI.

#### 9.5.1.1 Unit & Integration Tests
* **Tests to Write:**
  - `tests/images/test_download_marquee_png::test_size_enforcement`
  - `tests/integration/test_cache_hits.py::test_tmdb_cache`
  - `tests/integration/test_cache_hits.py::test_tvdb_cache`
  - `tests/regression/test_undo_logo.py::test_logo_undo`
* **Steps:**
  1. Replace placeholder logo test with real >500 px RGBA PNG; assert `download_marquee` saves <600 KB.
  2. Mock `requests.get` and call TMDB/TVDB helpers twice; assert HTTP layer called once (cache hit).
  3. Extend undo regression test to verify `logo.png` creation and rollback.
* **Done when:** All new unit/integration tests pass locally.

#### 9.5.1.2 Extended End-to-End Pipeline Test
* **Tests to Write:**
  - `tests/e2e/test_pipeline_extended.py::test_full_pipeline_multi_season`
* **Steps:**
  1. Build temp library with multi-season show and anthology span file.
  2. Mock API responses to include ratings (0-10) and logo URLs.
  3. Run `cli.run`; assert generated XML contains correct `<marquee>` paths and normalized `<rating>` values.
  4. Validate resulting XML with `xmlschema` for well-formedness.
* **Done when:** Extended pipeline test passes without network.

#### 9.5.1.3 CI Workflow Updates
* **Steps:**
  1. Expand GitHub Actions matrix to Python 3.9, 3.10, and 3.11.
  2. Install any new dev deps (e.g., `xmlschema`).
* **Done when:** CI green across all versions and new tests.

### 9.6 Documentation Sweep – Extended Metadata
* **Goal:** Document new XML tags and command-line options.
* **Tests to Write:** N/A
* **Steps:**
  1. Update `docs/QUICK_START.md` and `README.md` with examples of ratings/marquee.
  2. Ensure any new CLI flags are documented.
* **Done when:** Docs reflect extended metadata support.

## 10 · Sprint 10 (Live Scraping Integration)
**Purpose:** Replace placeholder metadata & artwork with real data from TVDB / TMDB and wire a full scrape step into the CLI.

### 10.1 TV Show Scraping
* **Goal:** Download episode descriptions, ratings, posters, and clearLogo for every show.
* **Tests to Write:**
  - `tests/integration/test_scrape_tv.py::test_episode_metadata_downloaded`
  - `tests/integration/test_scrape_tv.py::test_logo_saved`
* **Steps:**
  1. Add `scraper.py` with `scrape_tv(show_dir: Path)`.
  2. Use existing TVDB helpers to fetch series + episode records.
  3. Save poster to `images/poster.png`, episode thumbnails to `images/SxxEyy.png`, logo to `images/logo.png` via `download_marquee`.
  4. Cache the raw TVDB response under `.scrape_cache.json`.
* **Done when:** Unit tests pass with mocked HTTP; images ≤ 600 KB.

### 10.2 Movie Scraping
* **Goal:** Fetch overview, normalized rating, poster, and logo for each movie.
* **Tests to Write:**
  - `tests/integration/test_scrape_movie.py::test_movie_metadata_downloaded`
* **Steps:**
  1. Implement `scrape_movie(movie_path: Path)` (TMDB).
  2. Save poster (`images/<title>.png`) and logo (`images/logo.png`).
  3. Cache TMDB JSON alongside the movie file.
* **Done when:** Posters/logos downloaded (≤ 600 KB) and tests pass.

### 10.3 `scrape` CLI Command
* **Goal:** Add `python -m mpv_scraper.cli scrape <dir>`.
* **Tests to Write:**
  - `tests/smoke/test_cli_commands.py::test_scrape_command`
* **Steps:**
  1. Call `scan_directory`, then invoke TV / Movie scrapers per item.
  2. Record new files with `TransactionLogger`.
* **Done when:** Smoke test passes using mocked network.

### 10.4 Integrate Scrape into `run`
* **Goal:** `cli.run` performs **scan → scrape → generate** with real data.
* **Tests to Write:**
  - `tests/e2e/test_pipeline_real.py::test_run_full_real_flow`
* **Steps:**
  1. Insert a call to the new `scrape` command inside `cli.run`.
  2. Ensure `generate` reads the scrape cache and populates `<desc>`, `<rating>`, `<marquee>`.
* **Done when:** End-to-end test passes (HTTP mocked).

### 10.5 Error Handling & Retries
* **Goal:** Robust retry logic and graceful fallbacks.
* **Tests to Write:**
  - `tests/unit/test_retry.py::test_retry_logic`
  - `tests/unit/test_scraper.py::test_missing_artwork_placeholder`
* **Steps:**
  1. Add a retry decorator (max 3 attempts, exponential back-off).
  2. If poster/logo unavailable, leave placeholder PNG but still write metadata.
* **Done when:** Tests simulate failures and scraper completes without crashing.

---

## 11 · Sprint 11 (First‑Run Init Wizard)
**Purpose:** Provide a one‑command onboarding flow that validates prerequisites, scaffolds config, and guides users to a working setup.

### 11.1 `init` CLI Command
* **Goal:** Add `python -m mpv_scraper.cli init <library_root>` that performs environment checks and writes config.
* **Tests to Write:**
  - `tests/smoke/test_cli_commands.py::test_init_writes_config`
  - `tests/smoke/test_cli_commands.py::test_init_idempotent`
  - `tests/smoke/test_cli_commands.py::test_init_validates_ffmpeg`
* **Steps:**
  1. Add Click command `init` in `src/mpv_scraper/cli.py`.
  2. Implement utility `validate_prereqs()` in `src/mpv_scraper/utils.py`:
     - Verify `ffmpeg` and `ffprobe` exist via `subprocess.run(["ffmpeg", "-version"])` and `...ffprobe...`.
     - Return dict of versions and a list of warnings.
  3. Create a minimal config file `mpv-scraper.toml` at `<library_root>` containing:
     - `library_root`, `workers`, `preset`, `replace_originals_default`, `regen_gamelist_default`.
  4. Create `.env.example` with `TVDB_API_KEY=` and `TMDB_API_KEY=` placeholders and notes about optional fallbacks.
  5. If `.env` does not exist, copy from `.env.example` (empty values) and print next steps.
  6. Ensure `/Movies` and top‑level `images/` exist; create if missing.
  7. Print a “cheat‑sheet” with recommended commands (optimize, run, undo).
  8. Make command idempotent: never overwrite existing files without `--force`.
* **Done when:** Running `init` creates config and scaffolding, prints versions, exits 0, and re‑running is a no‑op without `--force`.

### 11.2 Config Loading & Defaults
* **Goal:** Load `mpv-scraper.toml` automatically for CLI defaults.
* **Tests to Write:**
  - `tests/smoke/test_cli_commands.py::test_cli_uses_config_defaults`
* **Steps:**
  1. Add `load_config(path: Optional[Path]) -> dict` in `utils.py` (TOML parser; fallback to empty).
  2. In `cli.py`, decorate main group to apply defaults from config when flags are omitted.
  3. Respect precedence: CLI flags > env vars > config file > hardcoded defaults.
* **Done when:** Omitting flags uses values from the config created by `init`.

### 11.3 Documentation
* **Goal:** Add a Guided Setup page and update Quick Start.
* **Tests to Write:** N/A
* **Steps:**
  1. Create `docs/QUICK_START.md` section “First‑run wizard (`init`)”.
  2. Document required tools, environment variables, and fallbacks.
  3. Link from `README.md` usage to the new section.
* **Done when:** Docs clearly explain running `init` and the generated files.

---

## 12 · Sprint 12 (Full TUI Dashboard)
**Purpose:** Provide an interactive terminal UI to manage jobs, view progress, and inspect logs without a full desktop GUI.

### 12.1 TUI Entry Point
* **Goal:** Add `python -m mpv_scraper.cli tui` command.
* **Tests to Write:**
  - `tests/smoke/test_cli_commands.py::test_tui_entrypoint_dry_run`
* **Steps:**
  1. Add dependency `textual>=0.63` (or fallback to `rich` if Textual unavailable) to `requirements.txt`.
  2. Create `src/mpv_scraper/tui.py` with `run_tui(non_interactive: bool = False)`.
  3. In `cli.py`, add `tui` command with `--non-interactive` that starts, renders once, then exits (for tests/CI).
  4. Wire basic layout: sidebar (library paths, queue), main panel (progress tables), bottom panel (logs/status).
* **Done when:** `tui --non-interactive` exits 0 and renders without raising.

### 12.2 Job Queue & Progress Integration
* **Goal:** Control optimize/scrape/generate jobs from the TUI with live progress.
* **Tests to Write:**
  - `tests/integration/test_tui_jobs.py::test_enqueue_optimize_job` (marked `@pytest.mark.integration`)
  - `tests/integration/test_tui_jobs.py::test_cancel_job` (integration)
* **Steps:**
  1. Expose a lightweight job API in `src/mpv_scraper/transaction.py` or a new `jobs.py`:
     - `enqueue(command: Callable, args, kwargs) -> job_id`
     - `observe(job_id) -> progress/events` using existing `progress_callback` hooks.
     - `cancel(job_id)` best‑effort via cooperative flags.
  2. Adapt `parallel_optimize_videos` to post structured progress events (files total/done, current file, ETA).
  3. Render job list and per‑job progress bars in the TUI; add actions: start/pause/cancel.
  4. Persist recent job history to a small JSON file under the library root (`.mpv-scraper/jobs.json`).
* **Done when:** A user can enqueue an optimize job from the TUI, observe progress, and cancel it; events update the UI.

### 12.3 Log Viewer & Error Surfacing
* **Goal:** Provide an in‑TUI log viewer and error drill‑down.
* **Tests to Write:**
  - `tests/integration/test_tui_jobs.py::test_error_event_surfaces_in_ui`
* **Steps:**
  1. Centralize logging to a rotating file `mpv-scraper.log` in the library root.
  2. Add a TUI panel that tails the log and highlights errors/warnings.
  3. On task failures, show a modal with the failing file and an action to retry.
* **Done when:** Errors from background jobs appear in the TUI and can be acknowledged.

### 12.4 Documentation
* **Goal:** Add a “Using the TUI” guide.
* **Tests to Write:** N/A
* **Steps:**
  1. Create `docs/USER_INTERFACE.md` with screenshots/GIFs and keybindings.
  2. Update `README.md` with a short TUI section and link to the guide.
* **Done when:** Docs explain launching the TUI and controlling jobs.

---

## 13 · Sprint 13 (Free/Open Metadata Fallbacks)
**Purpose:** Allow scraping without paid keys by using TVmaze (TV) and OMDb (Movies) as fallbacks.

### 13.1 TVmaze Client (TV Fallback)
* **Goal:** Implement search and series/episode fetch using TVmaze’s public API.
* **Tests to Write:**
  - `tests/integration/test_tvmaze.py::test_search_show`
  - `tests/integration/test_tvmaze.py::test_get_episodes`
  - `tests/integration/test_cache_hits.py::test_tvmaze_cache`
* **Steps:**
  1. Create `src/mpv_scraper/tvmaze.py` with:
     - `search_show(name: str) -> List[dict]`
     - `get_show_episodes(show_id: int) -> List[dict]`
  2. Map TVmaze fields to internal structures used by `scraper.py` (title, season, episode, overview, image URLs, rating if present).
  3. Add simple caching and rate limiting (mirror TVDB/TMDB helpers).
  4. Add selection logic: when TVDB unavailable or `--prefer-fallback`, use TVmaze.
* **Done when:** Mocked tests pass and fallback data flows through `generate`.

### 13.2 OMDb Client (Movie Fallback)
* **Goal:** Provide movie search/details via OMDb; key optional but supported.
* **Tests to Write:**
  - `tests/integration/test_omdb.py::test_search_movie`
  - `tests/integration/test_cache_hits.py::test_omdb_cache`
* **Steps:**
  1. Create `src/mpv_scraper/omdb.py` with:
     - `search_movie(title: str, year: Optional[int]) -> List[dict]`
     - `get_movie_details(omdb_id: str) -> dict`
  2. Load optional `OMDB_API_KEY` from env; if absent, document the limited anonymous mode behavior (if any) or require key.
  3. Map OMDb fields to internal structures (overview, release_date, poster URL, rating normalized to 0–1 if present).
  4. Cache responses and apply rate limiting.
  5. Integrate into `scraper.py`: prefer TMDB; if unavailable or `--prefer-fallback/--fallback-only`, use OMDb.
* **Done when:** Mocked tests pass and movie fallback paths populate XML/images.

### 13.3 CLI Flags & Flow Control
* **Goal:** Expose fallback behavior via flags and config.
* **Tests to Write:**
  - `tests/smoke/test_cli_extended.py::test_generate_with_fallbacks`
* **Steps:**
  1. Add flags to `cli.py`: `--prefer-fallback`, `--fallback-only`, and `--no-remote`.
  2. Respect flags in `run`, `scrape`, and `generate` flows; log provenance of chosen provider.
  3. Extend transaction logging to include provider used per item.
* **Done when:** CLI runs can select providers deterministically and logs reflect the choice.

### 13.4 Documentation
* **Goal:** Clearly document fallbacks and how to run without paid keys.
* **Tests to Write:** N/A
* **Steps:**
  1. Add `docs/FALLBACKS.md` with provider capabilities, limits, and examples.
  2. Update `docs/QUICK_START.md` to mention fallback‑only setup.
  3. Update `README.md` feature list and flags table.
* **Done when:** Users can follow docs to run the tool with fallbacks only.

---

## 14 · Sprint 14 (TUI v1: Colored Interface & Controls)
**Purpose:** Replace the placeholder TUI with a functional, colored interface using Textual/Rich. Show live job progress, tail logs, and provide cancel/retry controls. Expose provider flags from the UI.

### 14.1 Textual App Scaffolding & Layout
* **Goal:** Create a Textual-based app with a stable layout and color theme.
* **Tests to Write:**
  - `tests/smoke/test_tui_textual.py::test_tui_non_interactive_renders`
* **Steps:**
  1. Add `textual>=0.63` to `requirements.txt` (guarded import; fallback prints if unavailable).
  2. Implement `src/mpv_scraper/tui_app.py` with a `Textual` `App` subclass.
  3. Layout: header (title/status), left sidebar (library path and actions), main panel (jobs table), bottom panel (log tail). Apply basic color theme.
  4. Wire `run_tui(non_interactive=True)` to mount the layout, render once, then exit.
* **Done when:** `python -m mpv_scraper.cli tui --non-interactive` renders colored scaffold without exceptions.

### 14.2 Jobs Table with Live Progress
* **Goal:** Display queued/running/completed jobs with progress bars and status.
* **Tests to Write:**
  - `tests/integration/test_tui_jobs.py::test_jobs_table_shows_progress` (marks integration)
* **Steps:**
  1. Subscribe the app to a lightweight update loop (e.g., interval timer) that polls `JobManager.observe(job_id)`.
  2. Render a table: columns = ID, Name, Status, Progress (bar/percent), Message.
  3. Update the table on events; keep <=100 past jobs in memory; persist summary to `.mpv-scraper/jobs.json`.
* **Done when:** Enqueuing a dummy job updates the table from 0% → 100% in the UI during a short demo run.

### 14.3 Log Tail Panel with Highlighting
* **Goal:** Tail `mpv-scraper.log` and highlight INFO/WARN/ERROR with colors.
* **Tests to Write:**
  - `tests/integration/test_tui_logs.py::test_log_tail_renders_lines` (integration)
* **Steps:**
  1. Implement a log reader that seeks the end and reads the last N lines (configurable, default 200).
  2. Color rules: INFO=default, WARNING=yellow, ERROR=red; dim timestamps.
  3. Auto-scroll to latest; provide PageUp/PageDown to browse; preserve scroll on updates.
* **Done when:** Recent lines appear in the panel with correct colors; updates stream in during running jobs.

### 14.4 Actions: Enqueue/Cancel/Retry from TUI
* **Goal:** Provide keyboard actions to control jobs.
* **Tests to Write:**
  - `tests/integration/test_tui_jobs.py::test_cancel_action_updates_status` (integration)
* **Steps:**
  1. Keybindings: `o`=optimize (prompt for dir), `s`=scrape (prompt for dir and provider mode), `g`=generate, `c`=cancel selected job, `r`=retry last failed job, `q`=quit.
  2. Implement prompts via Textual input modals; enqueue background jobs using existing CLI functions via Python callables with `progress_callback`.
  3. On cancel, set the `should_cancel` flag through `JobManager` and reflect `cancelled` status.
* **Done when:** User can start an optimize job and cancel it from within the TUI; status updates correctly.

### 14.5 Provider Mode Controls (Flags from UI)
* **Goal:** Expose provider selection in the TUI for scrape runs.
* **Tests to Write:**
  - `tests/smoke/test_tui_textual.py::test_provider_mode_menu_shows_options`
* **Steps:**
  1. Add a provider mode selector in the sidebar: Primary (default), Prefer Fallback, Fallback Only, Offline.
  2. Pass `--prefer-fallback/--fallback-only/--no-remote` equivalents when enqueuing scrape jobs.
* **Done when:** The selected mode is used for new scrape jobs and is visible in job metadata.

### 14.6 Documentation & Help Overlay
* **Goal:** Document the TUI and provide an in-app help overlay.
* **Tests to Write:** N/A
* **Steps:**
  1. Add a `?` hotkey to show an overlay listing keybindings and provider modes.
  2. Update `docs/USER_INTERFACE.md` with screenshots/GIFs of the new TUI, and a quick how-to for jobs.
* **Done when:** Users can discover controls in-app and docs reflect the colored interface.

---

## 15 · Sprint 15 (Release v1.0.0: PyPI + GitHub)
**Purpose:** Prepare and publish the first stable release, validate packaging on TestPyPI, then publish to PyPI and cut a GitHub Release.

### 15.1 Packaging Hardening & Version Bump
* **Goal:** Make the project PyPI-ready and bump version to `1.0.0`.
* **Tasks:**
  1. Update `setup.py` with `version="1.0.0"`, `python_requires=">=3.9"`, `long_description` from `README.md`, and add `python-dotenv` to `install_requires`.
  2. Add `pyproject.toml` with modern build backend (`setuptools>=61`, `wheel`).
  3. Add `MANIFEST.in` to include README/docs/assets as appropriate.
  4. Ensure console entry point `mpv-scraper` is defined.
* **Done when:** `python -m build` succeeds locally and `twine check dist/*` reports no errors.

### 15.2 Test Suite Smoke Pass
* **Goal:** Verify core CLI commands on current Python.
* **Tasks:**
  1. Install dev deps: `python -m pip install -r requirements-dev.txt`.
  2. Run smoke tests: `python -m pytest -k smoke -q`.
* **Done when:** Smoke tests pass.

### 15.3 Build Artifacts
* **Goal:** Produce clean sdist and wheel.
* **Tasks:**
  1. Install build tools: `python -m pip install --upgrade build twine`.
  2. Build: `python -m build`.
  3. Validate: `twine check dist/*`.
* **Done when:** `.tar.gz` and `.whl` exist under `dist/` and pass checks.

### 15.4 TestPyPI Dry Run
* **Goal:** Validate upload and installation from TestPyPI.
* **Tasks:**
  1. Upload: `twine upload --repository testpypi dist/*`.
  2. Install for verification:
     - `python -m pip install --index-url https://test.pypi.org/simple/ --no-deps mpv-scraper`
     - Run `mpv-scraper --help` to confirm entry point.
* **Done when:** Install works and CLI responds from TestPyPI package.

### 15.5 Open PR and Merge Release Branch
* **Goal:** Create a PR for `release/v1.0.0` → `main`.
* **Tasks:**
  1. Push branch and open PR with changelog summary and release notes.
  2. Ensure CI passes; request review.
  3. Merge via squash or merge commit as preferred.
* **Done when:** Branch is merged to `main` and CI green.

### 15.6 Publish to PyPI and Tag
* **Goal:** Publish to the real PyPI and tag the release.
* **Tasks:**
  1. Rebuild on `main` (optional) or reuse artifacts.
  2. Upload: `twine upload dist/*`.
  3. Create git tag: `git tag -a v1.0.0 -m "v1.0.0" && git push origin v1.0.0`.
* **Done when:** Package visible on PyPI and tag exists on GitHub.

### 15.7 Hardening & Docs
* **Goal:** Improve install UX and document releases.
* **Tasks:**
  1. README/Docs: add `pipx install mpv-scraper` primary path; keep `pip install mpv-scraper` as alternate.
  2. Add an Install/Setup demo script and link from README.
  3. Optional: Add GitHub Release with attached wheel/sdist and changelog.
  4. Optional: Set up Trusted Publisher (GitHub Actions) for future automated releases.
* **Done when:** Docs updated and install path validated end‑to‑end.

---
