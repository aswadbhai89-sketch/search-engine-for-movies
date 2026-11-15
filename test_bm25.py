# test_bm25.py - BM25 relevance checks, comparison with TF-IDF, parameter tuning
# Run: python test_bm25.py

import sys
import time

from bm25_search import (
    build_bm25_index,
    explain_bm25_score,
    print_bm25_stats,
    search_bm25,
)
from inverted_index import get_movies_dict
from tfidf_search import build_tfidf_index, search_tfidf

# query -> acceptable top results (None = no results expected)
EXPECTED = {
    "batman gotham": {"Batman", "The Dark Knight"},
    "dream heist": {"Inception"},
    "joker": {"The Dark Knight", "Batman"},
    "astronauts mission": {"Interstellar"},
    "mafia": {"GoodFellas"},
    "love story": {"Titanic", "GoodFellas"},
    "hacker simulation": {"The Matrix"},
    "the": None,   # stopword only
    "xyz": None,
}


def check_relevance(index, tfidf_index, movies_dict):
    failures = 0
    for query, expected in EXPECTED.items():
        start = time.perf_counter()
        bm25 = search_bm25(query, index, movies_dict, max_results=3)
        bm25_time = time.perf_counter() - start

        start = time.perf_counter()
        tfidf = search_tfidf(query, tfidf_index, movies_dict, max_results=3)
        tfidf_time = time.perf_counter() - start

        top = bm25[0][0][1] if bm25 else None
        ok = (top is None) if expected is None else (top in expected)
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  '{query}' -> {top}")
        print(f"      BM25   {bm25_time * 1000:.3f} ms: " + ", ".join(f"{m[1]} ({s:.2f})" for m, s in bm25))
        print(f"      TF-IDF {tfidf_time * 1000:.3f} ms: " + ", ".join(f"{m[1]} ({s:.2f})" for m, s in tfidf))
    return failures


def tune_params(index, movies_dict, query="batman gotham"):
    """Show how k1 and b change the ranking of one query."""
    print(f"\nParameter tuning for '{query}':")
    for params in ({'k1': 1.2, 'b': 0.75}, {'k1': 1.5, 'b': 0.75}, {'k1': 2.0, 'b': 0.75},
                   {'k1': 1.5, 'b': 0.5}, {'k1': 1.5, 'b': 1.0}):
        results = search_bm25(query, index, movies_dict, max_results=3, params=params)
        print(f"  k1={params['k1']}, b={params['b']}: " + ", ".join(f"{m[1]} ({s:.2f})" for m, s in results))


def main():
    movies_dict = get_movies_dict()

    start = time.perf_counter()
    index = build_bm25_index()
    print(f"BM25 index built in {time.perf_counter() - start:.4f}s")
    print_bm25_stats(index)
    print()

    failures = check_relevance(index, build_tfidf_index(), movies_dict)

    tune_params(index, movies_dict)

    top = search_bm25("batman gotham", index, movies_dict, max_results=1)
    if top:
        explain_bm25_score("batman gotham", top[0][0][0], index)

    print()
    print("All checks passed." if not failures else f"{failures} check(s) failed.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
