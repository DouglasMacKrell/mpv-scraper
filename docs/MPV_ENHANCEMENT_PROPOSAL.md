# MPV System Enhancement Proposal

## Current State
KNULLI's MPV system currently functions as a basic media player that:
- Accepts video files in `/userdata/roms/mpv/`
- Provides basic playback controls
- Displays files as simple list entries
- Does not support metadata scraping or rich UI

## Proposed Enhancement
Transform MPV into a full EmulationStation system with rich metadata support.

## Key Benefits
1. **Consistent User Experience** - MPV would work like other EmulationStation systems
2. **Rich Metadata Display** - Show descriptions, ratings, release dates, etc.
3. **Image Assets** - Display posters, logos, thumbnails, and fan art
4. **Organized Structure** - Support nested folders with proper gamelist.xml files
5. **Scraping Integration** - Use EmulationStation's built-in scraping tools

## Technical Implementation

### 1. System Configuration
Create `/System/configs/emulationstation/es_systems_mpv.cfg`:
```xml
<?xml version="1.0"?>
<systemList>
  <system>
        <fullname>Media Player</fullname>
        <name>mpv</name>
        <manufacturer>Media</manufacturer>
        <release>0000</release>
        <hardware>media</hardware>
        <path>/userdata/roms/mpv</path>
        <extension>.mp4 .avi .mkv .mov .wmv .flv .webm .m4v .3gp .ogv .ts .mts .m2ts</extension>
        <command>emulatorlauncher %CONTROLLERSCONFIG% -system %SYSTEM% -rom %ROM% -gameinfoxml %GAMEINFOXML% -systemname %SYSTEMNAME%</command>
        <platform>media</platform>
        <theme>mpv</theme>
        <emulators>
            <emulator name="mpv">
                <cores>
                    <core default="true">mpv</core>
                </cores>
            </emulator>
        </emulators>
  </system>
</systemList>
```

### 2. EmulatorLauncher Integration
- **Preserve existing control mapping** - Uses the same `emulatorlauncher` system as current MPV
- **Maintain handheld controls** - All existing MPV controls (Start, Select, D-pad, etc.) continue to work
- **Add metadata support** - Pass metadata via `%GAMEINFOXML%` parameter
- **No control changes** - Users will have the exact same playback experience

### 3. Metadata Structure
Support standard EmulationStation metadata fields:
- `name` - Display name
- `desc` - Description/synopsis
- `rating` - User rating (0.0-1.0)
- `releasedate` - Release date (YYYYMMDDT000000)
- `developer` - Production company
- `publisher` - Studio/distributor
- `genre` - Content type (TV Show, Movie, etc.)
- `image` - Poster image
- `marquee` - Logo image
- `box` - Box art
- `thumbnail` - Thumbnail image
- `fanart` - Background image

### 4. Directory Structure
```
/userdata/roms/mpv/
├── gamelist.xml                    # Top-level gamelist
├── images/                         # Top-level images
│   ├── Movies-poster.png
│   ├── Movies-marquee.png
│   └── Movies-box.png
├── Movies/                         # Movie folder
│   ├── gamelist.xml               # Movie-specific gamelist
│   ├── images/                    # Movie-specific images
│   │   ├── Movie Title (2023)-image.png
│   │   ├── Movie Title (2023)-marquee.png
│   │   └── Movie Title (2023)-box.png
│   └── Movie Title (2023).mp4
└── TV Show Name/                   # TV show folder
    ├── gamelist.xml               # Show-specific gamelist
    ├── images/                    # Show-specific images
    │   ├── TV Show Name-marquee.png
    │   ├── TV Show Name-box.png
    │   ├── S01E01 - Episode Title-image.png
    │   └── S01E01 - Episode Title-marquee.png
    └── TV Show Name - S01E01 - Episode Title.mp4
```

### 5. Scraping Sources
- **TV Shows**: TheTVDB.com (primary), TMDB.org (fallback)
- **Movies**: TMDB.org (primary), OMDB API (fallback)
- **Additional Sources**: FanartTV, AniDB (for anime)

### 6. Image Naming Conventions
- `-image.png` - Main poster/cover image
- `-marquee.png` - Logo/clear logo
- `-box.png` - Box art/alternative cover
- `-thumb.png` - Thumbnail image
- `-fanart.png` - Background image

## Implementation Steps

### Phase 1: System Configuration
1. Create `es_systems_mpv.cfg`
2. Test basic system recognition
3. Verify file loading and playback

### Phase 2: Metadata Integration
1. Implement gamelist.xml generation
2. Add image asset support
3. Test metadata display in UI

### Phase 3: Scraping Enhancement
1. Integrate with existing scraping tools
2. Add TVDB/TMDB API support
3. Implement fallback mechanisms

### Phase 4: Advanced Features
1. Support for anthology episodes (S01E01-E02)
2. Multi-language metadata
3. Custom themes and layouts

## Backward Compatibility
- **Existing MPV files continue to work** - No changes to file compatibility
- **All handheld controls preserved** - Start, Select, D-pad, shoulder buttons work exactly as before
- **Same playback experience** - Users won't notice any difference in how they control MPV
- **Gradual migration to enhanced features** - Metadata is optional and doesn't affect playback

## User Experience Improvements
1. **Rich Browsing** - See posters, descriptions, ratings
2. **Organized Content** - Group by shows, movies, genres
3. **Search & Filter** - Find content by title, genre, rating
4. **Favorites** - Mark and organize favorite content
5. **Playlists** - Create custom playlists and collections

## Technical Considerations
- Maintain existing MPV controls and hotkeys
- Preserve performance for large media libraries
- Support for various video formats and codecs
- Handle missing metadata gracefully
- Cache scraping results for offline use

## Future Enhancements
- Integration with external media servers (Plex, Jellyfin)
- Automatic subtitle downloading
- Audio track selection and management
- Video quality selection and transcoding
- Social features (ratings, reviews, recommendations)

This enhancement would transform KNULLI's MPV system from a basic media player into a full-featured media management system that rivals dedicated media center applications while maintaining the simplicity and performance that users expect from KNULLI.
