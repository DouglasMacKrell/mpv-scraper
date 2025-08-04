#!/usr/bin/env python3
"""Debug script to test TVDB logo fetching."""

from mpv_scraper.tvdb import authenticate_tvdb, search_show, get_series_extended


def test_darkwing_duck():
    """Test Darkwing Duck logo fetching."""
    print("Testing Darkwing Duck logo fetching...")

    # Authenticate
    token = authenticate_tvdb()
    print("✓ Authenticated with TVDB")

    # Search for show
    results = search_show("Darkwing Duck", token)
    print(f"✓ Found {len(results)} search results")

    if not results:
        print("❌ No search results found")
        return

    # Get extended record
    record = get_series_extended(results[0]["id"], token)
    if not record:
        print("❌ No extended record found")
        return

    print(f"✓ Got extended record for: {record.get('name')}")

    # Check logo URL
    logo_url = record.get("artworks", {}).get("clearLogo")
    print(f"Logo URL: {logo_url}")

    # Check poster URL
    poster_url = record.get("image")
    print(f"Poster URL: {poster_url}")

    # Check episode count
    episodes = record.get("episodes", [])
    print(f"Episode count: {len(episodes)}")

    # Check episodes with images
    episodes_with_images = [ep for ep in episodes if ep.get("image")]
    print(f"Episodes with images: {len(episodes_with_images)}")


if __name__ == "__main__":
    test_darkwing_duck()
