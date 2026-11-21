"""Shared synthetic MovieLens-style data so tests are fast and need no downloads."""
import numpy as np
import pandas as pd

from src import MovieRecommender


def make_engine() -> MovieRecommender:
    rng = np.random.default_rng(0)
    scifi = ["Alien", "Blade Runner", "The Matrix", "Terminator", "Robocop"]
    anim = ["Toy Story", "Up", "Finding Nemo", "Coco", "Shrek"]
    genres = ["Sci-Fi|Action"] * 5 + ["Animation|Children"] * 5
    ratings = []
    for u in range(1, 101):
        liked, other = (range(0, 5), range(5, 10)) if u % 2 else (range(5, 10), range(0, 5))
        ratings += [(u, i + 1, float(rng.integers(4, 6))) for i in liked]
        ratings += [(u, i + 1, float(rng.integers(1, 3))) for i in other]
    stats = pd.DataFrame(ratings).groupby(1)[2].agg(["size", "mean"])
    movies = pd.DataFrame({"movieId": range(1, 11), "title": scifi + anim, "year": 1990, "genres": genres,
                           "n_ratings": stats["size"].values, "avg_rating": stats["mean"].values.round(3)})
    return MovieRecommender("test", movies=movies,
                            ratings=pd.DataFrame(ratings, columns=["userId", "movieId", "rating"]))
