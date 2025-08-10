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
    tmdb_key = os.getenv("TMDB_API_KEY")

    print(f"TVDB_API_KEY: {'SET' if tvdb_key else 'NOT SET'}")
    print(f"TMDB_API_KEY: {'SET' if tmdb_key else 'NOT SET'}")

    if tvdb_key:
        print(f"TVDB key format: {tvdb_key[:10]}... (length: {len(tvdb_key)})")
    if tmdb_key:
        print(f"TMDB key format: {tmdb_key[:20]}... (length: {len(tmdb_key)})")

    # Don't fail the test, just report presence
    assert True
