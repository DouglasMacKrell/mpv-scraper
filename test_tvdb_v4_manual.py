#!/usr/bin/env python3
# ruff: noqa: E402
"""Manual test script for TVDB API V4 client.

This script performs live API calls to verify the V4 client is working correctly.
Run this script to test your TVDB_API_KEY2 configuration.

Usage:
    python test_tvdb_v4_manual.py
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from mpv_scraper.tvdb import authenticate_tvdb, search_show, get_series_extended


def verify_authentication():
    """Test V4 API authentication."""
    print("=" * 60)
    print("Testing TVDB V4 API Authentication")
    print("=" * 60)

    try:
        token = authenticate_tvdb()
        print("✅ Authentication successful!")
        print(f"   Token: {token[:20]}... (length: {len(token)})")
        return token
    except ValueError as e:
        print(f"❌ Authentication failed: {e}")
        print("\nMake sure TVDB_API_KEY2 is set in your .env file")
        return None
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None


def verify_search(show_name: str = "The Simpsons"):
    """Test V4 API search functionality."""
    print("\n" + "=" * 60)
    print(f"Testing TVDB V4 API Search: '{show_name}'")
    print("=" * 60)

    token = authenticate_tvdb()
    if not token:
        return None

    try:
        results = search_show(show_name, token)
        print(f"✅ Search successful! Found {len(results)} results")

        if results:
            print("\nTop results:")
            for i, result in enumerate(results[:5], 1):
                result_id = result.get("id", "N/A")
                result_name = result.get("name") or result.get("seriesName", "Unknown")
                result_year = result.get("year") or result.get("firstAired", "N/A")
                print(f"  {i}. {result_name} (ID: {result_id}, Year: {result_year})")

            return results[0]["id"] if results else None
        else:
            print("⚠️  No results found")
            return None
    except Exception as e:
        print(f"❌ Search failed: {e}")
        import traceback

        traceback.print_exc()
        return None


def verify_series_extended(series_id):
    """Test V4 API series extended information retrieval."""
    print("\n" + "=" * 60)
    print(f"Testing TVDB V4 API Series Extended: ID {series_id}")
    print("=" * 60)

    token = authenticate_tvdb()
    if not token:
        return None

    try:
        series_info = get_series_extended(series_id, token)

        if series_info:
            print("✅ Series information retrieved successfully!")
            print("\nSeries Details:")
            print(f"  ID: {series_info.get('id', 'N/A')}")
            print(f"  Name: {series_info.get('name', 'N/A')}")
            print(f"  Overview: {series_info.get('overview', 'N/A')[:100]}...")
            print(f"  Rating: {series_info.get('siteRating', 'N/A')}")
            print(f"  Episodes: {len(series_info.get('episodes', []))}")

            if series_info.get("episodes"):
                print("\nFirst few episodes:")
                for ep in series_info["episodes"][:5]:
                    season = ep.get("seasonNumber") or ep.get("season") or "?"
                    number = ep.get("number") or ep.get("episode") or "?"
                    name = ep.get("episodeName") or ep.get("name") or "Unknown"
                    # Handle None values for formatting
                    try:
                        if isinstance(season, (int, float)) and isinstance(
                            number, (int, float)
                        ):
                            print(f"  S{int(season):02d}E{int(number):02d}: {name}")
                        else:
                            print(f"  S{season}E{number}: {name}")
                    except (TypeError, ValueError):
                        print(f"  S{season}E{number}: {name}")

            return series_info
        else:
            print("❌ Series information not found")
            return None
    except Exception as e:
        print(f"❌ Series extended failed: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TVDB API V4 Manual Test Script")
    print("=" * 60)

    # Check environment variables
    tvdb_key2 = os.getenv("TVDB_API_KEY2")
    tvdb_key = os.getenv("TVDB_API_KEY")

    print("\nEnvironment Check:")
    print(f"  TVDB_API_KEY2: {'✅ SET' if tvdb_key2 else '❌ NOT SET'}")
    print(f"  TVDB_API_KEY:  {'✅ SET (fallback)' if tvdb_key else '❌ NOT SET'}")

    if not tvdb_key2 and not tvdb_key:
        print("\n❌ No TVDB API key found!")
        print("   Please set TVDB_API_KEY2 in your .env file")
        return 1

    # Test authentication
    token = verify_authentication()
    if not token:
        return 1

    # Test search
    series_id = verify_search("The Simpsons")
    if not series_id:
        print("\n⚠️  Search test completed but no series ID returned")
        return 0

    # Test series extended
    series_info = verify_series_extended(series_id)
    if not series_info:
        print("\n⚠️  Series extended test completed but no data returned")
        return 0

    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
