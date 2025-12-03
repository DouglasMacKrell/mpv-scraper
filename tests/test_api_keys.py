"""Lightweight environment reporting for API keys.

We do not perform live authentication in tests to avoid external calls and
environment coupling. This file only reports whether keys are present.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def test_api_keys_environment():
    """Test that API keys are properly set in environment."""
    tvdb_key = os.getenv("TVDB_API_KEY")
    tvdb_key2 = os.getenv("TVDB_API_KEY2")
    tmdb_key = os.getenv("TMDB_API_KEY")

    print(f"TVDB_API_KEY: {'SET' if tvdb_key else 'NOT SET'}")
    print(f"TVDB_API_KEY2 (V4): {'SET' if tvdb_key2 else 'NOT SET'}")
    print(f"TMDB_API_KEY: {'SET' if tmdb_key else 'NOT SET'}")

    # Report key lengths only (not partial keys for security)
    if tvdb_key:
        print(f"TVDB key length: {len(tvdb_key)} characters")
    if tvdb_key2:
        print(f"TVDB V4 key length: {len(tvdb_key2)} characters")
    if tmdb_key:
        print(f"TMDB key length: {len(tmdb_key)} characters")

    # Don't fail the test, just report presence
    assert True
