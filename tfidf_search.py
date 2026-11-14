# tfidf_search.py - rank movies by how well a query matches titles, genres and plots

import math
from collections import Counter, defaultdict

from inverted_index import load_movies, tokenize

STOPWORDS = {
    'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
    'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'shall',
    'can', 'need', 'and', 'or', 'but', 'if', 'then', 'else', 'when', 'where', 'why',
    'how', 'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'i',
    'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my',
    'your', 'his', 'its', 'our', 'their', 'as', 'into', 'who', 'one', 'two',
}

# A title word says more about a movie than a plot word, so titles and genres are
# repeated when the searchable document is built.
TITLE_WEIGHT = 3
GENRE_WEIGHT = 2


def extract_terms(text):
    """
    Lowercase words without stopwords, with plurals folded ("fights" -> "fight").
    """
    terms = []
    for word in tokenize(text):
        if word in STOPWORDS or len(word) < 2:
            continue
        if len(word) > 3 and word.endswith('s') and not word.endswith('ss'):
            word = word[:-1]
        terms.append(word)
    return terms


def document_terms(movie):
    """Searchable terms of one movie: title (x3) + genre (x2) + plot."""
    title = movie[1] or ""
    genre = movie[3] or ""
    plot = movie[5] if movie[5] and movie[5] != 'N/A' else ""
    return (
        extract_terms(title) * TITLE_WEIGHT
        + extract_terms(genre) * GENRE_WEIGHT
        + extract_terms(plot)
    )


def compute_idf(documents):
    """
    Smoothed inverse document frequency: log((1 + N) / (1 + df)) + 1.
    Rare words score high; a word in every document still keeps a small weight.
    documents: list of term lists. Returns {term: idf}.
    """
    n_docs = len(documents)
    doc_freq = defaultdict(int)
    for terms in documents:
        for term in set(terms):
            doc_freq[term] += 1
    return {term: math.log((1 + n_docs) / (1 + df)) + 1 for term, df in doc_freq.items()}


def compute_tfidf(terms, idf):
    """TF-IDF vector {term: weight}. TF = count / number of terms in the text."""
    if not terms:
        return {}
    counts = Counter(terms)
    total = len(terms)
    return {term: (count / total) * idf[term] for term, count in counts.items() if term in idf}


def build_tfidf_index(db_path='movies.db', movies=None):
    """
    Build the TF-IDF index.
    Returns a dict:
        idf       {term: idf}
        postings  {term: [(movie_id, weight), ...]}
        norms     {movie_id: vector length}
    """
    movies = movies if movies is not None else load_movies(db_path)
    documents = {movie[0]: document_terms(movie) for movie in movies}
    idf = compute_idf(list(documents.values()))

    postings = defaultdict(list)
    norms = {}
    for movie_id, terms in documents.items():
        vector = compute_tfidf(terms, idf)
        norms[movie_id] = math.sqrt(sum(w * w for w in vector.values()))
        for term, weight in vector.items():
            postings[term].append((movie_id, weight))

    return {'idf': idf, 'postings': dict(postings), 'norms': norms}


def search_tfidf(query, index, movies_dict, max_results=10, min_score=0.05):
    """
    Cosine similarity between the query and every movie sharing a term with it.
    Only the postings of the query's terms are visited, never the whole collection.
    Returns: list of (movie, score) with score in 0.0-1.0, best first.
    """
    query_vector = compute_tfidf(extract_terms(query), index['idf'])
    if not query_vector:
        return []

    query_norm = math.sqrt(sum(w * w for w in query_vector.values()))
    dot = defaultdict(float)
    for term, q_weight in query_vector.items():
        for movie_id, weight in index['postings'].get(term, ()):
            dot[movie_id] += q_weight * weight

    results = []
    for movie_id, value in dot.items():
        movie = movies_dict.get(movie_id)
        norm = index['norms'].get(movie_id, 0)
        if not movie or not norm:
            continue
        score = value / (query_norm * norm)
        if score >= min_score:
            results.append((movie, score))

    results.sort(key=lambda x: (-x[1], x[0][1].lower()))
    return results[:max_results]


def print_tfidf_stats(index):
    """Print index statistics (for debugging)."""
    idf = index['idf']
    print(f"Movies in index: {len(index['norms'])}")
    print(f"Unique terms: {len(idf)}")
    print("Rarest terms (highest IDF):")
    for term, score in sorted(idf.items(), key=lambda x: -x[1])[:5]:
        print(f"  '{term}': {score:.3f}")
