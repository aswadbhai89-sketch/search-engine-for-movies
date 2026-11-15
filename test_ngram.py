# test_ngram.py - checks typo handling and compares timings (python test_ngram.py)

import sys
import time

from fuzzy_search import fuzzy_search as levenshtein_scan, get_all_movies
from inverted_index import build_inverted_index, get_movies_dict
from ngram_index import (
    build_ngram_index,
    print_ngram_stats,
    search_hybrid,
    search_with_ngrams,
)

# query -> title that must come first (None = no results expected)
EXPECTED = {
    "titanic": "Titanic",
    "titanik": "Titanic",
    "dark knight": "The Dark Knight",
    "dark knigt": "The Dark Knight",
    "inception": "Inception",
    "incepton": "Inception",
    "batman": "Batman",
    "batmn": "Batman",
    "xyz": None,
}


def main():
    movies = get_all_movies()
    movies_dict = get_movies_dict()

    start = time.perf_counter()
    word_index = build_inverted_index()
    ngram_index = build_ngram_index()
    print(f"Indexes built in {time.perf_counter() - start:.4f}s")
    print(f"Word index: {len(word_index)} words | N-gram index: {len(ngram_index)} n-grams")
    print_ngram_stats(ngram_index)
    print()

    failures = 0
    for query, expected in EXPECTED.items():
        start = time.perf_counter()
        hybrid = search_hybrid(query, word_index, ngram_index, movies_dict, max_results=5)
        hybrid_time = time.perf_counter() - start

        start = time.perf_counter()
        ngram = search_with_ngrams(query, ngram_index, movies_dict, max_results=5)
        ngram_time = time.perf_counter() - start

        start = time.perf_counter()
        scan = levenshtein_scan(query, movies, max_results=5)
        scan_time = time.perf_counter() - start

        top = hybrid[0]['movie'][1] if hybrid else None
        ok = top == expected
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  '{query}' -> {top}  (expected {expected})")
        print(f"      hybrid {hybrid_time * 1000:.3f} ms | n-gram only {ngram_time * 1000:.3f} ms "
              f"({len(ngram)} hits) | Levenshtein scan {scan_time * 1000:.3f} ms")

    print()
    print("All checks passed." if not failures else f"{failures} check(s) failed.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
