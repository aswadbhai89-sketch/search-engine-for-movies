# inverted_index.py

import re
import sqlite3
from collections import defaultdict


def tokenize(text):
    """
    Text ko words mein todta hai
    "The Dark Knight!" -> ["the", "dark", "knight"]
    "Spider-Man"       -> ["spider", "man"]
    """
    if not text:
        return []
    text = text.lower()
    # Non-alphanumeric ko space banao (hyphen wale naam sahi split hon)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return text.split()


def load_movies(db_path='movies.db'):
    """Database se saari movies padho"""
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            'SELECT id, title, year, genre, rating, plot, poster FROM movies'
        ).fetchall()
    finally:
        conn.close()


def build_inverted_index(db_path='movies.db'):
    """
    Database se movies padho aur inverted index banao
    Returns: dict {word: set(movie_ids)}
    """
    index = defaultdict(set)

    for movie in load_movies(db_path):
        movie_id = movie[0]
        title_words = tokenize(movie[1])
        genre_words = tokenize(movie[3])

        for word in set(title_words + genre_words):
            index[word].add(movie_id)

    return dict(index)


def get_movies_dict(db_path='movies.db'):
    """Database se {movie_id: movie_tuple} banao"""
    return {movie[0]: movie for movie in load_movies(db_path)}


def search_with_index(query, index, movies_dict, max_results=10):
    """
    Inverted index se search karo

    Returns: list of movie tuples, ya None agar index me kuch nahi mila
             (None ka matlab: fuzzy search par fallback karo)
    """
    query_words = tokenize(query)

    if not query_words:
        return None

    # {movie_id: kitne query words match hue}
    word_matches = {}
    for word in set(query_words):
        for movie_id in index.get(word, ()):
            word_matches[movie_id] = word_matches.get(movie_id, 0) + 1

    if not word_matches:
        return None

    scored = [
        (score, movies_dict[movie_id])
        for movie_id, score in word_matches.items()
        if movie_id in movies_dict
    ]
    if not scored:
        return None

    # Zyada words match = upar; barabar score par title ke hisaab se (stable order)
    scored.sort(key=lambda x: (-x[0], x[1][1].lower()))

    return [movie for _, movie in scored[:max_results]]


def print_index_stats(index):
    """Index ke stats print karo (debugging ke liye)"""
    print(f"Total unique words: {len(index)}")
    print("Sample entries:")
    for word, ids in list(index.items())[:10]:
        print(f"  '{word}': {len(ids)} movies")
