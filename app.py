
import streamlit as st
import sqlite3
import requests
import base64
import html
import time
from urllib.parse import quote
from PIL import Image
from io import BytesIO

from inverted_index import build_inverted_index, get_movies_dict, search_with_index

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Fuzzy Movie Search",
    page_icon="🎬",
    layout="wide"
)

# ============================================================
# CUSTOM CSS (Styling)
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
    .block-container { padding-top: 2rem; max-width: 1100px; }
    #MainMenu, footer { visibility: hidden; }

    /* ---------- hero ---------- */
    .hero { text-align: center; padding: 1.5rem 0 0.5rem; }
    .hero h1 {
        font-size: 3.2rem; font-weight: 800; margin: 0; letter-spacing: -1px;
        background: linear-gradient(90deg, #ff4b5c, #ff9a5c 45%, #9b7bff);
        -webkit-background-clip: text; background-clip: text; color: transparent;
    }
    .hero p { color: #9a9ab0; font-size: 1.05rem; margin: 0.4rem 0 0; }

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
        display: flex; gap: 1.4rem; padding: 1.1rem; margin: 0 0 1rem;
        background: linear-gradient(145deg, rgba(255,255,255,0.07), rgba(255,255,255,0.02));
        border: 1px solid rgba(255, 255, 255, 0.09); border-radius: 18px;
        backdrop-filter: blur(6px); transition: transform .2s, border-color .2s, box-shadow .2s;
    }
    .card:hover {
        transform: translateY(-3px); border-color: rgba(255, 75, 92, 0.55);
        box-shadow: 0 12px 34px rgba(255, 75, 92, 0.15);
    }
    .card img.poster {
        width: 130px; height: 190px; object-fit: cover; border-radius: 12px; flex-shrink: 0;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    }
    .card .body { flex: 1; min-width: 0; }
    .card .title { margin: 0; font-size: 1.45rem; font-weight: 700; color: #ffffff; line-height: 1.25; }
    .card .title span { color: #8b8ba3; font-weight: 400; font-size: 1.05rem; }
    .chips { margin: 0.55rem 0; display: flex; flex-wrap: wrap; gap: 0.4rem; }
    .chip {
        font-size: 0.75rem; padding: 0.18rem 0.65rem; border-radius: 999px;
        background: rgba(155, 123, 255, 0.16); color: #c7b8ff; border: 1px solid rgba(155, 123, 255, 0.3);
    }
    .rating { color: #ffd166; font-weight: 700; font-size: 1.05rem; }
    .badge {
        display: inline-block; font-size: 0.7rem; font-weight: 700; letter-spacing: .6px;
        padding: 0.18rem 0.6rem; border-radius: 6px; margin-right: 0.4rem; text-transform: uppercase;
    }
    .badge.exact { background: rgba(46, 213, 115, .16); color: #2ed573; }
    .badge.partial { background: rgba(255, 193, 7, .16); color: #ffc107; }
    .badge.fuzzy { background: rgba(255, 140, 66, .16); color: #ff8c42; }
    .badge.low { background: rgba(160, 160, 180, .14); color: #a0a0b4; }
    .badge.method { background: rgba(86, 156, 255, .16); color: #6aa8ff; }
    .bar { height: 6px; border-radius: 6px; background: rgba(255,255,255,0.08); margin: 0.7rem 0 0.2rem; overflow: hidden; }
    .bar > div { height: 100%; background: linear-gradient(90deg, #ff4b5c, #9b7bff); border-radius: 6px; }
    .meta { color: #8b8ba3; font-size: 0.78rem; }
    details { margin-top: 0.5rem; color: #c4c4d4; font-size: 0.92rem; }
    details summary { cursor: pointer; color: #ff7a85; font-weight: 600; }

    /* ---------- poster grid (home) ---------- */
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 1rem; }
    .tile {
        position: relative; border-radius: 14px; overflow: hidden; aspect-ratio: 2 / 3;
        border: 1px solid rgba(255,255,255,0.09); transition: transform .2s, box-shadow .2s;
    }
    .tile:hover { transform: translateY(-5px) scale(1.02); box-shadow: 0 14px 30px rgba(0,0,0,.6); }
    .tile img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .tile .cap {
        position: absolute; inset: auto 0 0 0; padding: 2.2rem 0.7rem 0.6rem;
        background: linear-gradient(transparent, rgba(0,0,0,.92)); font-size: 0.85rem; font-weight: 600;
    }
    .tile .cap small { display: block; color: #ffd166; font-weight: 700; }
    .section-title { font-size: 1.25rem; font-weight: 700; margin: 1.8rem 0 0.8rem; color: #fff; }
    .empty { text-align: center; color: #8b8ba3; padding: 2rem; }

    /* ---------- sidebar ---------- */
    section[data-testid="stSidebar"] { background: #10101a; border-right: 1px solid rgba(255,255,255,.06); }
</style>
""", unsafe_allow_html=True)


# ============================================================
# LEVENSHTEIN DISTANCE
# ============================================================

def levenshtein_distance(s1, s2):
    """Do strings ke beech kitne characters different hain"""
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


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def init_db():
    """Table na ho to bana do (movies.db missing ho tab bhi app crash na ho)"""
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
    """Database ki saari movies nikaalo"""
    try:
        init_db()
        conn = sqlite3.connect('movies.db')
        try:
            return conn.execute('SELECT * FROM movies').fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return []


def add_movie_to_db(movie_data):
    """Nayi movie database mein add karo"""
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
    """OMDB se movie fetch karo"""
    url = "https://www.omdbapi.com/"
    
    try:
        response = requests.get(url, params={"t": title, "apikey": api_key}, timeout=10)
        data = response.json()
        
        if data.get('Response') == 'True':
            return data
        return None
    except (requests.RequestException, ValueError):
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_poster(url):
    """Poster download karo (cached - har rerun par dobara download nahi hoga)"""
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        Image.open(BytesIO(response.content)).verify()  # valid image hai ya nahi
        return response.content
    except Exception:
        return None


# ============================================================
# SEARCH FUNCTION
# ============================================================

def fuzzy_scan(query, movies, max_results=10):
    """Saari movies par Levenshtein scan (typos + substring, jaise 'bat' -> 'Batman')"""
    query = query.lower().strip()
    results = []
    
    for movie in movies:
        # movie tuple: (id, title, year, genre, rating, plot, poster)
        title = movie[1].lower()
        distance = levenshtein_distance(query, title)
        is_substring = query in title
        
        # Similarity score calculate karo (0-100%)
        max_len = max(len(query), len(title))
        similarity = ((max_len - distance) / max_len) * 100 if max_len > 0 else 0
        
        results.append({
            'movie': movie,
            'distance': distance,
            'similarity': similarity,
            'substring': is_substring,
            'method': 'fuzzy'
        })
    
    # Pehle substring matches, phir kam distance wale
    results.sort(key=lambda x: (not x['substring'], x['distance']))
    
    return results[:max_results]


@st.cache_data(show_spinner=False)
def get_search_index():
    """Index ek baar banao aur cache karo (movie add hone par clear hota hai)"""
    return build_inverted_index(), get_movies_dict()


def fuzzy_search(query, movies, max_results=10):
    """Pehle inverted index (fast), kuch na mile to fuzzy scan (typos ke liye)"""
    try:
        index, movies_dict = get_search_index()
        index_movies = search_with_index(query, index, movies_dict, max_results)
    except Exception:
        index_movies = None
    
    if index_movies is None:
        return fuzzy_scan(query, movies, max_results)
    
    q = query.lower().strip()
    results = []
    for movie in index_movies:
        title = movie[1].lower()
        distance = levenshtein_distance(q, title)
        max_len = max(len(q), len(title))
        similarity = ((max_len - distance) / max_len) * 100 if max_len > 0 else 0
        results.append({
            'movie': movie,
            'distance': distance,
            'similarity': similarity,
            'substring': q in title,
            'method': 'index'
        })
    return results  # index ka order (zyada words match = upar) rakho


# ============================================================
# UI HELPERS
# ============================================================

EXAMPLE_QUERIES = ["Titanik", "Batmn", "Incepton", "dark knight", "crime"]


@st.cache_data(show_spinner=False)
def poster_src(url):
    """Poster ko data-URI bana do (HTML card mein embed karne ke liye)"""
    data = fetch_poster(url) if url and url != 'N/A' else None
    if data:
        fmt = (Image.open(BytesIO(data)).format or "JPEG").lower()
        return f"data:image/{fmt};base64,{base64.b64encode(data).decode()}"
    return PLACEHOLDER_SVG


PLACEHOLDER_SVG = "data:image/svg+xml;utf8," + quote(
    '<svg xmlns="http://www.w3.org/2000/svg" width="260" height="380">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#23233a"/><stop offset="1" stop-color="#14141f"/></linearGradient></defs>'
    '<rect width="260" height="380" fill="url(#g)"/>'
    '<text x="130" y="185" font-size="64" text-anchor="middle">🎬</text>'
    '<text x="130" y="235" font-size="18" fill="#8b8ba3" text-anchor="middle" '
    'font-family="sans-serif">No Poster</text></svg>'
)


def set_query(value):
    st.session_state["query"] = value


def match_info(result):
    """(label, css class) - kis tarah ka match hai"""
    if result['distance'] == 0:
        return "Exact match", "exact"
    if result['substring']:
        return "Partial match", "partial"
    if result['distance'] <= 3:
        return "Fuzzy match", "fuzzy"
    return "Low match", "low"


def render_card(result):
    movie_id, title, year, genre, rating, plot, poster = result['movie']
    label, css = match_info(result)
    method = "⚡ Index" if result.get('method') == 'index' else "🔤 Fuzzy scan"
    
    chips = "".join(
        f'<span class="chip">{html.escape(g.strip())}</span>'
        for g in (genre or "").split(",") if g.strip() and g.strip() != 'N/A'
    )
    rating_txt = f"⭐ {rating:.1f}/10" if rating else "⭐ N/A"
    plot_txt = plot if plot and plot != 'N/A' else "Plot not available"
    similarity = max(0, min(100, result['similarity']))
    
    return f"""
    <div class="card">
        <img class="poster" src="{poster_src(poster)}" alt="">
        <div class="body">
            <div class="title">{html.escape(str(title))} <span>({html.escape(str(year))})</span></div>
            <div class="chips">{chips}</div>
            <div><span class="rating">{rating_txt}</span></div>
            <div class="bar"><div style="width:{similarity:.0f}%"></div></div>
            <div style="margin-top:.4rem">
                <span class="badge {css}">{label}</span>
                <span class="badge method">{method}</span>
                <span class="meta">distance {result['distance']} · similarity {similarity:.0f}%</span>
            </div>
            <details><summary>Plot</summary>{html.escape(plot_txt)}</details>
        </div>
    </div>
    """


def render_grid(movies):
    tiles = ""
    for movie in movies:
        title, year, rating, poster = movie[1], movie[2], movie[4], movie[6]
        rating_txt = f"⭐ {rating:.1f}" if rating else ""
        tiles += (
            f'<div class="tile"><img src="{poster_src(poster)}" alt="">'
            f'<div class="cap">{html.escape(str(title))}<small>{rating_txt} · {html.escape(str(year))}</small></div></div>'
        )
    return f'<div class="grid">{tiles}</div>'


# ============================================================
# MAIN APP
# ============================================================

def main():
    movies = get_all_movies()
    api_key = "69f58f62"  # Tumhari API key
    
    # ---------- sidebar ----------
    with st.sidebar:
        st.header("➕ Add New Movie")
        new_movie = st.text_input("Movie ka naam:", key="new_movie")
        
        if st.button("Add Movie", use_container_width=True):
            if new_movie:
                with st.spinner("Fetching from OMDB..."):
                    movie_data = fetch_from_omdb(new_movie, api_key)
                    
                    if movie_data:
                        add_movie_to_db(movie_data)
                        get_search_index.clear()  # naya movie index mein aaye
                        st.success(f"✅ Added: {movie_data.get('Title')}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Movie not found!")
            else:
                st.warning("Please enter a movie name")
        
        st.markdown("---")
        st.header("📊 Stats")
        st.metric("Total Movies", len(movies))
        try:
            st.metric("Index words", len(get_search_index()[0]))
        except Exception:
            pass
        
        st.markdown("---")
        st.caption("Typos handle hote hain: Titanik → Titanic, Batmn → Batman, Incepton → Inception")
    
    # ---------- hero ----------
    st.markdown(
        '<div class="hero"><h1>🎬 Fuzzy Movie Search</h1>'
        '<p>Typos ki fikar mat karo — inverted index + fuzzy matching dhoond hi lega.</p></div>',
        unsafe_allow_html=True
    )
    
    search_query = st.text_input(
        "Search",
        key="query",
        placeholder="🔍  Try: Titanik, Batmn, dark knight, crime…",
        label_visibility="collapsed"
    )
    
    chip_cols = st.columns(len(EXAMPLE_QUERIES))
    for col, example in zip(chip_cols, EXAMPLE_QUERIES):
        col.button(example, key=f"ex_{example}", on_click=set_query, args=(example,), use_container_width=True)
    
    # ---------- results ----------
    if search_query.strip():
        results = fuzzy_search(search_query, movies)
        
        st.markdown(
            f'<div class="section-title">Found {len(results)} result{"s" if len(results) != 1 else ""} for “{html.escape(search_query)}”</div>',
            unsafe_allow_html=True
        )
        if results:
            st.markdown("".join(render_card(r) for r in results), unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">Kuch nahi mila 😕 — database khaali hai?</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="section-title">🎲 Popular Movies</div>', unsafe_allow_html=True)
        if movies:
            st.markdown(render_grid(movies[:12]), unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">Database khaali hai — sidebar se movie add karo.</div>', unsafe_allow_html=True)


# ============================================================
# RUN APP
# ============================================================

if __name__ == "__main__":
    main()