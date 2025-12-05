# Changelog

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
