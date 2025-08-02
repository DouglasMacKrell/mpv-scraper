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
