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
    .card .score {
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

    @media (max-width: 640px) {
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


def fetch_from_omdb(title, api_key):
    """Look a movie up on OMDb. Returns the JSON dict or None."""
    try:
        response = requests.get(
            "https://www.omdbapi.com/",
            params={"t": title, "apikey": api_key},
            timeout=10,
        )
        data = response.json()
        return data if data.get('Response') == 'True' else None
    except (requests.RequestException, ValueError):
        return None


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
    """Build the word and n-gram indexes once; cleared whenever a movie is added."""
    movies = load_movies()
    return (
        build_inverted_index(movies=movies),
        build_ngram_index(movies=movies),
        get_movies_dict(movies=movies),
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
    """Hybrid index search first; edit-distance scan only if the indexes find nothing."""
    try:
        word_index, ngram_index, movies_dict = get_indexes()
        results = search_hybrid(query, word_index, ngram_index, movies_dict, max_results=max_results)
    except Exception:
        results = []
    return results or levenshtein_scan(query, movies, max_results)


# ============================================================
# UI HELPERS
# ============================================================

EXAMPLE_QUERIES = ["Titanik", "Batmn", "Incepton", "dark knigt", "crime"]
KIND_LABELS = {"exact": "Exact match", "title": "Title match", "genre": "Genre match", "typo": "Closest match"}


def set_query(value):
    st.session_state["query"] = value


def render_card(result):
    _, title, year, genre, rating, plot, poster = result['movie']
    kind = result['kind']

    chips = "".join(
        f'<span class="chip">{html.escape(g.strip())}</span>'
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
    <div class="card">
        <img class="poster" src="{poster_src(poster)}" alt="Poster of {html.escape(str(title))}">
        <div class="body">
            <div class="top">
                <div class="title">{html.escape(str(title))} <span>({html.escape(str(year))})</span></div>
                {score}
            </div>
            <div class="chips">{chips}</div>
            <p class="plot">{html.escape(plot_txt)}</p>
            <div class="foot"><span class="badge k-{kind}">{KIND_LABELS[kind]}</span>{meter}</div>
        </div>
    </div>
    """


def render_grid(movies):
    tiles = ""
    for movie in movies:
        title, year, rating, poster = movie[1], movie[2], movie[4], movie[6]
        rating_txt = f"★ {rating:.1f} · " if rating else ""
        tiles += (
            f'<div class="tile"><img src="{poster_src(poster)}" alt="">'
            f'<div class="cap">{html.escape(str(title))}<small>{rating_txt}{html.escape(str(year))}</small></div></div>'
        )
    return f'<div class="grid">{tiles}</div>'


# ============================================================
# MAIN APP
# ============================================================

def main():
    movies = get_all_movies()
    api_key = "69f58f62"

    # ---------- sidebar ----------
    with st.sidebar:
        st.header("Add a movie")
        new_movie = st.text_input("Movie title", key="new_movie", placeholder="e.g. Parasite")

        if st.button("Add movie", use_container_width=True):
            if not new_movie.strip():
                st.warning("Enter a movie title first.")
            else:
                with st.spinner("Looking it up on OMDb…"):
                    movie_data = fetch_from_omdb(new_movie, api_key)

                if movie_data:
                    add_movie_to_db(movie_data)
                    get_indexes.clear()  # make the new movie searchable
                    st.success(f"Added “{movie_data.get('Title')}”")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Movie not found.")

        st.divider()
        st.metric("Movies in collection", len(movies))
        st.caption("Typo-tolerant search powered by a word index and character n-grams.")

    # ---------- hero + search ----------
    st.markdown(
        '<div class="hero"><h1>🎬 Fuzzy Movie Search</h1>'
        '<p>Find any movie, even when you can’t spell it.</p></div>',
        unsafe_allow_html=True,
    )

    query = st.text_input(
        "Search",
        key="query",
        placeholder="Search for a movie or genre…",
        label_visibility="collapsed",
    )

    chip_cols = st.columns(len(EXAMPLE_QUERIES))
    for col, example in zip(chip_cols, EXAMPLE_QUERIES):
        col.button(example, key=f"ex_{example}", on_click=set_query, args=(example,), use_container_width=True)

    # ---------- results ----------
    if query.strip():
        start = time.perf_counter()
        results = search_movies(query, movies)
        elapsed_ms = (time.perf_counter() - start) * 1000

        if results:
            count = len(results)
            st.markdown(
                f'<div class="section-title">{count} result{"s" if count != 1 else ""} '
                f'for “{html.escape(query.strip())}”</div>'
                f'<div class="section-sub">Searched {len(movies)} movies in {elapsed_ms:.1f} ms</div>',
                unsafe_allow_html=True,
            )

            top = results[0]
            if top['kind'] == 'typo':
                suggestion = top['movie'][1]
                st.button(f"Did you mean “{suggestion}”?", key="suggest",
                          on_click=set_query, args=(suggestion,))

            st.markdown("".join(render_card(r) for r in results), unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="empty"><b>No matches for “{html.escape(query.strip())}”</b>'
                'Check the spelling, or try a shorter title or a genre like “drama”.</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div class="section-title">Top rated</div>'
            '<div class="section-sub">Start typing above, or pick a movie to search for.</div>',
            unsafe_allow_html=True,
        )
        if movies:
            top_rated = sorted(movies, key=lambda m: m[4] or 0, reverse=True)[:12]
            st.markdown(render_grid(top_rated), unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="empty"><b>Your collection is empty</b>'
                'Open the sidebar (top left) and add your first movie.</div>',
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
