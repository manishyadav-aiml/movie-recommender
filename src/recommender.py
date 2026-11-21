"""High-level recommender used by the app, CLI and tests."""
from __future__ import annotations

import difflib
import os
from pathlib import Path

import numpy as np
import pandas as pd

from .data import available_datasets, load_processed
from .models import ContentModel, ItemCF, PopularityModel, minmax, weighted_rating


class MovieNotFoundError(ValueError):
    """Raised when a title cannot be matched to the dataset."""


def default_dataset() -> str:
    env = os.environ.get("MOVIES_DATASET")
    if env:
        return env
    found = available_datasets()
    if not found:
        raise FileNotFoundError("No processed dataset found. Run: python -m scripts.prepare_data ...")
    return "ml-1m" if "ml-1m" in found else found[0]


class MovieRecommender:
    """Hybrid recommender: collaborative filtering + genre content + popularity prior.

    final = w_cf * CF + w_content * content + w_pop * popularity   (each min-max scaled)
    """

    def __init__(self, dataset: str | None = None, weights: tuple[float, float, float] = (0.7, 0.25, 0.05),
                 movies: pd.DataFrame | None = None, ratings: pd.DataFrame | None = None):
        if abs(sum(weights) - 1) > 1e-6 or min(weights) < 0:
            raise ValueError("weights must be non-negative and sum to 1")
        self.dataset = dataset or default_dataset()
        self.weights = weights
        if movies is None or ratings is None:
            movies, ratings = load_processed(self.dataset)
        self.movies = movies.reset_index(drop=True)
        self.movies["display"] = [
            f"{t} ({y})" if y else t for t, y in zip(self.movies["title"], self.movies["year"])]
        self.movies["wr"] = weighted_rating(self.movies["avg_rating"], self.movies["n_ratings"]).round(3)
        self._pos = {m: i for i, m in enumerate(self.movies["movieId"])}
        self._lower = {d.lower(): i for i, d in enumerate(self.movies["display"])}
        self.ratings = ratings.assign(item=ratings["movieId"].map(self._pos)).dropna(subset=["item"])
        self.ratings["item"] = self.ratings["item"].astype(int)
        self.cf = ItemCF(self.ratings, len(self.movies))
        self.content = ContentModel(self.movies)
        self.popularity = PopularityModel(self.movies)
        self._user_hist = {u: dict(zip(g["item"], g["rating"])) for u, g in self.ratings.groupby("userId")}

    # --------------------------------------------------------------- lookup
    @property
    def titles(self) -> list[str]:
        return self.movies.sort_values("n_ratings", ascending=False)["display"].tolist()

    @property
    def all_genres(self) -> list[str]:
        return sorted({g for gs in self.movies["genres"] for g in gs.split("|") if g})

    @property
    def user_ids(self) -> list[int]:
        return sorted(self._user_hist)

    def resolve_title(self, query: str) -> str:
        """Exact -> substring (most-rated first) -> fuzzy match."""
        key = query.strip().lower()
        if not key:
            raise MovieNotFoundError("Please type a movie title.")
        if key in self._lower:
            return self.movies.at[self._lower[key], "display"]
        hits = self.movies[self.movies["display"].str.lower().str.contains(key, regex=False)]
        if len(hits):
            return hits.sort_values("n_ratings", ascending=False).iloc[0]["display"]
        close = difflib.get_close_matches(key, list(self._lower), n=1, cutoff=0.6)
        if close:
            return self.movies.at[self._lower[close[0]], "display"]
        raise MovieNotFoundError(f"No movie found matching '{query}'.")

    def search(self, query: str, limit: int = 10) -> list[str]:
        key = query.strip().lower()
        hits = self.movies[self.movies["display"].str.lower().str.contains(key, regex=False)]
        return hits.sort_values("n_ratings", ascending=False)["display"].head(limit).tolist()

    def _idx(self, title: str) -> int:
        return self._lower[self.resolve_title(title).lower()]

    def details(self, title: str) -> dict:
        r = self.movies.iloc[self._idx(title)]
        return {"title": r["display"], "genres": r["genres"].replace("|", ", ") or "n/a",
                "n_ratings": int(r["n_ratings"]), "avg_rating": float(r["avg_rating"])}

    # -------------------------------------------------------------- scoring
    def _score(self, profile: dict[int, float]) -> np.ndarray:
        w_cf, w_ct, w_pop = self.weights
        return (w_cf * minmax(self.cf.score(profile)) + w_ct * minmax(self.content.score(profile))
                + w_pop * minmax(self.popularity.score(profile)))

    def _rank(self, scores: np.ndarray, exclude: set[int], n: int, genre: str | None,
              min_ratings: int, min_year: int = 0) -> pd.DataFrame:
        df = self.movies.assign(score=scores)
        mask = ~df.index.isin(exclude) & (df["n_ratings"] >= min_ratings) & (df["year"] >= min_year)
        if genre:
            mask &= df["genres"].str.split("|").apply(lambda g: genre in g)
        out = df[mask].sort_values("score", ascending=False).head(n)
        out = out[["display", "genres", "n_ratings", "avg_rating", "score"]].rename(columns={"display": "title"})
        out["genres"] = out["genres"].str.replace("|", ", ", regex=False)
        out["score"] = out["score"].round(3)
        return out.reset_index(drop=True)

    # ------------------------------------------------------------ public API
    def recommend(self, title: str, n: int = 10, genre: str | None = None,
                  min_ratings: int = 20, min_year: int = 0) -> pd.DataFrame:
        """Movies similar to one movie (item-item CF + genre similarity)."""
        if n < 1:
            raise ValueError("n must be at least 1")
        i = self._idx(title)
        w_cf, w_ct, w_pop = self.weights
        scores = (w_cf * minmax(self.cf.similar_to(i)) + w_ct * minmax(self.content.similar_to(i))
                  + w_pop * minmax(self.popularity.scores))
        out = self._rank(scores, {i}, n, genre, min_ratings, min_year)
        out["why"] = out["title"].apply(lambda t: self.why(self.movies.at[i, "display"], t))
        return out

    def recommend_for_ratings(self, ratings: dict[str, float], n: int = 10, genre: str | None = None,
                              min_ratings: int = 20, min_year: int = 0) -> pd.DataFrame:
        """Personalised recommendations from {title: your rating (0.5-5)}."""
        if not ratings:
            raise ValueError("Rate at least one movie.")
        profile = {self._idx(t): float(r) for t, r in ratings.items()}
        return self._rank(self._score(profile), set(profile), n, genre, min_ratings, min_year)

    def recommend_for_user(self, user_id: int, n: int = 10, genre: str | None = None,
                           min_ratings: int = 20) -> pd.DataFrame:
        """Recommendations for an existing MovieLens user, excluding what they already rated."""
        if user_id not in self._user_hist:
            raise ValueError(f"Unknown user id {user_id}")
        profile = self._user_hist[user_id]
        return self._rank(self._score(profile), set(profile), n, genre, min_ratings)

    def user_history(self, user_id: int, n: int = 10) -> pd.DataFrame:
        hist = self._user_hist[user_id]
        top = sorted(hist.items(), key=lambda kv: -kv[1])[:n]
        return pd.DataFrame({"title": [self.movies.at[i, "display"] for i, _ in top],
                             "your_rating": [r for _, r in top]})

    def top_rated(self, n: int = 10, genre: str | None = None, min_ratings: int = 50) -> pd.DataFrame:
        return self._rank(self.movies["wr"].values, set(), n, genre, min_ratings)

    def why(self, source: str, target: str) -> str:
        a = self.movies.iloc[self._lower[source.lower()]]
        b = self.movies.iloc[self._lower[target.lower()]]
        shared = [g for g in a["genres"].split("|") if g and g in b["genres"].split("|")]
        parts = ["fans of the first also rated it highly"]
        if shared:
            parts.insert(0, "shared genres: " + ", ".join(shared))
        return "; ".join(parts)
