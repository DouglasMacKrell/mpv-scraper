"""Miscellaneous utility helpers for mpv_scraper."""

import functools
import re
import time
from datetime import datetime
from typing import Any, Callable, Final, Type, Union

__all__ = [
    "normalize_rating",
    "retry_with_backoff",
    "format_release_date",
    "normalize_text",
    "validate_prereqs",
    "load_config",
    "get_logger",
]

_MAX_RAW: Final[float] = 10.0


def normalize_rating(raw: Union[float, int, None]) -> float:
    """Convert a 0–10 rating to 0–1, clamped to range.

    Parameters
    ----------
    raw
        Original rating value as returned by TVDB / TMDB (0‒10 scale).

    Returns
    -------
    float
        Rating between 0.0 and 1.0 rounded to two decimals.
    """

    if raw is None:
        return 0.0
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0

    if value < 0:
        value = 0.0
    elif value > _MAX_RAW:
        value = _MAX_RAW

    return round(value / _MAX_RAW, 2)


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Retry decorator with exponential backoff.

    Parameters
    ----------
    max_attempts
        Maximum number of attempts before giving up.
    base_delay
        Base delay in seconds for exponential backoff.
    exceptions
        Tuple of exception types to retry on.

    Returns
    -------
    Callable
        Decorated function that will retry on specified exceptions.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:  # Don't sleep on last attempt
                        delay = base_delay * (2**attempt)  # Exponential backoff
                        time.sleep(delay)

            # If we get here, all attempts failed
            raise last_exception

        return wrapper

    return decorator


def format_release_date(date_str: Union[str, None]) -> Union[str, None]:
    """Convert a date string to EmulationStation format (YYYYMMDDT000000).

    Parameters
    ----------
    date_str
        Date string in YYYY-MM-DD format (e.g., "2023-01-15")

    Returns
    -------
    Union[str, None]
        Date in EmulationStation format (YYYYMMDDT000000) or None if invalid
    """
    if not date_str:
        return None

    try:
        # Parse various date formats
        for fmt in ["%Y-%m-%d", "%Y-%m", "%Y"]:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime("%Y%m%dT000000")
            except ValueError:
                continue
    except Exception:
        pass

    return None


def normalize_text(text: str) -> str:
    """
    Normalize text by replacing special characters with ASCII equivalents.

    This function handles common special characters that can cause display
    issues in various systems, particularly umlauts and other diacritics.

    Args:
        text: The text to normalize

    Returns:
        Normalized text with special characters replaced
    """
    if not text:
        return text

    # Character mapping for common special characters
    char_map = {
        # German umlauts
        "ä": "a",
        "ö": "o",
        "ü": "u",
        "ß": "ss",
        "Ä": "A",
        "Ö": "O",
        "Ü": "U",
        # French accents
        "à": "a",
        "â": "a",
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "î": "i",
        "ï": "i",
        "ô": "o",
        "ù": "u",
        "û": "u",
        "ÿ": "y",
        "À": "A",
        "Â": "A",
        "É": "E",
        "È": "E",
        "Ê": "E",
        "Ë": "E",
        "Î": "I",
        "Ï": "I",
        "Ô": "O",
        "Ù": "U",
        "Û": "U",
        # Spanish characters
        "ñ": "n",
        "Ñ": "N",
        # Scandinavian characters
        "å": "a",
        "æ": "ae",
        "ø": "o",
        "Å": "A",
        "Æ": "AE",
        "Ø": "O",
        # Other common special characters
        "ç": "c",
        "Ç": "C",
        "š": "s",
        "Š": "S",
        "ž": "z",
        "Ž": "Z",
        "č": "c",
        "Č": "C",
        "ć": "c",
        "Ć": "C",
        "ń": "n",
        "Ń": "N",
        "ł": "l",
        "Ł": "L",
        "ś": "s",
        "Ś": "S",
        "ź": "z",
        "Ź": "Z",
        "ż": "z",
        "Ż": "Z",
        # Smart quotes and dashes
        '"': '"',
        """: "'", """: "'",
        "–": "-",
        "—": "-",
        "…": "...",
    }

    # Replace special characters
    normalized = text
    for special, replacement in char_map.items():
        normalized = normalized.replace(special, replacement)

    # Remove any remaining non-ASCII characters that might cause issues
    # Keep basic punctuation and alphanumeric characters
    normalized = re.sub(r"[^\x00-\x7F\s\-\.\,\!\?\&\'\"\(\)]", "", normalized)

    # Clean up multiple spaces
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def validate_prereqs() -> dict:
    """Validate presence of required external tools and return versions.

    Returns
    -------
    dict
        {
          "ok": bool,
          "ffmpeg_version": str | None,
          "ffprobe_version": str | None,
          "warnings": list[str]
        }
    """
    import shutil
    import subprocess

    warnings: list[str] = []

    result = {
        "ok": True,
        "ffmpeg_version": None,
        "ffprobe_version": None,
        "warnings": warnings,
    }

    # Check ffmpeg
    if shutil.which("ffmpeg") is None:
        warnings.append("ffmpeg not found in PATH")
        result["ok"] = False
    else:
        try:
            proc = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
            )
            if proc.returncode == 0:
                # parse first line
                first = (proc.stdout or proc.stderr or "").splitlines()[:1]
                result["ffmpeg_version"] = first[0] if first else "ffmpeg (unknown)"
            else:
                warnings.append("ffmpeg returned non-zero exit status for -version")
        except Exception as exc:
            warnings.append(f"ffmpeg version check failed: {exc}")

    # Check ffprobe
    if shutil.which("ffprobe") is None:
        warnings.append("ffprobe not found in PATH")
        result["ok"] = False
    else:
        try:
            proc = subprocess.run(
                ["ffprobe", "-version"], capture_output=True, text=True, timeout=5
            )
            if proc.returncode == 0:
                first = (proc.stdout or proc.stderr or "").splitlines()[:1]
                result["ffprobe_version"] = first[0] if first else "ffprobe (unknown)"
            else:
                warnings.append("ffprobe returned non-zero exit status for -version")
        except Exception as exc:
            warnings.append(f"ffprobe version check failed: {exc}")

    return result


def load_config(path) -> dict:
    """Load mpv-scraper.toml from given path directory (if present).

    Parameters
    ----------
    path : Path | str
        Directory expected to contain mpv-scraper.toml.

    Returns
    -------
    dict
        Parsed config dict or empty dict if not found/invalid.
    """
    from pathlib import Path

    try:
        import tomllib  # Python 3.11+
    except Exception:  # pragma: no cover
        try:
            import tomli as tomllib  # fallback
        except Exception:
            return {}

    root = Path(path)
    cfg_path = root / "mpv-scraper.toml"
    if not cfg_path.exists():
        return {}
    try:
        return tomllib.loads(cfg_path.read_text())
    except Exception:
        return {}


def get_logger(root_dir=None):
    """Return a configured logger that writes to mpv-scraper.log for ``root_dir``.

    The logger is namespaced by absolute ``root_dir`` so multiple libraries can
    be processed in one session without handler conflicts. If ``root_dir`` is
    None, uses the current working directory.
    """
    import logging
    from logging.handlers import RotatingFileHandler
    from pathlib import Path

    root = Path(root_dir) if root_dir else Path.cwd()
    try:
        root = root.resolve()
    except Exception:
        pass
    log_path = root / "mpv-scraper.log"

    logger_name = f"mpv_scraper[{log_path}]"
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=2)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger
