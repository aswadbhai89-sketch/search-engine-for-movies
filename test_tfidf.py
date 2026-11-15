# test_tfidf.py - plot/genre relevance checks and timings (python test_tfidf.py)

import sys
import time

from fuzzy_search import fuzzy_search as levenshtein_scan, get_all_movies
from inverted_index import get_movies_dict
from tfidf_search import build_tfidf_index, print_tfidf_stats, search_tfidf

# query -> acceptable top results (None = no results expected)
EXPECTED = {
    "batman gotham": {"Batman", "The Dark Knight"},
    "dream heist": {"Inception"},
    "joker": {"The Dark Knight", "Batman"},
    "astronauts mission": {"Interstellar"},
    "mafia": {"GoodFellas"},
    "love story": {"Titanic", "GoodFellas"},
    "hacker simulation": {"The Matrix"},
    "xyz": None,
}


def main():
    movies = get_all_movies()
    movies_dict = get_movies_dict()

    start = time.perf_counter()
    index = build_tfidf_index()
    print(f"TF-IDF index built in {time.perf_counter() - start:.4f}s")
    print_tfidf_stats(index)
    print()

    failures = 0
    for query, expected in EXPECTED.items():
        start = time.perf_counter()
        results = search_tfidf(query, index, movies_dict, max_results=3)
        tfidf_time = time.perf_counter() - start

        start = time.perf_counter()
        levenshtein_scan(query, movies, max_results=3)
        scan_time = time.perf_counter() - start

        top = results[0][0][1] if results else None
        ok = (top is None) if expected is None else (top in expected)
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  '{query}' -> {top}")
        for movie, score in results:
            print(f"        {movie[1]:<28} score {score:.3f}")
        print(f"      tf-idf {tfidf_time * 1000:.3f} ms | Levenshtein scan {scan_time * 1000:.3f} ms")

    print()
    print("All checks passed." if not failures else f"{failures} check(s) failed.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
