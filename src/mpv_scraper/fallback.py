"""Cross-API fallback system for robust metadata fetching.

This module provides fallback mechanisms when primary APIs fail or have poor data.
Supports TVDB, TMDB, OMDB, FanartTV, and AniDB as data sources.
"""

from __future__ import annotations

import os
import requests
from typing import Dict, Any, Optional
from pathlib import Path

from .tvdb import authenticate_tvdb, search_show, get_series_extended
from .tmdb import search_movie, get_movie_details


class FallbackScraper:
    """Cross-API fallback system for robust metadata fetching."""

    def __init__(self):
        self.tvdb_token = None
        self.api_keys = {
            "tmdb": os.getenv("TMDB_API_KEY"),
            "omdb": os.getenv("OMDB_API_KEY"),
            "fanarttv": os.getenv("FANARTTV_API_KEY"),
            "anidb": os.getenv("ANIDB_API_KEY"),
        }

    def _get_tvdb_token(self):
        """Get TVDB token, caching it for reuse."""
        if not self.tvdb_token:
            self.tvdb_token = authenticate_tvdb()
        return self.tvdb_token

    def _is_poor_data(self, record: Dict[str, Any], source: str) -> bool:
        """Determine if the data is poor quality and needs fallback."""
        if not record:
            return True

        if source == "tvdb":
            # Check if TVDB has poor data
            has_poster = bool(record.get("image"))
            has_logo = bool(record.get("artworks", {}).get("clearLogo"))
            has_episodes = len(record.get("episodes", [])) > 0
            has_overview = bool(record.get("overview"))

            # Consider poor if missing key assets
            return not (has_poster and has_logo and has_episodes and has_overview)

        elif source == "tmdb":
            # Check if TMDB has poor data
            has_poster = bool(record.get("poster_url"))
            has_logo = bool(record.get("logo_url"))
            has_overview = bool(record.get("overview"))

            return not (has_poster and has_overview)

        return False

    def _try_tmdb_for_tv_show(
        self, title: str, year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Try to find TV show data on TMDB."""
        try:
            # Search for TV show on TMDB
            search_results = requests.get(
                "https://api.themoviedb.org/3/search/tv",
                params={"api_key": self.api_keys["tmdb"], "query": title, "year": year, "language": "en-US"},
                timeout=10,
            ).json()

            if not search_results.get("results"):
                return None

            # Get the first result
            show_id = search_results["results"][0]["id"]

            # Get detailed TV show info
            details = requests.get(
                f"https://api.themoviedb.org/3/tv/{show_id}",
                params={"api_key": self.api_keys["tmdb"], "language": "en-US"},
                timeout=10,
            ).json()

            # Get images
            images = requests.get(
                f"https://api.themoviedb.org/3/tv/{show_id}/images",
                params={"api_key": self.api_keys["tmdb"], "include_image_language": "en,en-US,null"},
                timeout=10,
            ).json()

            # Transform to match our expected format
            poster_url = None
            logo_url = None

            if images.get("posters"):
                # More aggressive English filtering - prioritize US region and exclude known non-English
                us_posters = [p for p in images["posters"] if p.get("iso_3166_1") == "US"]
                english_posters = [p for p in images["posters"] if p.get("iso_639_1") == "en"]
                
                # Priority order: US posters first, then English posters, then all others
                if us_posters:
                    poster_candidates = us_posters
                elif english_posters:
                    poster_candidates = english_posters
                else:
                    # If no language info, try to filter by excluding known non-English patterns
                    poster_candidates = [
                        p for p in images["posters"] 
                        if not any(non_eng in p.get("file_path", "").lower() 
                                 for non_eng in ["ru", "de", "fr", "es", "it", "pt", "ja", "ko", "zh"])
                    ]
                    # If still no good candidates, use all posters
                    if not poster_candidates:
                        poster_candidates = images["posters"]
                
                poster_url = f"https://image.tmdb.org/t/p/original{poster_candidates[0]['file_path']}"

            if images.get("logos"):
                # More aggressive English filtering - prioritize US region and exclude known non-English
                us_logos = [l for l in images["logos"] if l.get("iso_3166_1") == "US"]
                english_logos = [l for l in images["logos"] if l.get("iso_639_1") == "en"]
                
                # Priority order: US logos first, then English logos, then all others
                if us_logos:
                    logo_candidates = us_logos
                elif english_logos:
                    logo_candidates = english_logos
                else:
                    # If no language info, try to filter by excluding known non-English patterns
                    logo_candidates = [
                        l for l in images["logos"] 
                        if not any(non_eng in l.get("file_path", "").lower() 
                                 for non_eng in ["ru", "de", "fr", "es", "it", "pt", "ja", "ko", "zh"])
                    ]
                    # If still no good candidates, use all logos
                    if not logo_candidates:
                        logo_candidates = images["logos"]
                
                logo_url = f"https://image.tmdb.org/t/p/original{logo_candidates[0]['file_path']}"

            return {
                "id": details.get("id"),
                "name": details.get("name"),
                "overview": details.get("overview"),
                "image": poster_url,
                "artworks": {"clearLogo": logo_url},
                "episodes": [],  # TMDB doesn't provide episode-level data easily
                "siteRating": details.get("vote_average", 0) / 10,  # Normalize to 0-1
                "genre": [g["name"] for g in details.get("genres", [])],
                "network": {
                    "name": (
                        details.get("networks", [{}])[0].get("name", "")
                        if details.get("networks")
                        else ""
                    )
                },
                "studio": [
                    {"name": company.get("name", "")}
                    for company in details.get("production_companies", [])
                    if company.get("name")
                ],
                "firstAired": details.get("first_air_date"),
                "source": "tmdb_fallback",
            }

        except Exception as e:
            print(f"TMDB fallback failed for {title}: {e}")
            return None

    def _try_fanarttv_for_tv_show(self, title: str) -> Optional[Dict[str, Any]]:
        """Try to find TV show data on FanartTV."""
        if not self.api_keys["fanarttv"]:
            return None

        try:
            # FanartTV requires TVDB ID, so this is limited
            # We'd need to first get TVDB ID to use FanartTV effectively
            return None
        except Exception:
            return None

    def scrape_tv_with_fallback(self, show_dir: Path) -> Optional[Dict[str, Any]]:
        """Scrape TV show with comprehensive fallback system."""
        show_name = show_dir.name

        # 1. Try TVDB first (primary for TV shows)
        print(f"Trying TVDB for {show_name}...")
        try:
            token = self._get_tvdb_token()
            results = search_show(show_name, token)

            if results:
                record = get_series_extended(results[0]["id"], token)
                if record and not self._is_poor_data(record, "tvdb"):
                    print(f"✓ TVDB has good data for {show_name}")
                    return record
                else:
                    print(f"⚠ TVDB has poor data for {show_name}, trying fallbacks...")
            else:
                print(f"❌ TVDB has no data for {show_name}, trying fallbacks...")
        except Exception as e:
            print(f"❌ TVDB failed for {show_name}: {e}")

        # 2. Try TMDB fallback
        print(f"Trying TMDB fallback for {show_name}...")
        tmdb_record = self._try_tmdb_for_tv_show(show_name)
        if tmdb_record and not self._is_poor_data(tmdb_record, "tmdb"):
            print(f"✓ TMDB fallback has good data for {show_name}")
            return tmdb_record

        # 3. Try FanartTV fallback (if we had TVDB ID)
        print(f"Trying FanartTV fallback for {show_name}...")
        fanart_record = self._try_fanarttv_for_tv_show(show_name)
        if fanart_record:
            print(f"✓ FanartTV fallback has data for {show_name}")
            return fanart_record

        # 4. Return best available data or None
        best_record = tmdb_record or fanart_record
        if best_record:
            print(f"⚠ Using best available data for {show_name} (may be incomplete)")
            return best_record

        print(f"❌ No good data found for {show_name} from any API")
        return None

    def scrape_movie_with_fallback(self, movie_path: Path) -> Optional[Dict[str, Any]]:
        """Scrape movie with comprehensive fallback system."""
        from .parser import parse_movie_filename

        movie_meta = parse_movie_filename(movie_path.name)
        if not movie_meta:
            return None

        # 1. Try TMDB first (primary for movies)
        print(f"Trying TMDB for {movie_meta.title}...")
        try:
            results = search_movie(movie_meta.title, movie_meta.year)

            if results:
                record = get_movie_details(results[0]["id"])
                if record and not self._is_poor_data(record, "tmdb"):
                    print(f"✓ TMDB has good data for {movie_meta.title}")
                    return record
                else:
                    print(
                        f"⚠ TMDB has poor data for {movie_meta.title}, trying fallbacks..."
                    )
            else:
                print(
                    f"❌ TMDB has no data for {movie_meta.title}, trying fallbacks..."
                )
        except Exception as e:
            print(f"❌ TMDB failed for {movie_meta.title}: {e}")

        # 2. Try OMDB fallback
        if self.api_keys["omdb"]:
            print(f"Trying OMDB fallback for {movie_meta.title}...")
            try:
                response = requests.get(
                    "http://www.omdbapi.com/",
                    params={
                        "apikey": self.api_keys["omdb"],
                        "t": movie_meta.title,
                        "y": movie_meta.year,
                    },
                    timeout=10,
                ).json()

                if response.get("Response") == "True":
                    # Transform OMDB data to our format
                    omdb_record = {
                        "id": None,
                        "title": response.get("Title"),
                        "overview": response.get("Plot"),
                        "vote_average": float(response.get("imdbRating", 0)) / 10,
                        "release_date": response.get("Year"),
                        "genre_names": [
                            g.strip() for g in response.get("Genre", "").split(",")
                        ],
                        "source": "omdb_fallback",
                    }

                    if not self._is_poor_data(omdb_record, "omdb"):
                        print(f"✓ OMDB fallback has good data for {movie_meta.title}")
                        return omdb_record

            except Exception as e:
                print(f"❌ OMDB fallback failed for {movie_meta.title}: {e}")

        print(f"❌ No good data found for {movie_meta.title} from any API")
        return None
