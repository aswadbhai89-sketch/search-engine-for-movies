import base64
import html
import sqlite3
import time
from io import BytesIO
from urllib.parse import quote

import requests
import streamlit as st
from PIL import Image

from inverted_index import build_inverted_index, get_movies_dict, load_movies
from ngram_index import build_ngram_index, search_hybrid
from omdb_client import clean, get_details, get_season, lookup_title
from tfidf_search import build_tfidf_index, search_tfidf

OMDB_API_KEY = "69f58f62"

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Fuzzy Movie Search",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# STYLES
# ============================================================

st.markdown("""
<style>
    /* ---------- page ---------- */
    .stApp {
        background:
            radial-gradient(900px 500px at 85% -10%, rgba(255, 75, 92, 0.18), transparent 60%),
            radial-gradient(700px 500px at -10% 10%, rgba(120, 80, 255, 0.16), transparent 60%),
            #0b0b14;
    }
    header[data-testid="stHeader"] { background: transparent; }
    .block-container { padding-top: 2.2rem; max-width: 1000px; }
    #MainMenu, footer { visibility: hidden; }

    /* ---------- hero ---------- */
    .hero { text-align: center; padding: 1.2rem 0 1.2rem; }
    .hero h1 {
        font-size: 3.1rem; font-weight: 800; margin: 0; letter-spacing: -1px;
        background: linear-gradient(90deg, #ff4b5c, #ff9a5c 45%, #9b7bff);
        -webkit-background-clip: text; background-clip: text; color: transparent;
    }
    .hero p { color: #9a9ab0; font-size: 1.05rem; margin: 0.5rem 0 0; }

    /* ---------- search box ---------- */
    div[data-testid="stTextInput"] div[data-baseweb="input"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 999px; overflow: hidden;
        transition: border-color .2s, box-shadow .2s;
    }
    div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
        border-color: #ff4b5c; box-shadow: 0 0 0 3px rgba(255, 75, 92, 0.25);
    }
    div[data-testid="stTextInput"] div[data-baseweb="base-input"],
    div[data-testid="stTextInput"] input {
        background: transparent !important; border: none !important; box-shadow: none !important;
    }
    div[data-testid="stTextInput"] input { padding: 0.9rem 1.4rem; font-size: 1.1rem; }
    div[data-testid="stButton"] button {
        border-radius: 999px; border: 1px solid rgba(255, 255, 255, 0.14);
        background: rgba(255, 255, 255, 0.04); color: #d8d8e6; transition: all .2s;
    }
    div[data-testid="stButton"] button:hover {
        border-color: #ff4b5c; color: #fff; transform: translateY(-1px);
    }

    /* ---------- result cards ---------- */
    .card {
        display: flex; gap: 1.3rem; padding: 1.1rem; margin: 0 0 1rem;
        background: linear-gradient(145deg, rgba(255,255,255,0.07), rgba(255,255,255,0.02));
        border: 1px solid rgba(255, 255, 255, 0.09); border-radius: 18px;
        transition: transform .2s, border-color .2s, box-shadow .2s;
    }
    .card:hover {
        transform: translateY(-3px); border-color: rgba(255, 75, 92, 0.55);
        box-shadow: 0 12px 34px rgba(255, 75, 92, 0.15);
    }
    .card img.poster {
        width: 120px; height: 180px; object-fit: cover; border-radius: 12px; flex-shrink: 0;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    }
    .card .body { flex: 1; min-width: 0; display: flex; flex-direction: column; }
    .card .top { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }
    .card .title { font-size: 1.4rem; font-weight: 700; color: #ffffff; line-height: 1.25; }
    .card .title span { color: #8b8ba3; font-weight: 400; font-size: 1rem; }
    .score {
        flex-shrink: 0; font-weight: 700; color: #ffd166; font-size: 0.95rem;
        background: rgba(255, 209, 102, 0.12); border-radius: 999px; padding: 0.2rem 0.7rem;
    }
    .chips { margin: 0.55rem 0 0.45rem; display: flex; flex-wrap: wrap; gap: 0.4rem; }
    .chip {
        font-size: 0.74rem; padding: 0.16rem 0.65rem; border-radius: 999px;
        background: rgba(155, 123, 255, 0.16); color: #c7b8ff; border: 1px solid rgba(155, 123, 255, 0.3);
    }
    .plot {
        color: #b4b4c6; font-size: 0.92rem; line-height: 1.5; margin: 0 0 0.7rem;
        display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
    }
    .foot { margin-top: auto; display: flex; align-items: center; gap: 0.8rem; }
    .badge {
        font-size: 0.68rem; font-weight: 700; letter-spacing: .6px; text-transform: uppercase;
        padding: 0.2rem 0.6rem; border-radius: 6px; white-space: nowrap;
    }
    .badge.k-exact { background: rgba(46, 213, 115, .16); color: #2ed573; }
    .badge.k-title { background: rgba(86, 156, 255, .16); color: #6aa8ff; }
    .badge.k-genre { background: rgba(155, 123, 255, .16); color: #b8a3ff; }
    .badge.k-typo  { background: rgba(255, 140, 66, .16); color: #ff9a5c; }
    .bar { flex: 1; height: 6px; border-radius: 6px; background: rgba(255,255,255,0.08); overflow: hidden; }
    .bar > div { height: 100%; background: linear-gradient(90deg, #ff4b5c, #9b7bff); border-radius: 6px; }
    .pct { color: #8b8ba3; font-size: 0.8rem; min-width: 2.6rem; text-align: right; }

    /* ---------- poster grid (home) ---------- */
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 1rem; }
    .tile {
        position: relative; border-radius: 14px; overflow: hidden; aspect-ratio: 2 / 3;
        border: 1px solid rgba(255,255,255,0.09); transition: transform .2s, box-shadow .2s;
    }
    .tile:hover { transform: translateY(-5px) scale(1.02); box-shadow: 0 14px 30px rgba(0,0,0,.6); }
    .tile img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .tile .cap {
        position: absolute; inset: auto 0 0 0; padding: 2.4rem 0.7rem 0.65rem;
        background: linear-gradient(transparent, rgba(0,0,0,.92)); font-size: 0.85rem; font-weight: 600;
    }
    .tile .cap small { display: block; color: #ffd166; font-weight: 700; }

    /* ---------- misc ---------- */
    .section-title { font-size: 1.2rem; font-weight: 700; margin: 1.6rem 0 0.2rem; color: #fff; }
    .section-sub { color: #8b8ba3; font-size: 0.85rem; margin: 0 0 1rem; }
    .empty {
        text-align: center; color: #9a9ab0; padding: 2.5rem 1rem; margin-top: 1rem;
        border: 1px dashed rgba(255,255,255,0.14); border-radius: 18px;
    }
    .empty b { color: #fff; font-size: 1.1rem; display: block; margin-bottom: 0.3rem; }
    section[data-testid="stSidebar"] { background: #10101a; border-right: 1px solid rgba(255,255,255,.06); }

    /* ---------- detail view ---------- */
    .detail {
        display: flex; gap: 1.8rem; padding: 1.5rem; margin: 0.5rem 0 1.2rem;
        background: linear-gradient(145deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
        border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 22px;
    }
    .detail img.poster {
        width: 220px; height: 330px; object-fit: cover; border-radius: 16px; flex-shrink: 0;
        box-shadow: 0 14px 40px rgba(0, 0, 0, 0.6);
    }
    .detail .body { flex: 1; min-width: 0; }
    .detail h2 { margin: 0; font-size: 2rem; font-weight: 800; color: #fff; line-height: 1.2; padding: 0; }
    .detail .meta { color: #9a9ab0; font-size: 0.92rem; margin: 0.35rem 0 0.7rem; }
    .detail .rating-row { display: flex; align-items: center; gap: 0.7rem; margin: 0.6rem 0 0.9rem; flex-wrap: wrap; }
    .detail .votes { color: #8b8ba3; font-size: 0.85rem; }
    .detail .full-plot { color: #cfcfdd; line-height: 1.65; font-size: 1rem; margin: 0.4rem 0 1.1rem; }
    .facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 0.9rem 1.5rem; }
    .fact .label { color: #8b8ba3; font-size: 0.72rem; text-transform: uppercase; letter-spacing: .7px; }
    .fact .value { color: #ececf3; font-size: 0.94rem; margin-top: 0.1rem; }
    .badge.k-series { background: rgba(255, 75, 92, .16); color: #ff7a85; }
    .badge.k-movie { background: rgba(86, 156, 255, .16); color: #6aa8ff; }
    .badge.k-plot { background: rgba(46, 213, 115, .14); color: #3fe08a; }
    .notice {
        padding: 0.8rem 1rem; border-radius: 12px; margin: 0.5rem 0 1rem; font-size: 0.9rem;
        background: rgba(255, 193, 7, 0.1); border: 1px solid rgba(255, 193, 7, 0.3); color: #ffd666;
    }
    .episodes { margin: 0.4rem 0 1rem; }
    .ep {
        display: grid; grid-template-columns: 3.2rem 1fr auto 4.2rem; gap: 0.8rem; align-items: center;
        padding: 0.65rem 0.9rem; border-radius: 12px; border: 1px solid transparent; transition: background .15s;
    }
    .ep:nth-child(odd) { background: rgba(255,255,255,0.035); }
    .ep:hover { background: rgba(255, 75, 92, 0.1); border-color: rgba(255, 75, 92, 0.3); }
    .ep .n { color: #ff7a85; font-weight: 700; }
    .ep .t { color: #fff; font-weight: 500; }
    .ep .d { color: #8b8ba3; font-size: 0.82rem; }
    .ep .r { color: #ffd166; font-weight: 700; text-align: right; }
    .ep-detail {
        padding: 1.1rem 1.3rem; border-radius: 16px; margin-top: 0.8rem;
        background: rgba(155, 123, 255, 0.08); border: 1px solid rgba(155, 123, 255, 0.25);
    }
    .ep-detail .t { color: #fff; font-size: 1.15rem; font-weight: 700; }

    @media (max-width: 640px) {
        .detail { flex-direction: column; align-items: center; text-align: left; padding: 1.1rem; }
        .detail img.poster { width: 180px; height: 270px; }
        .detail .body { width: 100%; }
        .ep { grid-template-columns: 2.6rem 1fr 3.4rem; }
        .ep .d { display: none; }
        .tile { width: 150px; }
        div[data-testid="stHorizontalBlock"] { flex-direction: row !important; flex-wrap: wrap; gap: 0.5rem !important; }
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            min-width: 0 !important; width: auto !important; flex: 0 0 auto !important;
        }
        .hero h1 { font-size: 2.2rem; }
        .card { gap: 0.9rem; padding: 0.8rem; }
        .card img.poster { width: 84px; height: 126px; }
        .card .title { font-size: 1.15rem; }
        .plot { -webkit-line-clamp: 4; font-size: 0.85rem; }
        .foot { flex-wrap: wrap; gap: 0.5rem; }
        .grid { grid-template-columns: repeat(2, 1fr); }
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# DATABASE
# ============================================================

def init_db():
    """Create the movies table if it does not exist yet."""
    conn = sqlite3.connect('movies.db')
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS movies (
                id TEXT PRIMARY KEY,
                title TEXT,
                year TEXT,
                genre TEXT,
                rating REAL,
                plot TEXT,
                poster TEXT
            )
        ''')
        conn.commit()
    finally:
        conn.close()


def get_all_movies():
    """Return every movie as (id, title, year, genre, rating, plot, poster)."""
    try:
        init_db()
        return load_movies()
    except sqlite3.Error:
        return []


def add_movie_to_db(movie_data):
    """Insert (or update) a movie fetched from OMDb."""
    init_db()

    try:
        rating = float(movie_data.get('imdbRating', 0))
    except (TypeError, ValueError):
        rating = 0.0

    conn = sqlite3.connect('movies.db')
    try:
        conn.execute('''
            INSERT OR REPLACE INTO movies (id, title, year, genre, rating, plot, poster)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            movie_data.get('imdbID'),
            movie_data.get('Title'),
            movie_data.get('Year'),
            movie_data.get('Genre'),
            rating,
            movie_data.get('Plot'),
            movie_data.get('Poster')
        ))
        conn.commit()
    finally:
        conn.close()


# ============================================================
# POSTERS
# ============================================================

PLACEHOLDER_SVG = "data:image/svg+xml;utf8," + quote(
    '<svg xmlns="http://www.w3.org/2000/svg" width="260" height="380">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#23233a"/><stop offset="1" stop-color="#14141f"/></linearGradient></defs>'
    '<rect width="260" height="380" fill="url(#g)"/>'
    '<text x="130" y="185" font-size="64" text-anchor="middle">🎬</text>'
    '<text x="130" y="235" font-size="18" fill="#8b8ba3" text-anchor="middle" '
    'font-family="sans-serif">No poster</text></svg>'
)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_poster(url):
    """Download a poster once and cache it. Returns bytes or None."""
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        Image.open(BytesIO(response.content)).verify()  # make sure it is a real image
        return response.content
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def poster_src(url):
    """Return the poster as a data URI (or a placeholder) for embedding in HTML."""
    data = fetch_poster(url) if url and url != 'N/A' else None
    if data:
        fmt = (Image.open(BytesIO(data)).format or "JPEG").lower()
        return f"data:image/{fmt};base64,{base64.b64encode(data).decode()}"
    return PLACEHOLDER_SVG


# ============================================================
# SEARCH
# ============================================================

def levenshtein_distance(s1, s2):
    """Number of single-character edits needed to turn s1 into s2."""
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])

    return dp[m][n]


@st.cache_resource(show_spinner=False)
def get_indexes():
    """Build the word, n-gram and TF-IDF indexes once; cleared whenever a movie is added."""
    movies = load_movies()
    movies_dict = get_movies_dict(movies=movies)
    return (
        build_inverted_index(movies=movies),
        build_ngram_index(movies=movies),
        movies_dict,
        build_tfidf_index(movies=movies),
    )


def levenshtein_scan(query, movies, max_results=10, min_similarity=40):
    """Last-resort scan over every title using edit distance."""
    q = query.lower().strip()
    results = []
    for movie in movies:
        title = movie[1].lower()
        max_len = max(len(q), len(title))
        similarity = (1 - levenshtein_distance(q, title) / max_len) * 100 if max_len else 0
        if similarity >= min_similarity:
            results.append({'movie': movie, 'similarity': similarity, 'kind': 'typo'})
    results.sort(key=lambda r: -r['similarity'])
    return results[:max_results]


def search_movies(query, movies, max_results=10):
    """
    Ranking, best first:
      1. exact and title matches        (the user typed a title)
      2. genre and plot matches         (ordered by TF-IDF relevance)
      3. typo matches                   (closest titles by n-gram similarity)
    The edit-distance scan runs only when every index comes back empty.
    """
    try:
        word_index, ngram_index, movies_dict, tfidf_index = get_indexes()
        hybrid = search_hybrid(query, word_index, ngram_index, movies_dict, max_results=max_results)
        tfidf = search_tfidf(query, tfidf_index, movies_dict, max_results=max_results)
    except Exception:
        hybrid, tfidf = [], []

    tfidf_scores = {movie[0]: score for movie, score in tfidf}
    top = [r for r in hybrid if r['kind'] in ('exact', 'title')]
    typos = [r for r in hybrid if r['kind'] == 'typo']
    middle = {r['movie'][0]: r for r in hybrid if r['kind'] == 'genre'}
    for movie, score in tfidf:
        middle.setdefault(movie[0], {'movie': movie, 'similarity': score * 100, 'kind': 'plot'})
    middle = sorted(middle.values(), key=lambda r: -tfidf_scores.get(r['movie'][0], 0))

    seen, results = set(), []
    for r in top + middle + typos:
        if r['movie'][0] not in seen:
            seen.add(r['movie'][0])
            results.append(r)
    return results[:max_results] or levenshtein_scan(query, movies, max_results)


# ============================================================
# MOVIE DETAILS (OMDb)
# ============================================================

@st.cache_data(ttl=86400, show_spinner=False)
def cached_details(imdb_id):
    """Details for one title. Raises on failure so errors are never cached."""
    data = get_details(imdb_id, OMDB_API_KEY)
    if data.get("Response") != "True":
        raise RuntimeError(data.get("Error", "Unknown error"))
    return data


@st.cache_data(ttl=86400, show_spinner=False)
def cached_season(imdb_id, season):
    """Episode list of one season. Raises on failure so errors are never cached."""
    data = get_season(imdb_id, season, OMDB_API_KEY)
    if data.get("Response") != "True":
        raise RuntimeError(data.get("Error", "Unknown error"))
    return data


# ============================================================
# UI HELPERS
# ============================================================


EXAMPLE_QUERIES = ["Titanik", "Batmn", "Incepton", "batman gotham", "dream heist", "crime"]
KIND_LABELS = {
    "exact": "Exact match",
    "title": "Title match",
    "genre": "Genre match",
    "plot": "Plot match",
    "typo": "Closest match",
}


def set_query(value):
    st.session_state["query"] = value


def open_movie(movie_id):
    st.session_state["selected"] = movie_id


def close_movie():
    st.session_state["selected"] = None


def esc(value):
    return html.escape(str(value)) if value is not None else ""


def render_card(result):
    _, title, year, genre, rating, plot, poster = result['movie']
    kind = result['kind']

    chips = "".join(
        f'<span class="chip">{esc(g.strip())}</span>'
        for g in (genre or "").split(",") if g.strip() and g.strip() != 'N/A'
    )
    score = f'<div class="score">★ {rating:.1f}</div>' if rating else ""
    plot_txt = plot if plot and plot != 'N/A' else "No plot summary available."

    # A percentage only makes sense when the title itself was compared
    meter = ""
    if kind in ("typo", "title"):
        pct = max(0, min(100, result['similarity']))
        meter = f'<div class="bar"><div style="width:{pct:.0f}%"></div></div><span class="pct">{pct:.0f}%</span>'

    return f"""
    <div class="card" style="margin-bottom:-0.25rem">
        <img class="poster" src="{poster_src(poster)}" alt="Poster of {esc(title)}">
        <div class="body">
            <div class="top">
                <div class="title">{esc(title)} <span>({esc(year)})</span></div>
                {score}
            </div>
            <div class="chips">{chips}</div>
            <p class="plot">{esc(plot_txt)}</p>
            <div class="foot"><span class="badge k-{kind}">{KIND_LABELS[kind]}</span>{meter}</div>
        </div>
    </div>
    """


def render_tile(movie):
    title, year, rating, poster = movie[1], movie[2], movie[4], movie[6]
    rating_txt = f"★ {rating:.1f} · " if rating else ""
    return (
        f'<div class="tile"><img src="{poster_src(poster)}" alt="">'
        f'<div class="cap">{esc(title)}<small>{rating_txt}{esc(year)}</small></div></div>'
    )


def fact(label, value):
    if not value:
        return ""
    return f'<div class="fact"><div class="label">{label}</div><div class="value">{esc(value)}</div></div>'


def render_detail(row, details):
    """Big detail card. `details` is the OMDb dict, or None to show saved data only."""
    _, title, year, genre, rating, plot, poster = row
    d = details or {}

    title = clean(d.get('Title')) or title
    media_type = (clean(d.get('Type')) or '').lower()
    seasons = clean(d.get('totalSeasons'))
    plot_txt = clean(d.get('Plot')) or (plot if plot and plot != 'N/A' else "No plot summary available.")
    genre_txt = clean(d.get('Genre')) or genre
    imdb_rating = clean(d.get('imdbRating')) or (f"{rating:.1f}" if rating else None)
    votes = clean(d.get('imdbVotes'))

    badge = f'<span class="badge k-{media_type}">{esc(media_type.title())}</span> ' if media_type in ('movie', 'series') else ""
    meta_parts = [clean(d.get('Year')) or year, clean(d.get('Rated')), clean(d.get('Runtime'))]
    if seasons:
        meta_parts.append(f"{seasons} season{'s' if seasons != '1' else ''}")
    meta = " · ".join(esc(p) for p in meta_parts if p)

    chips = "".join(
        f'<span class="chip">{esc(g.strip())}</span>'
        for g in (genre_txt or "").split(",") if g.strip() and g.strip() != 'N/A'
    )
    rating_row = ""
    if imdb_rating:
        votes_html = f'<span class="votes">{esc(votes)} votes</span>' if votes else ""
        rating_row = f'<div class="rating-row"><div class="score">★ {esc(imdb_rating)}</div>{votes_html}</div>'

    facts = "".join([
        fact("Director", clean(d.get('Director'))),
        fact("Writer", clean(d.get('Writer'))),
        fact("Cast", clean(d.get('Actors'))),
        fact("Released", clean(d.get('Released'))),
        fact("Language", clean(d.get('Language'))),
        fact("Country", clean(d.get('Country'))),
        fact("Awards", clean(d.get('Awards'))),
    ])

    return f"""
    <div class="detail">
        <img class="poster" src="{poster_src(poster)}" alt="Poster of {esc(title)}">
        <div class="body">
            <h2>{esc(title)}</h2>
            <div class="meta">{badge}{meta}</div>
            <div class="chips">{chips}</div>
            {rating_row}
            <div class="full-plot">{esc(plot_txt)}</div>
            <div class="facts">{facts}</div>
        </div>
    </div>
    """


def render_episodes(episodes):
    rows = ""
    for ep in episodes:
        rating = clean(ep.get('imdbRating'))
        rows += (
            '<div class="ep">'
            f'<span class="n">E{esc(ep.get("Episode"))}</span>'
            f'<span class="t">{esc(ep.get("Title"))}</span>'
            f'<span class="d">{esc(clean(ep.get("Released")) or "")}</span>'
            f'<span class="r">{"★ " + esc(rating) if rating else ""}</span>'
            '</div>'
        )
    return f'<div class="episodes">{rows}</div>'


def render_episode_detail(ep):
    rating = clean(ep.get('imdbRating'))
    meta = " · ".join(esc(p) for p in [
        f"S{ep['Season']} E{ep['Episode']}" if clean(ep.get('Season')) and clean(ep.get('Episode')) else None,
        clean(ep.get('Released')),
        clean(ep.get('Runtime')),
        f"★ {rating}" if rating else None,
    ] if p)
    facts = "".join([
        fact("Director", clean(ep.get('Director'))),
        fact("Writer", clean(ep.get('Writer'))),
        fact("Cast", clean(ep.get('Actors'))),
    ])
    return f"""
    <div class="ep-detail">
        <div class="t">{esc(ep.get('Title'))}</div>
        <div class="meta">{meta}</div>
        <div class="full-plot">{esc(clean(ep.get('Plot')) or 'No plot summary available.')}</div>
        <div class="facts">{facts}</div>
    </div>
    """


def notice(message):
    st.markdown(f'<div class="notice">{esc(message)}</div>', unsafe_allow_html=True)


def show_series(movie_id, details):
    """Season picker, episode list and per-episode details."""
    total = clean(details.get('totalSeasons'))
    if not total or not total.isdigit():
        notice("Season information is not available for this series.")
        return

    st.markdown('<div class="section-title">Seasons and episodes</div>', unsafe_allow_html=True)
    season = st.selectbox(
        "Season", range(1, int(total) + 1),
        format_func=lambda n: f"Season {n}", key=f"season_{movie_id}",
    )

    try:
        episodes = cached_season(movie_id, season).get('Episodes') or []
    except Exception as e:
        notice(f"Could not load this season ({e}).")
        return
    if not episodes:
        notice("No episodes are listed for this season yet.")
        return

    st.markdown(
        f'<div class="section-sub">{len(episodes)} episode{"s" if len(episodes) != 1 else ""}</div>'
        + render_episodes(episodes),
        unsafe_allow_html=True,
    )

    labels = {ep['imdbID']: f"E{ep.get('Episode')} · {ep.get('Title')}" for ep in episodes if ep.get('imdbID')}
    choice = st.selectbox(
        "Episode details", list(labels), format_func=labels.get, index=None,
        placeholder="Pick an episode to see its plot and credits",
        key=f"episode_{movie_id}_{season}",
    )
    if choice:
        try:
            st.markdown(render_episode_detail(cached_details(choice)), unsafe_allow_html=True)
        except Exception as e:
            notice(f"Could not load this episode ({e}).")


def show_detail(row, has_query):
    st.button("← Back to results" if has_query else "← Back to top rated", key="back", on_click=close_movie)

    try:
        details, error = cached_details(row[0]), None
    except Exception as e:
        details, error = None, str(e)

    st.markdown(render_detail(row, details), unsafe_allow_html=True)

    if error:
        notice(f"Showing saved info only. Extended details are unavailable right now ({error}).")
    elif (details.get('Type') or '').lower() == 'series':
        show_series(row[0], details)


# ============================================================
# MAIN APP
# ============================================================

def main():
    movies = get_all_movies()
    by_id = {m[0]: m for m in movies}

    # ---------- sidebar ----------
    with st.sidebar:
        st.header("Add a movie or series")
        new_title = st.text_input("Title", key="new_movie", placeholder="e.g. Parasite or Breaking Bad")
        new_type = st.radio("Type", ["Any", "Movie", "Series"], horizontal=True)

        if st.button("Add to collection", use_container_width=True):
            if not new_title.strip():
                st.warning("Enter a title first.")
            else:
                with st.spinner("Looking it up on OMDb…"):
                    movie_data = lookup_title(new_title, OMDB_API_KEY, new_type.lower())

                if movie_data:
                    add_movie_to_db(movie_data)
                    get_indexes.clear()  # make the new title searchable
                    st.success(f"Added “{movie_data.get('Title')}”")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Not found. Check the spelling or the type.")

        st.divider()
        st.metric("Titles in collection", len(movies))
        st.caption("Search combines a word index, character n-grams and TF-IDF plot relevance.")

    # ---------- hero + search ----------
    st.markdown(
        '<div class="hero"><h1>🎬 Fuzzy Movie Search</h1>'
        '<p>Find any movie or series, even when you can’t spell it.</p></div>',
        unsafe_allow_html=True,
    )

    query = st.text_input(
        "Search",
        key="query",
        placeholder="Search by title, genre or story…",
        label_visibility="collapsed",
    )

    chip_cols = st.columns(len(EXAMPLE_QUERIES))
    for col, example in zip(chip_cols, EXAMPLE_QUERIES):
        col.button(example, key=f"ex_{example}", on_click=set_query, args=(example,), use_container_width=True)

    # Typing a new query closes any open detail page
    if st.session_state.get("_last_query") != query:
        st.session_state["selected"] = None
        st.session_state["_last_query"] = query

    # ---------- detail page ----------
    selected = by_id.get(st.session_state.get("selected"))
    if selected:
        show_detail(selected, bool(query.strip()))
        return

    # ---------- results ----------
    if query.strip():
        start = time.perf_counter()
        results = search_movies(query, movies)
        elapsed_ms = (time.perf_counter() - start) * 1000

        if results:
            count = len(results)
            st.markdown(
                f'<div class="section-title">{count} result{"s" if count != 1 else ""} '
                f'for “{esc(query.strip())}”</div>'
                f'<div class="section-sub">Searched {len(movies)} titles in {elapsed_ms:.1f} ms · '
                'select a title to see cast, plot and episodes</div>',
                unsafe_allow_html=True,
            )

            top = results[0]
            if top['kind'] == 'typo':
                suggestion = top['movie'][1]
                st.button(f"Did you mean “{suggestion}”?", key="suggest",
                          on_click=set_query, args=(suggestion,))

            for r in results:
                st.markdown(render_card(r), unsafe_allow_html=True)
                st.button("View details →", key=f"open_{r['movie'][0]}",
                          on_click=open_movie, args=(r['movie'][0],))
        else:
            st.markdown(
                f'<div class="empty"><b>No matches for “{esc(query.strip())}”</b>'
                'Check the spelling, or try a shorter title, a genre like “drama”, '
                'or a few words from the story.</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div class="section-title">Top rated</div>'
            '<div class="section-sub">Select a title to see cast, plot and episodes.</div>',
            unsafe_allow_html=True,
        )
        if movies:
            top_rated = sorted(movies, key=lambda m: m[4] or 0, reverse=True)[:12]
            per_row = 6
            for start in range(0, len(top_rated), per_row):
                cols = st.columns(per_row)
                for col, movie in zip(cols, top_rated[start:start + per_row]):
                    with col:
                        st.markdown(render_tile(movie), unsafe_allow_html=True)
                        st.button("Details", key=f"tile_{movie[0]}", on_click=open_movie,
                                  args=(movie[0],), use_container_width=True)
        else:
            st.markdown(
                '<div class="empty"><b>Your collection is empty</b>'
                'Open the sidebar (top left) and add your first title.</div>',
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
