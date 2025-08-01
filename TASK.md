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

## 4 · Sprint 4 (TMDB Integration)
**Purpose:** Search TMDB and fetch movie metadata.

### 4.1 TMDB Movie Search
* **Goal:** Find movie by title and year. Disambiguation choices are for the current session only.
* **Tests to Write:**
  - `tests/test_tmdb.py::test_search_movie_by_title_year`
  - `tests/test_tmdb.py::test_search_movie_without_year`
* **Steps:**
  1. Load `TMDB_API_KEY` from env; raise if unset.
  2. Implement `search_movie(title, year) -> List[Movie]` using `/search/movie` endpoint.
* **Done when:** Tests pass with mocked TMDB responses.

### 4.2 Fetch Movie Details
* **Goal:** Extract overview, release date, rating, and poster path.
* **Tests to Write:**
  - `tests/test_tmdb.py::test_fetch_movie_details`
* **Steps:**
  1. Implement `get_movie_details(movie_id) -> MovieMeta`.
  2. Convert `vote_average` to 0–1 float.
* **Done when:** Tests validate meta mapping.

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

---
