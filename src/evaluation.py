"""Offline evaluation on real held-out ratings.

Protocol: hold out 20% of every user's ratings. Models only see the training
ratings. For each sampled test user we recommend 10 unseen movies and check how
many of the user's held-out *liked* movies (rating >= 4) appear in the list.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .data import load_processed, train_test_split_by_user
from .recommender import MovieRecommender

MODEL_WEIGHTS = {
    "Popularity baseline": (0.0, 0.0, 1.0),
    "Content only (genres)": (0.0, 1.0, 0.0),
    "Collaborative only": (1.0, 0.0, 0.0),
    "Hybrid (default)": (0.7, 0.25, 0.05),
}


def _metrics_for(top: np.ndarray, relevant: set[int], k: int) -> tuple[float, float, float, float]:
    hits = [1.0 if i in relevant else 0.0 for i in top]
    n_hit = sum(hits)
    dcg = sum(h / np.log2(rank + 2) for rank, h in enumerate(hits))
    idcg = sum(1.0 / np.log2(r + 2) for r in range(min(len(relevant), k)))
    return n_hit / k, n_hit / len(relevant), float(n_hit > 0), dcg / idcg if idcg else 0.0


def evaluate(dataset: str = "ml-1m", weight_sets: dict[str, tuple] | None = None, k: int = 10,
             n_users: int = 500, seed: int = 42, min_test_positives: int = 3) -> pd.DataFrame:
    movies, ratings = load_processed(dataset)
    train, test = train_test_split_by_user(ratings, 0.2, seed)
    rec = MovieRecommender(dataset, movies=movies, ratings=train)
    pos = test[test["movieId"].isin(rec._pos) & (test["rating"] >= 4)]
    pos = pos.assign(item=pos["movieId"].map(rec._pos))
    liked = {u: set(g["item"]) for u, g in pos.groupby("userId") if len(g) >= min_test_positives}
    users = [u for u in liked if u in rec._user_hist]
    rng = np.random.default_rng(seed)
    users = list(rng.choice(users, size=min(n_users, len(users)), replace=False))

    rows = {}
    for name, w in (weight_sets or MODEL_WEIGHTS).items():
        rec.weights = w
        prec, recall, hit, ndcg, seen = [], [], [], [], set()
        for u in users:
            hist = rec._user_hist[u]
            scores = rec._score(hist).copy()
            scores[list(hist)] = -np.inf
            scores[(rec.movies["n_ratings"] < 20).values] = -np.inf
            top = np.argpartition(-scores, k)[:k]
            top = top[np.argsort(-scores[top])]
            p, r, h, n = _metrics_for(top, liked[u], k)
            prec.append(p); recall.append(r); hit.append(h); ndcg.append(n); seen.update(top.tolist())
        rows[name] = {f"precision@{k}": np.mean(prec), f"recall@{k}": np.mean(recall),
                      f"hit_rate@{k}": np.mean(hit), f"ndcg@{k}": np.mean(ndcg),
                      "coverage": len(seen) / len(rec.movies)}
    out = pd.DataFrame(rows).T.round(4).rename_axis("model").reset_index()
    out.attrs["info"] = {"dataset": dataset, "users": len(users), "k": k, "seed": seed,
                         "train_ratings": len(train), "test_ratings": len(test)}
    return out


def save_results(df: pd.DataFrame, folder: str | Path = "results") -> Path:
    folder = Path(folder)
    folder.mkdir(exist_ok=True)
    info = df.attrs["info"]
    path = folder / f"evaluation_{info['dataset']}.json"
    path.write_text(json.dumps({"info": info, "results": df.to_dict(orient="records")}, indent=2))
    cols = list(df.columns)
    lines = [f"# Evaluation on {info['dataset']} (k={info['k']}, {info['users']} test users)", "",
             "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    lines += ["", "Hold-out: 20% of each user's ratings; relevant = held-out rating >= 4."]
    path.with_suffix(".md").write_text("\n".join(lines) + "\n")
    return path
