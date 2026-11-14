# ngram_index.py - character n-gram index for typo-tolerant title search

from collections import defaultdict

from inverted_index import load_movies, tokenize

NGRAM_SIZE = 3
MIN_SIMILARITY = 0.35


def generate_ngrams(text, n=NGRAM_SIZE):
    """
    Character n-grams of each word in `text`, as a set.
    Grams never cross word boundaries.

    "titanic"     -> {"tit", "ita", "tan", "ani", "nic"}
    "dark knight" -> {"dar", "ark", "kni", "nig", "igh", "ght"}
    Words of n characters or fewer are kept whole ("the" -> {"the"}).
    """
    grams = set()
    for word in tokenize(text):
        if len(word) <= n:
            grams.add(word)
        else:
            grams.update(word[i:i + n] for i in range(len(word) - n + 1))
    return grams


def dice(a, b):
    """Dice coefficient of two sets: 1.0 = identical, 0.0 = nothing shared."""
    if not a or not b:
        return 0.0
    return 2 * len(a & b) / (len(a) + len(b))


def build_ngram_index(db_path='movies.db', n=NGRAM_SIZE, movies=None):
    """
    Build an n-gram -> movie ids index over movie titles.
    (Genres are covered by the word index, so they are not repeated here.)
    """
    index = defaultdict(set)
    for movie in (movies if movies is not None else load_movies(db_path)):
        for gram in generate_ngrams(movie[1], n):
            index[gram].add(movie[0])
    return dict(index)


def search_with_ngrams(query, ngram_index, movies_dict, n=NGRAM_SIZE,
                       max_results=10, min_similarity=MIN_SIMILARITY):
    """
    Typo-tolerant title search.
    Returns: list of (movie, similarity) with similarity in 0.0-1.0, best first.
    """
    query_grams = generate_ngrams(query, n)
    if not query_grams:
        return []

    # Count how many n-grams each candidate title shares with the query
    shared = defaultdict(int)
    for gram in query_grams:
        for movie_id in ngram_index.get(gram, ()):
            shared[movie_id] += 1

    results = []
    for movie_id, count in shared.items():
        movie = movies_dict.get(movie_id)
        if not movie:
            continue
        title_grams = generate_ngrams(movie[1], n)
        similarity = 2 * count / (len(query_grams) + len(title_grams))
        if similarity >= min_similarity:
            results.append((movie, similarity))

    results.sort(key=lambda x: (-x[1], x[0][1].lower()))
    return results[:max_results]


def search_hybrid(query, word_index, ngram_index, movies_dict, n=NGRAM_SIZE,
                  max_results=10, min_similarity=MIN_SIMILARITY):
    """
    Word index (exact words, titles + genres) combined with the n-gram index (typos).

    Returns a list of dicts, best first:
        movie       the movie tuple
        similarity  0-100, n-gram overlap between the query and the title
        kind        "exact" | "title" | "genre" | "typo"
    Returns [] when nothing matches (caller may fall back to a full scan).
    """
    query_words = set(tokenize(query))
    query_grams = generate_ngrams(query, n)
    if not query_words:
        return []

    # Candidates: any movie sharing a word or an n-gram with the query
    candidates = set()
    for word in query_words:
        candidates |= word_index.get(word, set())
    for gram in query_grams:
        candidates |= ngram_index.get(gram, set())

    normalized_query = " ".join(tokenize(query))
    scored = []
    for movie_id in candidates:
        movie = movies_dict.get(movie_id)
        if not movie:
            continue

        title_words = set(tokenize(movie[1]))
        title_hits = len(query_words & title_words)
        genre_hits = len(query_words & set(tokenize(movie[3])))
        similarity = dice(query_grams, generate_ngrams(movie[1], n))

        if normalized_query == " ".join(tokenize(movie[1])):
            kind = "exact"
        elif title_hits:
            kind = "title"
        elif genre_hits:
            kind = "genre"
        elif similarity >= min_similarity:
            kind = "typo"
        else:
            continue  # shares a stray n-gram only - not a real match

        score = (10 if kind == "exact" else 0) + 2 * title_hits + genre_hits + similarity
        scored.append((score, {
            'movie': movie,
            'similarity': similarity * 100,
            'kind': kind,
        }))

    scored.sort(key=lambda x: (-x[0], x[1]['movie'][1].lower()))
    return [item for _, item in scored[:max_results]]


def print_ngram_stats(ngram_index):
    """Print n-gram index statistics (for debugging)."""
    print(f"Total unique n-grams: {len(ngram_index)}")
    print("Sample entries:")
    for gram, ids in list(ngram_index.items())[:10]:
        print(f"  '{gram}': {len(ids)} movies")
