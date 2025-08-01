# Plex Naming Conventions

This document summarizes the standard Plex naming conventions for TV shows and movies, as outlined in their official documentation. Our scraper will be designed to parse filenames that adhere to these standards.

## Basic Structure

Plex strongly recommends separating media types into distinct root folders.

```
/Media
   /Movies
      movie content...
   /TV Shows
      television content...
```

## TV Shows

Reference: [Plex: Naming and Organizing Your TV Show Files](https://support.plex.tv/articles/naming-and-organizing-your-tv-show-files/)

### Standard Season-Based Shows

The most critical part is the `sXXeYY` notation for season and episode.

**Folder Structure:**
```
/TV Shows/Show Name (Year)/Season XX/
```

**File Naming:**
```
Show Name (Year) - sXXeYY - Optional Episode Title.ext
```

*   **Show Name (Year):** The show's title, with the release year in parentheses, is recommended for accuracy (e.g., `The Office (US) (2005)`).
*   **sXXeYY:** Season and episode numbers, with leading zeros (e.g., `s01e01`).
*   **Separators:** Dashes, dots, or spaces are all acceptable.
*   **Optional Info:** Text after the episode number is considered optional and is ignored by Plex for matching purposes, but can be used for metadata hints.

### Multi-Episode Files (Spans)

For files containing more than one episode, a range format is used. This is the format our tool refers to as an "anthology span."

**File Naming:**
```
Show Name (Year) - sXXeYY-eZZ - Optional Titles.ext
```
*Example:* `Grey's Anatomy (2005) - s02e01-e03.avi`

Plex will list each episode individually, but playing any of them will play the entire file. Our tool will create a combined title for these spans (e.g., `Episode A & Episode B – s01e01-e02`).

### Specials

Specials should be placed in a `Season 00` or `Specials` folder.

**File Naming:**
```
Show Name (Year) - s00eXX - Special Title.ext
```

### Date-Based Shows

For daily shows like news or talk shows.

**File Naming:**
```
Show Name - YYYY-MM-DD - Optional Title.ext
```

## Movies

Reference: [Plex: Naming and organizing your Movie files](https://support.plex.tv/articles/naming-and-organizing-your-movie-media-files/)

### Standard Movie Naming

It is recommended to place each movie in its own folder.

**Folder Structure:**
```
/Movies/Movie Name (Year)/
```

**File Naming:**
```
Movie Name (Year).ext
```
*Example:* `/Movies/Avatar (2009)/Avatar (2009).mkv`

### Match Hinting

To improve accuracy, you can include the IMDb or TMDB ID in the folder and filename.

**Format:**
```
Movie Name (Year) {source-id}.ext
```
*Example:* `Batman Begins (2005) {tmdb-272}.mp4`

Our tool will parse the title and year, and the scraper will use that information to find the correct ID from the API.
