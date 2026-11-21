"""Convert raw MovieLens files into the project's processed format.

Examples (run from the project root, after extracting the zip files):
    python -m scripts.prepare_data --raw raw/ml-latest-small --name ml-small
    python -m scripts.prepare_data --raw raw/ml-1m --name ml-1m
    python -m scripts.prepare_data --raw raw/ml-25m --name ml-25m-top --max-users 20000 --max-movies 5000
"""
import argparse

from src.data import prepare_dataset

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", required=True, help="Folder containing movies/ratings files")
    ap.add_argument("--name", required=True, help="Output dataset name")
    ap.add_argument("--max-movies", type=int, help="Keep only the N most-rated movies")
    ap.add_argument("--max-users", type=int, help="Keep only users with id <= N (for huge files)")
    ap.add_argument("--min-movie-ratings", type=int, default=5)
    a = ap.parse_args()
    out = prepare_dataset(a.raw, a.name, a.max_movies, a.max_users, a.min_movie_ratings)
    print(f"Saved processed dataset to {out}")
