import sqlite3

# ============================================================
# LEVENSHTEIN DISTANCE (Typo Correction)
# ============================================================

def levenshtein_distance(s1, s2):
    """
    Do strings ke beech kitne characters different hain
    Example: "Titanik" vs "Titanic" = 1
    """
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
# DATABASE SE MOVIES NIKAO
# ============================================================

def get_all_movies():
    """Database ki saari movies nikaalo"""
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM movies')
    movies = cursor.fetchall()
    
    conn.close()
    return movies


# ============================================================
# FUZZY SEARCH KARO
# ============================================================

def fuzzy_search(query, movies, max_results=5):
    """
    User ke input se best movies dhundo
    (typos allowed)
    """
    query = query.lower().strip()
    results = []
    
    for movie in movies:
        title = movie[1].lower()
        distance = levenshtein_distance(query, title)
        results.append((movie, distance, query in title))
    
    # Pehle substring matches ("bat" -> "Batman"), phir kam distance wale
    results.sort(key=lambda x: (not x[2], x[1]))
    
    return results[:max_results]


# ============================================================
# MAIN FUNCTION (USER INPUT LEGA)
# ============================================================

def main():
    # Database se saari movies nikaalo
    movies = get_all_movies()
    print(f"📊 Database mein {len(movies)} movies hain\n")
    
    while True:
        # User se input lo
        user_input = input("🔍 Movie ka naam type karo (ya 'exit' likho): ")
        
        if user_input.lower() == 'exit':
            print("👋 Alvida!")
            break
        
        # Fuzzy search karo
        results = fuzzy_search(user_input, movies)
        
        # Results dikhayo
        print(f"\n🔎 Results for '{user_input}':")
        print("-" * 60)
        
        for i, (movie, distance, _) in enumerate(results, 1):
            movie_id, title, year, genre, rating, plot, poster = movie
            print(f"{i}. {title} ({year})")
            print(f"   Genre: {genre}")
            print(f"   Rating: {rating}")
            print(f"   Distance: {distance}")
            print()
        
        print("-" * 60)


# ============================================================
# RUN KARO
# ============================================================

if __name__ == "__main__":
    main()
