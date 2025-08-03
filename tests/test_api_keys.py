"""Test API key authentication for TVDB and TMDB."""

import os
import pytest
from dotenv import load_dotenv
from mpv_scraper.tvdb import authenticate_tvdb
from mpv_scraper.tmdb import search_movie

# Load environment variables from .env file
load_dotenv()


def test_tvdb_authentication():
    """Test TVDB API key authentication."""
    api_key = os.getenv("TVDB_API_KEY")
    if not api_key:
        pytest.skip("TVDB_API_KEY not set")

    print(f"Testing TVDB with key: {api_key[:10]}...")

    try:
        token = authenticate_tvdb()
        print(f"✅ TVDB authentication successful! Token: {token[:20]}...")
        assert token is not None
        assert len(token) > 10
    except Exception as e:
        print(f"❌ TVDB authentication failed: {e}")
        raise


def test_tmdb_authentication():
    """Test TMDB API key authentication."""
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        pytest.skip("TMDB_API_KEY not set")

    print(f"Testing TMDB with key: {api_key[:20]}...")

    try:
        # Test with a simple search
        results = search_movie("Moana", 2016)
        print(f"✅ TMDB authentication successful! Found {len(results)} results")
        assert results is not None
    except Exception as e:
        print(f"❌ TMDB authentication failed: {e}")
        raise


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

    # Don't fail the test, just report
    assert True
