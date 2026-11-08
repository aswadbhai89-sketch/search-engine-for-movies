import sqlite3
import requests
import time
import os

# ============================================================
# DATABASE BANAO
# ============================================================

def create_database():
    """Database file banao aur table banao"""
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    
    cursor.execute('''
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
    conn.close()
    print("✅ Database ready!")


# ============================================================
# OMDB SE MOVIE FETCH KARO
# ============================================================

def fetch_movie(title, api_key):
    """OMDB se ek movie ki details lo"""
    url = f"http://www.omdbapi.com/?t={title}&apikey={api_key}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get('Response') == 'True':
            return data
        else:
            print(f"❌ Movie nahi mili: {title}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


# ============================================================
# DATABASE MEIN SAVE KARO
# ============================================================

def save_movie(movie_data):
    """Movie ko database mein save karo"""
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
    print(f"✅ Saved: {movie_data.get('Title')}")


# ============================================================
# SAARI MOVIES FETCH KARO
# ============================================================

def main():
    API_KEY = os.environ.get("OMDB_API_KEY")
    if not API_KEY:
        raise SystemExit("Set OMDB_API_KEY environment variable first (see README).")
    
    create_database()
    
    movies_list = [
        "Titanic",
        "The Dark Knight",
        "Inception",
        "Interstellar",
        "The Shawshank Redemption",
        "Pulp Fiction",
        "Fight Club",
        "Forrest Gump",
        "The Matrix",
        "Goodfellas"
    ]
    
    print(f"\n🎬 {len(movies_list)} movies fetch kar rahi hoon...\n")
    
    for i, title in enumerate(movies_list, 1):
        print(f"[{i}/{len(movies_list)}] Fetching: {title}")
        
        movie_data = fetch_movie(title, API_KEY)
        
        if movie_data:
            save_movie(movie_data)
        
        time.sleep(1)
    
    print("\n" + "="*50)
    print("✅ Saari movies database mein save ho gayi!")
    print("="*50)


# ============================================================
# SAARI MOVIES DIKHao
# ============================================================

def show_all_movies():
    """Database ki saari movies dikhayo"""
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT title, year, genre, rating FROM movies')
    movies = cursor.fetchall()
    
    print(f"\n📊 Total movies: {len(movies)}")
    print("-" * 60)
    print(f"{'Title':<35} {'Year':<8} {'Rating':<8}")
    print("-" * 60)
    
    for movie in movies:
        title, year, genre, rating = movie
        print(f"{title:<35} {year:<8} {rating:<8}")
    
    conn.close()


# ============================================================
# RUN KARO
# ============================================================

if __name__ == "__main__":
    main()
    show_all_movies()