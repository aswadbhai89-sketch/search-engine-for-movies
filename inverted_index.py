# inverted_index.py

import re
import sqlite3
from collections import defaultdict


def tokenize(text):
    """
    Split text into lowercase words.
    "The Dark Knight!" -> ["the", "dark", "knight"]
    "Spider-Man"       -> ["spider", "man"]
    """
    if not text:
        return []
    text = text.lower()
    # Replace punctuation with spaces so hyphenated names split correctly
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return text.split()


def load_movies(db_path='movies.db'):
    """Read all movies from the database."""
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            'SELECT id, title, year, genre, rating, plot, poster FROM movies'
        ).fetchall()
    finally:
        conn.close()


def build_inverted_index(db_path='movies.db', movies=None):
    """
    Build a word -> movie ids index over titles and genres.
    Returns: dict {word: set(movie_ids)}
    """
    index = defaultdict(set)

    for movie in (movies if movies is not None else load_movies(db_path)):
        movie_id = movie[0]
        title_words = tokenize(movie[1])
        genre_words = tokenize(movie[3])

        for word in set(title_words + genre_words):
            index[word].add(movie_id)

    return dict(index)


def get_movies_dict(db_path='movies.db', movies=None):
    """Build {movie_id: movie_tuple}."""
    return {movie[0]: movie for movie in (movies if movies is not None else load_movies(db_path))}


def search_with_index(query, index, movies_dict, max_results=10):
    """
    Look up query words in the inverted index.

    Returns: list of movie tuples, or None when nothing matched
             (None means: fall back to a fuzzier search).
    """
    query_words = tokenize(query)

    if not query_words:
        return None

    # {movie_id: number of query words matched}
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

    # More matched words first; ties broken alphabetically for a stable order
    scored.sort(key=lambda x: (-x[0], x[1][1].lower()))

    return [movie for _, movie in scored[:max_results]]


def print_index_stats(index):
    """Print index statistics (for debugging)."""
    print(f"Total unique words: {len(index)}")
    print("Sample entries:")
    for word, ids in list(index.items())[:10]:
        print(f"  '{word}': {len(ids)} movies")
