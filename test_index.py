# test_index.py - inverted index vs full fuzzy scan (python test_index.py)

import time

from fuzzy_search import fuzzy_search, get_all_movies
from inverted_index import (
    build_inverted_index,
    get_movies_dict,
    print_index_stats,
    search_with_index,
)


def test_performance():
    movies = get_all_movies()
    movies_dict = get_movies_dict()

    start = time.perf_counter()
    index = build_inverted_index()
    print(f"✅ Index build time: {time.perf_counter() - start:.4f}s")
    print_index_stats(index)
    print()

    for query in ["dark", "knight", "inception", "batman", "titanic", "titanik", "xyz"]:
        print(f"Query: '{query}'")

        start = time.perf_counter()
        results_old = fuzzy_search(query, movies)
        time_old = time.perf_counter() - start

        start = time.perf_counter()
        results_new = search_with_index(query, index, movies_dict)
        time_new = time.perf_counter() - start

        print(f"  Fuzzy: {len(results_old)} results in {time_old:.6f}s")
        if results_new:
            print(f"  Index: {len(results_new)} results in {time_new:.6f}s")
            print(f"  Speedup: {time_old / max(time_new, 1e-9):.1f}x")
            print(f"  Top result: {results_new[0][1]}")
        else:
            print("  Index: No results (app falls back to fuzzy search)")
        print()


if __name__ == "__main__":
    test_performance()
