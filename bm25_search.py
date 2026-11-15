# bm25_search.py - BM25 ranking over titles, genres and plots

import math
from collections import Counter, defaultdict

from inverted_index import load_movies
from tfidf_search import document_terms, extract_terms

K1 = 1.5   # term-frequency saturation: higher = repeated words keep helping for longer
B = 0.75   # length normalisation: 0 = ignore document length, 1 = fully normalise


def compute_idf_bm25(total_docs, doc_freq):
    """
    BM25 IDF: log((N - df + 0.5) / (df + 0.5) + 1)
    N = number of documents, df = documents containing the term. Always positive.
    """
    return math.log((total_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1)


def build_bm25_index(db_path='movies.db', movies=None, k1=K1, b=B):
    """
    Build the BM25 index. Returns a dict:
        docs      {movie_id: {'tf': {term: count}, 'length': n_terms}}
        postings  {term: [(movie_id, tf), ...]}
        idf       {term: idf}
        avgdl     average document length
        params    {'k1': k1, 'b': b}
    Documents use the same terms as the TF-IDF index (title x3, genre x2, plot).
    """
    movies = movies if movies is not None else load_movies(db_path)

    docs, postings, doc_freq = {}, defaultdict(list), defaultdict(int)
    total_length = 0
    for movie in movies:
        terms = document_terms(movie)
        tf = Counter(terms)
        docs[movie[0]] = {'tf': dict(tf), 'length': len(terms)}
        total_length += len(terms)
        for term, count in tf.items():
            postings[term].append((movie[0], count))
            doc_freq[term] += 1

    n_docs = len(docs)
    return {
        'docs': docs,
        'postings': dict(postings),
        'idf': {term: compute_idf_bm25(n_docs, df) for term, df in doc_freq.items()},
        'avgdl': total_length / n_docs if n_docs else 0,
        'params': {'k1': k1, 'b': b},
    }


def term_score(tf, idf, doc_length, avgdl, k1, b):
    """BM25 contribution of one query term to one document."""
    norm = 1 - b + b * (doc_length / avgdl if avgdl else 0)
    return idf * (tf * (k1 + 1)) / (tf + k1 * norm)


def search_bm25(query, index, movies_dict, max_results=10, min_relative=0.0, params=None):
    """
    Rank movies for `query` with BM25. Only the postings of the query's terms are visited.

    min_relative: drop results scoring below this fraction of the best score
                  (0.2 removes weak tails when the query has several words).
    params:       optional {'k1': ..., 'b': ...} to override the index defaults.
    Returns: list of (movie, score), best first. Scores are not capped at 1.
    """
    terms = set(extract_terms(query))
    if not terms:
        return []

    k1 = (params or index['params']).get('k1', K1)
    b = (params or index['params']).get('b', B)
    idf, docs, avgdl = index['idf'], index['docs'], index['avgdl']

    scores = defaultdict(float)
    for term in terms:
        for movie_id, tf in index['postings'].get(term, ()):
            scores[movie_id] += term_score(tf, idf[term], docs[movie_id]['length'], avgdl, k1, b)

    if not scores:
        return []

    cutoff = max(scores.values()) * min_relative
    results = [
        (movies_dict[movie_id], score)
        for movie_id, score in scores.items()
        if score >= cutoff and movie_id in movies_dict
    ]
    results.sort(key=lambda x: (-x[1], x[0][1].lower()))
    return results[:max_results]


def print_bm25_stats(index):
    """Print index statistics (for debugging)."""
    print(f"Movies in index: {len(index['docs'])}")
    print(f"Unique terms: {len(index['idf'])}")
    print(f"Average document length: {index['avgdl']:.2f} terms")
    print(f"Parameters: k1={index['params']['k1']}, b={index['params']['b']}")
    print("Rarest terms (highest IDF):")
    for term, score in sorted(index['idf'].items(), key=lambda x: -x[1])[:5]:
        print(f"  '{term}': {score:.4f}")


def explain_bm25_score(query, movie_id, index):
    """Print, term by term, how a movie's BM25 score for `query` is made up."""
    terms = sorted(set(extract_terms(query)))
    doc = index['docs'][movie_id]
    k1, b = index['params']['k1'], index['params']['b']

    print(f"\nQuery: '{query}'  ->  terms {terms}")
    print(f"Movie {movie_id}: length={doc['length']}, avgdl={index['avgdl']:.2f}")
    print(f"\n{'Term':<14}{'TF':<5}{'IDF':<9}{'Score part':<12}")
    print("-" * 40)

    total = 0.0
    for term in terms:
        tf = doc['tf'].get(term, 0)
        idf = index['idf'].get(term, 0)
        if tf:
            part = term_score(tf, idf, doc['length'], index['avgdl'], k1, b)
            total += part
            print(f"{term:<14}{tf:<5}{idf:<9.4f}{part:<12.4f}")
        else:
            print(f"{term:<14}{tf:<5}{idf:<9.4f}{'0 (not in doc)':<12}")
    print("-" * 40)
    print(f"{'TOTAL':<28}{total:.4f}")
    return total
