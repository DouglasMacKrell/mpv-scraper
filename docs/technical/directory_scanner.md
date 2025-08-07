# Documentation: Directory Scanner

## 1. Overview

The Directory Scanner is the initial entrypoint for the `mpv-scraper` workflow. Its primary responsibility is to traverse a given root directory (e.g., `/mpv`), identify all relevant media files and folders, and organize them into a structured format that downstream modules can process.

The scanner differentiates between two main content types:
- **TV Shows:** Assumed to be organized into their own subdirectories (e.g., `/mpv/Paw Patrol/`).
- **Movies:** Assumed to be located together within a dedicated `Movies` folder (e.g., `/mpv/Movies/`).

## 2. Core Functionality

The main function for this module is `scanner.scan_directory(path)`.

### Input
- `path` (`Path`): A `pathlib.Path` object pointing to the root directory to be scanned.

### Output
A `ScanResult` object (defined in `mpv_scraper.types`) with the following structure:
```python
@dataclass
class ScanResult:
    shows: List[ShowDirectory]
    movies: List[MovieFile]
```
- `shows`: A list of `ShowDirectory` objects, each representing a folder identified as a TV show.
- `movies`: A list of `MovieFile` objects, each representing a file found in the `Movies` directory.

### Data Structures

- `ShowDirectory(path: Path, files: List[Path])`:
  - `path`: The absolute path to the show's directory.
  - `files`: A list of all media files found within that directory.
- `MovieFile(path: Path)`:
  - `path`: The absolute path to the movie file.

## 3. Implementation Details

### File Traversal
The scanner performs a **one-level-deep** search from the root path. It iterates through each item in the root directory:
- If an item is a directory and its name is **not** `Movies`, it is treated as a TV Show directory. The scanner then lists all files directly within it.
- If an item is a directory and its name **is** `Movies`, the scanner iterates through all files within it, treating each one as a movie file.
- It explicitly ignores dotfiles (e.g., `.DS_Store`) and any non-media files based on a list of supported extensions (e.g., `.mkv`, `.mp4`).

### Error Handling
- The function will raise a `FileNotFoundError` if the provided root path does not exist.
- It logs warnings for any subdirectories that are empty or contain no valid media files but does not raise an error.

## 4. Usage Example

```python
from pathlib import Path
from mpv_scraper.scanner import scan_directory

# Define the root directory to scan
media_root = Path("/path/to/your/mpv")

# Run the scanner
try:
    scan_result = scan_directory(media_root)

    # Process the results
    print("TV Shows Found:")
    for show in scan_result.shows:
        print(f"- {show.path.name} ({len(show.files)} episodes)")

    print("\nMovies Found:")
    for movie in scan_result.movies:
        print(f"- {movie.path.name}")

except FileNotFoundError:
    print(f"Error: The directory '{media_root}' was not found.")
```

This structured approach ensures that the rest of the application receives a predictable and well-organized list of media to process, separating concerns cleanly between scanning and parsing.

# Directory Scanner

Understanding how the MPV Scraper discovers and categorizes media files in your directory structure.

## 🔍 Directory Scanning Flow

```mermaid
flowchart TD
    A[Start Scan] --> B[Read Directory]
    B --> C[Filter Media Files]
    C --> D{File Type?}

    D -->|Video File| E[Parse Filename]
    D -->|Non-Video| F[Skip File]

    E --> G{Parse Success?}
    G -->|Yes| H[Extract Metadata]
    G -->|No| I[Log Parse Error]

    H --> J{Show or Movie?}
    J -->|TV Show| K[Add to Shows List]
    J -->|Movie| L[Add to Movies List]
    J -->|Unknown| M[Add to Unknown List]

    I --> N[Add to Parse Errors]

    F --> O[Continue Scanning]
    K --> O
    L --> O
    M --> O
    N --> O

    O --> P{More Files?}
    P -->|Yes| B
    P -->|No| Q[Generate Summary]

    Q --> R[Return Results]

    style A fill:#e3f2fd
    style R fill:#c8e6c9
    style F fill:#ffcdd2
    style I fill:#ffcdd2
```

## File Discovery
