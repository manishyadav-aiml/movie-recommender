"""Recommendation models on MovieLens data (NumPy + pandas only).

* ContentModel    - TF-IDF over genres + decade (works for movies with no ratings: cold start)
* ItemCF          - item-item cosine similarity on mean-centred ratings with shrinkage
* PopularityModel - weighted-rating baseline
All models score *every* movie for a user profile {movie_index: rating}.
No scikit-learn / SciPy is needed, which keeps the deployment small (e.g. Vercel's 250 MB limit).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def weighted_rating(avg: pd.Series, n: pd.Series, m: int = 50) -> pd.Series:
    """IMDB-style Bayesian average: pulls movies with few votes toward the global mean."""
    c = float((avg * n).sum() / max(n.sum(), 1))
    return (n / (n + m)) * avg + (m / (n + m)) * c


class PopularityModel:
    def __init__(self, movies: pd.DataFrame):
        self.scores = weighted_rating(movies["avg_rating"], movies["n_ratings"]).values.astype("float32")

    def score(self, profile: dict[int, float]) -> np.ndarray:
        return self.scores


class ContentModel:
    """Genre/decade TF-IDF similarity (movie index space).

    Same maths as scikit-learn's TfidfVectorizer defaults: smoothed idf = ln((1+n)/(1+df)) + 1,
    then L2 normalisation, so dot products are cosine similarities.
    """

    def __init__(self, movies: pd.DataFrame):
        docs = []
        for genres, year in zip(movies["genres"], movies["year"]):
            tokens = [g.replace("-", "").replace(" ", "").lower() for g in genres.split("|") if g]
            if year:
                tokens.append(f"decade{int(year) // 10 * 10}")
            docs.append(tokens)
        vocab: dict[str, int] = {}
        for tokens in docs:
            for t in tokens:
                vocab.setdefault(t, len(vocab))
        n = len(docs)
        tf = np.zeros((n, max(len(vocab), 1)), dtype="float32")
        for i, tokens in enumerate(docs):
            for t in tokens:
                tf[i, vocab[t]] += 1.0
        df = (tf > 0).sum(axis=0)
        idf = (np.log((1 + n) / (1 + df)) + 1).astype("float32")
        m = tf * idf
        norms = np.linalg.norm(m, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.matrix = (m / norms).astype("float32")

    def similar_to(self, idx: int) -> np.ndarray:
        return self.matrix @ self.matrix[idx]

    def score(self, profile: dict[int, float]) -> np.ndarray:
        if not profile:
            return np.zeros(self.matrix.shape[0], dtype="float32")
        idx = list(profile)
        w = np.array([profile[i] for i in idx], dtype="float32") - 3.0  # >3 stars attracts, <3 repels
        sims = self.matrix[idx] @ self.matrix.T  # (k, n)
        return (w[:, None] * sims).sum(axis=0) / max(np.abs(w).sum(), 1e-6)


class ItemCF:
    """Item-based collaborative filtering (users are processed in chunks to bound memory)."""

    def __init__(self, ratings: pd.DataFrame, n_items: int, shrinkage: float = 10.0,
                 min_ratings: int = 3, chunk_users: int = 2000):
        u, _ = pd.factorize(ratings["userId"])
        i = ratings["item"].to_numpy()
        r = ratings["rating"].to_numpy(dtype="float32")
        n_users = int(u.max()) + 1 if len(u) else 0
        user_mean = np.bincount(u, weights=r, minlength=n_users) / np.maximum(np.bincount(u, minlength=n_users), 1)
        centred = (r - user_mean[u]).astype("float32")
        order = np.argsort(u, kind="stable")
        u, i, centred = u[order], i[order], centred[order]

        dot = np.zeros((n_items, n_items), dtype="float32")
        co = np.zeros((n_items, n_items), dtype="float32")
        for start in range(0, n_users, chunk_users):
            lo, hi = np.searchsorted(u, [start, start + chunk_users])
            rows = u[lo:hi] - start
            size = min(chunk_users, n_users - start)
            c = np.zeros((size, n_items), dtype="float32")
            c[rows, i[lo:hi]] = centred[lo:hi]
            b = np.zeros((size, n_items), dtype="float32")
            b[rows, i[lo:hi]] = 1.0
            dot += c.T @ c
            co += b.T @ b

        counts = np.diag(co).copy()
        norms = np.sqrt(np.maximum(np.diag(dot), 1e-9))
        dot /= np.outer(norms, norms)
        dot *= co / (co + shrinkage)  # trust pairs with many shared raters more
        np.fill_diagonal(dot, 0.0)
        rare = counts < min_ratings
        dot[rare, :] = 0.0
        dot[:, rare] = 0.0
        self.sim = dot
        self.counts = counts

    def similar_to(self, idx: int) -> np.ndarray:
        return self.sim[idx]

    def score(self, profile: dict[int, float]) -> np.ndarray:
        if not profile:
            return np.zeros(self.sim.shape[0], dtype="float32")
        idx = np.array(list(profile))
        r = np.array([profile[i] for i in idx], dtype="float32")
        w = r - r.mean() if len(r) > 1 else r - 3.0
        return (self.sim[idx].T @ w) / max(np.abs(w).sum(), 1e-6)


def minmax(x: np.ndarray) -> np.ndarray:
    lo, hi = float(x.min()), float(x.max())
    return (x - lo) / (hi - lo) if hi > lo else np.zeros_like(x)
