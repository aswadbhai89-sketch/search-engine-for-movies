
import streamlit as st
import sqlite3
import requests
import time
import os
from PIL import Image
from io import BytesIO

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
    .movie-card {
        background-color: #1e1e1e;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid #333;
    }
    .movie-title {
        color: #ff4b4b;
        font-size: 24px;
        font-weight: bold;
    }
    .movie-info {
        color: #cccccc;
        font-size: 14px;
    }
    .rating {
        color: #ffd700;
        font-size: 18px;
        font-weight: bold;
    }
    .distance {
        color: #00ff00;
        font-size: 12px;
    }
    .exact-match {
        color: #00ff00;
        font-weight: bold;
    }
    .fuzzy-match {
        color: #ffa500;
        font-weight: bold;
    }
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

def get_all_movies():
    """Database ki saari movies nikaalo"""
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM movies')
    movies = cursor.fetchall()
    
    conn.close()
    return movies


def add_movie_to_db(movie_data):
    """Nayi movie database mein add karo"""
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    
    try:
        rating = float(movie_data.get('imdbRating', 0))
    except:
        rating = 0.0
    
    cursor.execute('''
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
    conn.close()


def fetch_from_omdb(title, api_key):
    """OMDB se movie fetch karo"""
    url = f"http://www.omdbapi.com/?t={title}&apikey={api_key}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('Response') == 'True':
            return data
        return None
    except:
        return None


# ============================================================
# SEARCH FUNCTION
# ============================================================

def fuzzy_search(query, movies, max_results=10):
    """Fuzzy search karo"""
    query = query.lower()
    results = []
    
    for movie in movies:
        # movie tuple: (id, title, year, genre, rating, plot, poster)
        title = movie[1].lower()
        distance = levenshtein_distance(query, title)
        
        # Similarity score calculate karo (0-100%)
        max_len = max(len(query), len(title))
        similarity = ((max_len - distance) / max_len) * 100 if max_len > 0 else 0
        
        results.append({
            'movie': movie,
            'distance': distance,
            'similarity': similarity
        })
    
    # Distance ke hisaab se sort karo
    results.sort(key=lambda x: x['distance'])
    
    return results[:max_results]


# ============================================================
# MAIN APP
# ============================================================

def main():
    # Title
    st.title("🎬 Fuzzy Movie Search Engine")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("ℹ️ About")
        st.info("""
        Yeh ek **Fuzzy Search Engine** hai jo typos ko handle karta hai.
        
        **Example:**
        - "Titanik" → "Titanic" ✅
        - "Batmn" → "Batman" ✅
        - "Incepton" → "Inception" ✅
        """)
        
        st.markdown("---")
        
        # Add new movie section
        st.header("➕ Add New Movie")
        new_movie = st.text_input("Movie ka naam:")
        api_key = os.environ.get("OMDB_API_KEY") or st.secrets.get("OMDB_API_KEY", "")
        
        if st.button("Add Movie"):
            if not api_key:
                st.error("OMDB_API_KEY is not set. See README.")
            elif new_movie:
                with st.spinner("Fetching from OMDB..."):
                    movie_data = fetch_from_omdb(new_movie, api_key)
                    
                    if movie_data:
                        add_movie_to_db(movie_data)
                        st.success(f"✅ Added: {movie_data.get('Title')}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Movie not found!")
            else:
                st.warning("Please enter a movie name")
        
        st.markdown("---")
        
        # Stats
        movies = get_all_movies()
        st.header("📊 Stats")
        st.metric("Total Movies", len(movies))
    
    # Main content
    st.header("🔍 Search Movies")
    
    # Search box
    search_query = st.text_input(
        "Movie ka naam type karo (typos chalega):",
        placeholder="e.g., Titanik, Batmn, Incepton..."
    )
    
    if search_query:
        # Search karo
        results = fuzzy_search(search_query, movies)
        
        # Results count
        st.markdown(f"### 🔎 Found {len(results)} results for '{search_query}'")
        st.markdown("---")
        
        # Results dikhayo
        for i, result in enumerate(results, 1):
            movie = result['movie']
            distance = result['distance']
            similarity = result['similarity']
            
            # Movie data extract karo
            movie_id, title, year, genre, rating, plot, poster = movie
            
            # Match type
            if distance == 0:
                match_type = "EXACT MATCH"
                match_class = "exact-match"
            elif distance <= 3:
                match_type = "FUZZY MATCH"
                match_class = "fuzzy-match"
            else:
                match_type = "PARTIAL MATCH"
                match_class = "fuzzy-match"
            
            # Card layout
            col1, col2 = st.columns([1, 3])
            
            with col1:
                # Poster
                if poster and poster != 'N/A':
                    try:
                        response = requests.get(poster, timeout=5)
                        img = Image.open(BytesIO(response.content))
                        st.image(img, width=150)
                    except:
                        st.image("https://via.placeholder.com/150x220?text=No+Poster", width=150)
                else:
                    st.image("https://via.placeholder.com/150x220?text=No+Poster", width=150)
            
            with col2:
                # Movie info
                st.markdown(f'<p class="movie-title">{title} ({year})</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="movie-info">📁 {genre}</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="rating">⭐ {rating}/10</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="distance">📏 Distance: {distance} | Similarity: {similarity:.1f}%</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="{match_class}">{match_type}</p>', unsafe_allow_html=True)
                
                # Expander for plot
                with st.expander("📖 Plot"):
                    st.write(plot if plot and plot != 'N/A' else "Plot not available")
            
            st.markdown("---")
    else:
        # Default message
        st.info("👆 Upar movie ka naam type karo toh search shuru karo!")
        
        # Show some random movies
        st.markdown("### 🎲 Popular Movies")
        
        col1, col2, col3 = st.columns(3)
        
        for i, movie in enumerate(movies[:6]):
            with [col1, col2, col3][i % 3]:
                movie_id, title, year, genre, rating, plot, poster = movie
                
                if poster and poster != 'N/A':
                    try:
                        response = requests.get(poster, timeout=5)
                        img = Image.open(BytesIO(response.content))
                        st.image(img, use_container_width=True)
                    except:
                        pass
                
                st.markdown(f"**{title}** ({year})")
                st.markdown(f"⭐ {rating}/10")


# ============================================================
# RUN APP
# ============================================================

if __name__ == "__main__":
    main()