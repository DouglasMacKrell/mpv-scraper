# Error Handling Guide

Understanding how the MPV Scraper handles failures and implements graceful fallbacks.

## 🛡️ Error Handling Flow

```mermaid
flowchart TD
    A[Operation Starts] --> B{Success?}

    B -->|Yes| C[Continue]
    B -->|No| D{Error Type?}

    D -->|Network Error| E[Retry Logic]
    D -->|API Error| F[Fallback Strategy]
    D -->|File Error| G[Skip & Log]
    D -->|Parse Error| H[Use Defaults]

    E --> I[Exponential Backoff]
    I --> J[Retry 3 Times]
    J --> K{Retry Success?}
    K -->|Yes| C
    K -->|No| F

    F --> L{API Available?}
    L -->|TVDB Failed| M[Try TMDB]
    L -->|TMDB Failed| N[Generate Screenshot]
    L -->|Both Failed| O[Create Placeholder]

    M --> P{TMDB Success?}
    P -->|Yes| C
    P -->|No| N

    N --> Q[Capture Video Frame]
    O --> R[Create Basic Image]

    Q --> C
    R --> C

    C --> S[Log Result]
    S --> T[Continue Processing]

    style C fill:#c8e6c9
    style A fill:#e3f2fd
    style D fill:#ffcdd2
```

## Retry Logic

### Retry Decorator

The `retry_with_backoff` decorator provides automatic retry functionality with exponential backoff:

```python
@retry_with_backoff(max_attempts=3, base_delay=1.0, exceptions=(requests.RequestException,))
def download_image(url: str, dest: Path) -> None:
    # Function implementation
```

**Parameters:**
- `max_attempts`: Maximum number of retry attempts (default: 3)
- `base_delay`: Base delay in seconds for exponential backoff (default: 1.0)
- `exceptions`: Tuple of exception types to retry on (default: all exceptions)

**Backoff Strategy:**
- Attempt 1: Immediate execution
- Attempt 2: Wait 1 second
- Attempt 3: Wait 2 seconds
- Final failure: Raise the last exception

### Applied Functions

The retry decorator is applied to network-dependent functions:

- `download_image()` - Retries on `requests.RequestException`
- `download_marquee()` - Retries on `requests.RequestException`

## Error Handling in Scraper Functions

### TV Show Scraping (`scrape_tv`)

The TV show scraper handles failures gracefully:

```python
# Poster download with fallback
if poster_url:
    try:
        download_image(poster_url, images_dir / "poster.png")
    except Exception:
        # Create placeholder if poster download fails
        create_placeholder_png(images_dir / "poster.png")

# Logo download with fallback
if logo_url:
    try:
        download_marquee(logo_url, images_dir / "logo.png")
    except Exception:
        # Create placeholder if logo download fails
        create_placeholder_png(images_dir / "logo.png")
```

### Movie Scraping (`scrape_movie`)

Similar error handling is implemented for movie scraping:

```python
# Poster download with fallback
if poster_path:
    try:
        download_image(poster_url, images_dir / f"{movie_meta.title}.png")
    except Exception:
        # Create placeholder if poster download fails
        create_placeholder_png(images_dir / f"{movie_meta.title}.png")
```

## Placeholder Images

When artwork downloads fail, the scraper automatically creates transparent placeholder PNG images:

- **Size**: 1x1 pixel transparent PNG
- **Purpose**: Ensures XML generation can proceed without missing image references
- **Location**: Same path as the intended artwork
- **Compliance**: Meets EmulationStation size requirements (≤600 KB)

## Partial Failure Handling

The scraper continues processing even when individual operations fail:

1. **Metadata First**: API calls for metadata are prioritized over artwork downloads
2. **Cache Preservation**: Scrape cache is created even if some artwork downloads fail
3. **XML Generation**: XML files are generated with available metadata and artwork
4. **Transaction Logging**: All successful operations are logged for potential undo

## Common Failure Scenarios

### Network Failures
- **Symptom**: `requests.RequestException` or timeout errors
- **Handling**: Automatic retry with exponential backoff
- **Fallback**: Placeholder images if all retries fail

### Missing Artwork
- **Symptom**: 404 errors or missing URLs in API responses
- **Handling**: Skip download, create placeholder
- **Impact**: Minimal - metadata still captured

### API Rate Limiting
- **Symptom**: 429 status codes
- **Handling**: Retry after backoff delay
- **Note**: Built-in rate limiting in TVDB/TMDB clients

### Invalid Image Data
- **Symptom**: `PIL.UnidentifiedImageError`
- **Handling**: Create placeholder image
- **Impact**: Metadata preserved, artwork missing

## Monitoring and Debugging

### Logging
The scraper provides feedback on operations:
- Success messages: `✓ Scraped Show Name`
- Failure messages: `✗ Failed to scrape Show Name: Error message`

### Transaction Log
All file operations are logged in `transaction.log` for:
- Audit trail of changes
- Undo functionality
- Debugging failed operations

## Best Practices

1. **Check Logs**: Review CLI output for any failure messages
2. **Verify Placeholders**: Look for 1x1 pixel transparent images indicating download failures
3. **Network Stability**: Ensure stable internet connection for best results
4. **API Limits**: Be aware of TVDB/TMDB rate limits for large libraries

## Testing Error Handling

The error handling is thoroughly tested with:
- Unit tests for retry logic (`tests/test_retry.py`)
- Integration tests for graceful failures (`tests/test_scraper.py`)
- End-to-end tests with mocked failures

Run tests with: `pytest tests/test_retry.py tests/test_scraper.py`
