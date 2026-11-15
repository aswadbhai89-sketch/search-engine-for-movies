# 🎬 Fuzzy Movie Search

A movie search app that tolerates typos ("Titanik" → "Titanic") using Levenshtein distance. Movie data comes from the [OMDb API](https://www.omdbapi.com/) and is stored in SQLite.

## Setup

```bash
git clone <repo-url>
cd search-engine-for-movies
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The OMDb API key is set in `app.py` and `fetch_movies.py`. To use your own, get a free key at https://www.omdbapi.com/apikey.aspx and replace it.

## Run

```bash
streamlit run app.py        # web app
python fuzzy_search.py      # command-line version
```

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit web app (search, add movies) |
| `inverted_index.py` | Word -> movie index (exact words in titles and genres) |
| `ngram_index.py` | Character n-gram index and hybrid search (typo tolerance) |
| `bm25_search.py` | BM25 ranking over titles, genres and plots (used by the app) |
| `tfidf_search.py` | TF-IDF ranking, kept for comparison and shared text processing |
| `omdb_client.py` | OMDb API wrapper (lookup, full details, season episodes) |
| `fuzzy_search.py` | Command-line search using edit distance |
| `test_index.py`, `test_ngram.py`, `test_tfidf.py`, `test_bm25.py` | Search checks and timing comparisons |
| `setup_db.py` | Creates the empty `movies.db` table |
| `fetch_movies.py` | Bulk-fetches a starter list of movies from OMDb |
| `movies.db` | SQLite database (sample data included) |

## How search works

1. **Word index** - exact words from titles and genres ("dark", "crime").
2. **N-gram index** - 3-letter chunks of each title, so "titanik" still shares "tit", "ita", "tan" and "ani" with "Titanic".
3. **BM25** - ranks movies by how well a few story words match the plot ("dream heist" finds Inception). Rare words count more, repeated words stop helping after a while, and long descriptions are not favoured over short ones. This is the ranking used by most search engines; `k1` and `b` in `bm25_search.py` tune it, and `python test_bm25.py` shows how a score is built up step by step.
4. **Edit-distance scan** - only used when all the indexes find nothing.

Results are ordered: exact/title matches, then genre and plot matches, then typo matches.

## Movie and series details

Select any title to open its page: full plot, cast, director, runtime, awards and IMDb rating, loaded live from OMDb. For TV series there is also a season picker, the episode list with air dates and ratings, and a plot and credits panel for any episode.

If OMDb is unreachable (or the daily request limit is hit) the page falls back to the data stored in `movies.db`.

Run `python test_ngram.py`, `python test_tfidf.py` and `python test_bm25.py` to check search quality and compare timings.

## Team workflow

- Work on a branch, open a pull request, have your teammate review it:
  `git checkout -b feature/my-change`
- `git pull` before you start working.
- `movies.db` is binary and can't be merged — agree on who changes it, or regenerate it with `fetch_movies.py`.

## Deploying (e.g. Streamlit Community Cloud)

`movies.db` ships with the repo, so the app starts with the sample movies. Movies added through the app are written to the server's local disk and can be lost when the app restarts or redeploys. For permanent data, commit the updated `movies.db` or move to a hosted database.
