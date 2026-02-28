# Changelog

## [1.3.0] - 2026-02-28
### Fixed
- **optimize-parallel**: Pre-replace validation—verify output with ffprobe before replacing originals (prevents corrupt files from truncated writes)
- **optimize-parallel**: Skip loudnorm for codec-only audio passes (DTS/AC3→AAC); use loudnorm only for quiet audio—fixes 30+ min hangs
- **optimize-parallel**: Real-time feedback—echo each completed filename and loudnorm timing note
- **optimize-parallel**: Improved ffprobe error logging (`-v error`) so failures show actual reason (e.g. "moov atom not found")
- **Scraper**: Fix IndexError when user enters API ID after TVDB search fails (empty search_results)
- **Title normalization**: Strip (Dub), (Sub), (1080p), etc. before API search—fixes "The Irresponsible Captain Tylor (Dub)" and similar

### Added
- `verify_video_output_valid()` to catch truncated/corrupt output before replace
- `_normalize_title_for_search()` for TV and movie search
- `completion_callback` for per-file progress during optimization

## [1.2.0] - 2026-01-04
### Added
- **ES-DE Video Previews**: 30-second preview clips from the 25% mark for gamelist integration (`/mpv/videos/`, `--no-previews` to skip)
- **Audio compatibility**: Part of handheld check—audio-only pass for incompatible codecs (DTS/AC3 → AAC) and quiet videos (< -20 LUFS → -14 LUFS)
- **`optimize-parallel`**: `-y/--yes` to auto-confirm destructive actions; `--regen-gamelist` to regenerate gamelist.xml after optimization
- **Progress bars**: Two-phase flow (analysis then optimization) with determinate bar; non-TTY fallback (`Analyzing N/total`, `Optimized N/total`)
- **TVDB logos**: ClearLogo via `/v4/series/{id}/extended?meta=artworks`; `--refresh` bypasses TVDB cache for fresh logo fetches
- API keys acquisition guide for first-time users

### Fixed
- TVDB 401 handling: auto-refresh token on expiry in `search_show` and `get_series_extended`
- AppleDouble (`._`) files filtered from episode lists to avoid ffprobe warnings
- Video preview clips use even dimensions for libx264 compatibility
- CI: Python 3.9 type hints, artifact naming, pre-commit alignment with pipeline

### Changed
- Parallel optimizer deletes originals incrementally (post-validation) with atomic replace to preserve filenames
- `optimize-parallel` skips already-compatible files; shows "All N already compatible" or skipped count
- Improved prompts, screenshot timing, timeouts, and image source reporting

### Removed
- Debug scripts (`debug_tvdb.py`, `debug_tvdb_logos.py`, `test_tvdb_v4_manual.py`)

## [1.1.0] - 2025-12-05
### Added
- Sprint 5.2 image resize/compress utility (`ensure_png_size`).
- Documentation updates in README and QUICK_START (image handling).
- Folder entries in gamelist.xml now support `marquee` field for series logos.
- Enhanced episode matching to handle shows with `seasonNumber=None` (e.g., Super Kitties).
- Improved TVDB V4 artwork fetching to prefer `screencap` type over `thumbnail`.
- Screenshot timing improvements to skip intro/logo sequences (minimum 30 second skip).

### Fixed
- Fixed Super Kitties episode images not being fetched due to `seasonNumber=None` matching issue.
- Fixed folder entries missing series logos in gamelist.xml.
- Fixed episode images defaulting to series poster when episode images were available.
- Fixed screenshot capture timing to avoid capturing logo frames during theme songs.
- Improved TVDB V4 API artwork endpoint handling for episode images.
