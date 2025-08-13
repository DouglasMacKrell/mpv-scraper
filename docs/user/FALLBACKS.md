# Fallback Providers

This project supports free/open fallbacks so you can scrape without paid keys or when primary services are unavailable.

## TV (shows)
- Primary: TVDB (requires `TVDB_API_KEY`)
- Fallback: TVmaze (no key required)

## Movies
- Primary: TMDB (requires `TMDB_API_KEY`)
- Fallback: OMDb (requires `OMDB_API_KEY`)

## How selection works
- Default: prefer primaries when their keys are set. If a key is missing, we do not call that API.
- Flags to control behavior:
  - `--prefer-fallback`: try TVmaze/OMDb first, then primaries if needed.
  - `--fallback-only`: only use TVmaze/OMDb. Skip TVDB/TMDB entirely.
  - `--no-remote`: make no network calls. Use cache/placeholders only.

## Examples
```bash
# Run using only fallbacks (no TVDB/TMDB), useful without paid keys
python -m mpv_scraper.cli scrape /mpv --fallback-only

# Prefer TVmaze/OMDb first, but still allow TVDB/TMDB if needed
python -m mpv_scraper.cli scrape /mpv --prefer-fallback

# Do a dry, offline pass: write placeholders and cache-only
python -m mpv_scraper.cli scrape /mpv --no-remote
```

## Notes
- We apply a small delay per HTTP request and cache responses to be polite to providers.
- We never attempt a provider that requires a missing key.
