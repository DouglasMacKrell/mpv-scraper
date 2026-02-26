#!/usr/bin/env python3
"""Debug script to inspect TVDB logo/artwork API responses.

Run: python debug_tvdb_logos.py
Clears TVDB series cache and tests logo fetch for Popeye, Big Guy, etc.
"""

import glob
import json
import os
import sys


def main():
    # Setup path and env before importing mpv_scraper
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
    from dotenv import load_dotenv

    load_dotenv()

    from mpv_scraper.tvdb import authenticate_tvdb, get_series_extended, search_show
    import requests

    cache_dir = os.path.expanduser("~/.cache/mpv-scraper")

    def clear_series_cache():
        for f in glob.glob(os.path.join(cache_dir, "series_*_extended.json")):
            try:
                os.remove(f)
                print(f"Removed cache: {f}")
            except OSError:
                pass

    clear_series_cache()

    token = authenticate_tvdb()
    print("✓ Authenticated\n")

    # Jellystone! (2021)
    print("=== Jellystone (2021) ===")
    results = search_show("Jellystone", token)
    if not results:
        print("No search results")
        return
    jelly = next(
        (
            r
            for r in results
            if "2021" in str(r.get("firstAired", "") or r.get("year", ""))
        ),
        results[0],
    )
    sid = jelly.get("id") or jelly.get("tvdb_id")
    if str(sid).startswith("series-"):
        sid = int(sid.replace("series-", ""))
    print(f"Series ID: {sid} ({jelly.get('name')})\n")

    print("  Trying /v4/series/{id}/extended?meta=artworks ...")
    r = requests.get(
        f"https://api4.thetvdb.com/v4/series/{sid}/extended",
        headers={"Authorization": f"Bearer {token}"},
        params={"meta": "artworks"},
        timeout=10,
    )
    ext = (
        r.json()
        if r.headers.get("content-type", "").startswith("application/json")
        else {}
    )
    ext_data = ext.get("data", {})
    if "artworks" in ext_data:
        arts = ext_data["artworks"]
        clearlogos = [
            a
            for a in arts
            if isinstance(a, dict)
            and (a.get("type") == 23 or "clearlogo" in str(a.get("slug", "")).lower())
        ]
        print(f"    Got {len(arts)} artworks, {len(clearlogos)} ClearLogos")
        if clearlogos:
            print(f"    First ClearLogo: {json.dumps(clearlogos[0], indent=2)}")
    else:
        print(f"    Top-level keys: {list(ext_data.keys())}")
    print()

    # The Bullwinkle Show
    print("\n=== The Bullwinkle Show ===")
    results2 = search_show("Bullwinkle", token)
    if not results2:
        print("No search results")
        return
    bull = results2[0]
    sid2 = bull.get("id") or bull.get("tvdb_id")
    if str(sid2).startswith("series-"):
        sid2 = int(sid2.replace("series-", ""))
    print(f"Series ID: {sid2} ({bull.get('name')})\n")

    print("  Trying /v4/series/{id}/extended?meta=artworks ...")
    r2 = requests.get(
        f"https://api4.thetvdb.com/v4/series/{sid2}/extended",
        headers={"Authorization": f"Bearer {token}"},
        params={"meta": "artworks"},
        timeout=10,
    )
    ext2 = (
        r2.json()
        if r2.headers.get("content-type", "").startswith("application/json")
        else {}
    )
    ext_data2 = ext2.get("data", {})
    if "artworks" in ext_data2:
        arts2 = ext_data2["artworks"]
        clearlogos2 = [
            a
            for a in arts2
            if isinstance(a, dict)
            and (
                a.get("type") == 23
                or a.get("artworkTypeId") == 23
                or "clearlogo" in str(a.get("slug", "")).lower()
            )
        ]
        print(f"    Got {len(arts2)} artworks, {len(clearlogos2)} ClearLogos")
        if clearlogos2:
            print(f"    First ClearLogo: {json.dumps(clearlogos2[0], indent=2)}")
    else:
        print(f"    Top-level keys: {list(ext_data2.keys())}")
    print()

    # Artwork types
    print("\n=== Artwork Types (from /artwork/types) ===")
    r = requests.get(
        "https://api4.thetvdb.com/v4/artwork/types",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if r.status_code == 200:
        types_data = r.json()
        types_list = types_data.get("data", [])
        for t in types_list:
            if (
                "logo" in str(t.get("slug", "")).lower()
                or "logo" in str(t.get("name", "")).lower()
            ):
                print(json.dumps(t, indent=2))
    else:
        print(f"Status {r.status_code}: {r.text[:500]}")

    # Popeye with refresh
    print("\n=== Testing Popeye with get_series_extended(refresh=True) ===")
    clear_series_cache()
    results = search_show("Popeye", token)
    if not results:
        print("No search results for Popeye")
        return
    popeye = next(
        (
            r
            for r in results
            if "1933" in str(r.get("firstAired", "") or r.get("year", ""))
        ),
        results[0],
    )
    sid = popeye.get("id") or popeye.get("tvdb_id")
    if str(sid).startswith("series-"):
        sid = int(sid.replace("series-", ""))
    print(f"Series: {popeye.get('name')} (ID: {sid})")
    record = get_series_extended(sid, token, refresh=True)
    if record:
        logo = record.get("artworks", {}).get("clearLogo")
        print(f"Logo URL: {logo or '(none)'}")
    else:
        print("No record returned")


if __name__ == "__main__":
    main()
