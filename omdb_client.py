# omdb_client.py - small wrapper around the OMDb API (https://www.omdbapi.com/)

import os

import requests

# Overridable so tests can point at a local fake server.
OMDB_URL = os.environ.get("OMDB_URL", "https://www.omdbapi.com/")

NETWORK_ERROR = "Could not reach OMDb. Check your connection and try again."


def clean(value):
    """OMDb uses the string "N/A" for missing data; return None instead."""
    return None if value in (None, "", "N/A") else value


def _get(params, api_key):
    """Call OMDb. Always returns a dict; failures have Response == "False" and an Error."""
    try:
        response = requests.get(OMDB_URL, params={**params, "apikey": api_key}, timeout=10)
        data = response.json()
    except (requests.RequestException, ValueError):
        return {"Response": "False", "Error": NETWORK_ERROR}
    return data if isinstance(data, dict) else {"Response": "False", "Error": NETWORK_ERROR}


def lookup_title(title, api_key, media_type=None):
    """Find one movie/series by title. media_type: None, "movie" or "series"."""
    params = {"t": title}
    if media_type in ("movie", "series"):
        params["type"] = media_type
    data = _get(params, api_key)
    return data if data.get("Response") == "True" else None


def get_details(imdb_id, api_key):
    """Full details (cast, runtime, full plot, totalSeasons...) for an IMDb id."""
    return _get({"i": imdb_id, "plot": "full"}, api_key)


def get_season(imdb_id, season, api_key):
    """Episode list of one season of a series."""
    return _get({"i": imdb_id, "Season": season}, api_key)
