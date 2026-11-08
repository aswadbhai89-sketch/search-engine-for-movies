# 🎬 Fuzzy Movie Search

A movie search app that tolerates typos ("Titanik" → "Titanic") using Levenshtein distance. Movie data comes from the [OMDb API](https://www.omdbapi.com/) and is stored in SQLite.

## Setup

```bash
git clone <repo-url>
cd fuzzy-movie-search
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Get a free key at https://www.omdbapi.com/apikey.aspx, then set it:

```bash
export OMDB_API_KEY=your_key      # Windows PowerShell: $env:OMDB_API_KEY="your_key"
```

## Run

```bash
streamlit run app.py        # web app
python fuzzy_search.py      # command-line version
```

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit web app (search + add movies) |
| `fuzzy_search.py` | CLI version of the search |
| `setup_db.py` | Creates the empty `movies.db` table |
| `fetch_movies.py` | Bulk-fetches a starter list of movies from OMDb |
| `movies.db` | SQLite database (sample data included) |

## Team workflow

- Never commit API keys (use `OMDB_API_KEY`).
- Work on a branch, open a pull request, have your teammate review it:
  `git checkout -b feature/my-change`
- `git pull` before you start working.
- `movies.db` is binary and can't be merged — agree on who changes it, or regenerate it with `fetch_movies.py`.
