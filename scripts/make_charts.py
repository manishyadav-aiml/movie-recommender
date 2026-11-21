"""Generate README charts into docs/.   Usage: python -m scripts.make_charts"""
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src import MovieRecommender

OUT = Path("docs"); OUT.mkdir(exist_ok=True)
rec = MovieRecommender("ml-1m")
movies, ratings = rec.movies, rec.ratings

counts = Counter(g for gs in movies["genres"] for g in gs.split("|") if g)
labels, values = zip(*sorted(counts.items(), key=lambda kv: kv[1]))
plt.figure(figsize=(7, 6)); plt.barh(labels, values, color="#4C72B0")
plt.title("Movies per genre (ml-1m)"); plt.tight_layout(); plt.savefig(OUT / "genre_counts.png", dpi=130); plt.close()

plt.figure(figsize=(7, 4)); ratings["rating"].value_counts().sort_index().plot.bar(color="#55A868")
plt.title("Rating distribution (ml-1m)"); plt.xlabel("stars"); plt.ylabel("ratings"); plt.tight_layout()
plt.savefig(OUT / "rating_distribution.png", dpi=130); plt.close()

per_movie = movies["n_ratings"].sort_values(ascending=False).values
plt.figure(figsize=(7, 4)); plt.plot(per_movie, color="#C44E52"); plt.yscale("log")
plt.title("Long tail: ratings per movie (log scale)"); plt.xlabel("movie rank"); plt.ylabel("ratings")
plt.tight_layout(); plt.savefig(OUT / "long_tail.png", dpi=130); plt.close()

res = json.loads(Path("results/evaluation_ml-1m.json").read_text())["results"]
names = [r["model"] for r in res]; vals = [r["ndcg@10"] for r in res]
plt.figure(figsize=(8, 4)); plt.bar(names, vals, color="#8172B2")
plt.xticks(rotation=15, ha="right"); plt.ylabel("NDCG@10"); plt.title("Model comparison (held-out ratings)")
plt.tight_layout(); plt.savefig(OUT / "model_comparison.png", dpi=130); plt.close()
print("Charts saved to", OUT)
