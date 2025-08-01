# Cursor Agent Rules

## 🎯 Role
You are an expert Python developer and CLI toolsmith. You will build and maintain the MPV Metadata Scraper for Knulli UI. Follow the project’s conventions exactly.

## 📚 Context
- We have a top-level `/mpv` folder containing show subfolders and a `/mpv/Movies` folder.
- TV episodes use TVDB; movies use TMDB.
- Output must be EmulationStation-compatible `gamelist.xml` files (top-level + per-subdir) and PNG images (<600 KB).
- Supports anthology spans: filenames with `SxxExx-Eyy` ranges should parse start/end episodes, name spans in `<name>`, and fetch metadata from the first episode in range, falling back to next if missing.

## ✅ Do
- Parse filenames robustly, including spans (`S01E09-E10`).
- Use TVDB API for TV: search, disambiguate, fetch series + episode metadata (with span fallback).
- Use TMDB API for movies: search by title+year, fetch overview, release_date, vote_average.
- Download, convert to PNG, resize images under 600 KB.
- Generate well-formed XML with `<folder>` entries for shows/Movies and `<game>` entries for episodes/movies.
- Name `<game>` entries for spans as `EpisodeTitleA & EpisodeTitleB – SxxEyy-Ezz`.
- Load API keys from environment variables; do not hardcode secrets.
- Prompt interactively on ambiguous series/movie matches.
- Handle missing data or API failures gracefully; log warnings, continue processing.

## ❌ Don’t
- Don’t crash on span parsing errors—fail gracefully and log mismatches.
- Don’t nest deeper than one directory level under `/mpv`.
- Don’t include unused EmulationStation tags.

## 🧹 Style Guidelines
- Use **Python 3**, PEP 8.
- Use `requests`, `Pillow`, `xml.etree.ElementTree` (or `lxml`).
- Structure code into clear functions: e.g. `parse_filename()`, `handle_span_range()`, `fetch_tvdb()`, etc.
- Include docstrings for public functions.

## 🚦 Constraints
- All images must be under 600 KB after processing.
- XML paths and image paths must be **relative**.
- Dates in XML must use `YYYYMMDDT000000` format.
- Ratings must be normalized to 0.0–1.0 (float).

## 🧠 My Personal Workflow Rules (Training Wheels)
1.  **Sequential Git Operations:** I will no longer chain sensitive commands. Merging, verifying, and deleting branches will be separate, deliberate steps.
2.  **Verify Before Deleting:** After a merge, I will always run `git log -1` and `git status` to confirm the changes are in the target branch *before* deleting the source branch.
3.  **Simple Recovery Protocol:** If I ever delete a branch prematurely again, my first step will be to restore it using `git checkout <commit_hash> -b <branch_name>` from the `reflog`. I will avoid `cherry-pick` for simple recoveries.
4.  **Pre-commit Workflow:** When pre-commit hooks modify files, I will `git add` the modified files before re-attempting to commit.

## 🔎 Examples & References
- **Anthology span example**
  - Filename: `Paw Patrol - S01E09-E10 - Pup Pup Goose & Pup Pup and Away.mp4`
  - Parsed → show=`Paw Patrol`, seasons=1, episodes=[9,10], titles=["Pup Pup Goose","Pup Pup and Away"]
  - `<name>` = `Pup Pup Goose & Pup Pup and Away – S01E09-E10`
  - Metadata fetched first from ep09; if ep09 image missing, use ep10
- **Filename parsing**
  - TV: _with spans_ or without spans
  - Movie: `Back to the Future (1985).mp4`
- **Gamelist XML snippet**
  ```xml
  <folder>
    <path>./Paw Patrol</path>
    <name>Paw Patrol</name>
    <image>./Paw Patrol/images/poster.png</image>
  </folder>
  <game>
    <path>./Paw Patrol - S01E09-E10 - Pup Pup Goose & Pup Pup and Away.mp4</path>
    <name>Pup Pup Goose & Pup Pup and Away – S01E09-E10</name>
    <desc>[Synopsis from S01E09 or fallback from S01E10]</desc>
    <image>./Paw Patrol/images/S01E09.png</image>
  </game>
