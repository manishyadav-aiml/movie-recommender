"""Loading and preparing MovieLens data.

Supported raw formats
---------------------
* CSV  : movies.csv + ratings.csv   (ml-latest-small, ml-25m, ml-latest ...)
* DAT  : movies.dat + ratings.dat   (ml-1m, "::" separated)

`prepare_dataset` converts either into a compact, uniform "processed" folder:
    data/processed/<name>/movies.csv       movieId,title,year,genres,n_ratings,avg_rating
    data/processed/<name>/ratings.csv.gz   userId,movieId,rating
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
_YEAR = re.compile(r"\s*\((\d{4})\)\s*$")
_ARTICLE = re.compile(r"^(?P<name>.*), (?P<art>The|A|An|Les|La|Le|Il|Das|Der|Die|El|L')$")


def clean_title(raw: str) -> tuple[str, int | None]:
    """'Matrix, The (1999)' -> ('The Matrix', 1999). Alternative titles in brackets are dropped."""
    raw = raw.strip()
    year = None
    m = _YEAR.search(raw)
    if m:
        year = int(m.group(1))
        raw = raw[: m.start()]
    raw = re.sub(r"\s*\([^)]*\)\s*$", "", raw).strip()  # alt title, e.g. "(Cite des ...)"
    m = _ARTICLE.match(raw)
    if m:
        art = m.group("art")
        raw = f"{art}{'' if art.endswith(chr(39)) else ' '}{m.group('name')}"
    return raw, year


def _normalise_movies(df: pd.DataFrame) -> pd.DataFrame:
    parsed = df["title"].apply(clean_title)
    out = df.copy()
    out["title"] = [p[0] for p in parsed]
    out["year"] = [p[1] if p[1] else 0 for p in parsed]
    out["genres"] = out["genres"].replace("(no genres listed)", "").fillna("")
    out["genres"] = out["genres"].str.replace("Children's", "Children", regex=False)
    return out[["movieId", "title", "year", "genres"]]


def read_raw(raw_dir: str | Path, max_users: int | None = None,
             chunksize: int = 2_000_000) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read raw MovieLens files (csv or dat). Large csv files are read in chunks."""
    raw = Path(raw_dir)
    dat = next(raw.rglob("movies.dat"), None)
    if dat is not None:
        movies = pd.read_csv(dat, sep="::", engine="python", names=["movieId", "title", "genres"],
                             encoding="latin-1")
        ratings = pd.read_csv(dat.with_name("ratings.dat"), sep="::", engine="python",
                              names=["userId", "movieId", "rating", "ts"], usecols=[0, 1, 2])
        if max_users:
            ratings = ratings[ratings["userId"] <= max_users]
    else:
        movies_f = next(raw.rglob("movies.csv"), None)
        ratings_f = next(raw.rglob("ratings.csv"), None)
        if movies_f is None or ratings_f is None:
            raise FileNotFoundError(f"No MovieLens movies/ratings files found under {raw}")
        movies = pd.read_csv(movies_f)
        parts = []
        for chunk in pd.read_csv(ratings_f, usecols=["userId", "movieId", "rating"], chunksize=chunksize,
                                 dtype={"userId": "int32", "movieId": "int32", "rating": "float32"}):
            if max_users:
                chunk = chunk[chunk["userId"] <= max_users]
            parts.append(chunk)
        ratings = pd.concat(parts, ignore_index=True)
    return movies, ratings


def prepare_dataset(raw_dir: str | Path, name: str, max_movies: int | None = None,
                    max_users: int | None = None, min_movie_ratings: int = 5,
                    out_root: Path = PROCESSED_DIR) -> Path:
    """Clean raw files and write the processed dataset. Returns the output folder."""
    movies, ratings = read_raw(raw_dir, max_users)
    ratings = ratings.drop_duplicates(["userId", "movieId"])
    counts = ratings.groupby("movieId")["rating"].agg(n_ratings="size", avg_rating="mean")
    keep = counts[counts["n_ratings"] >= min_movie_ratings]
    if max_movies:
        keep = keep.sort_values("n_ratings", ascending=False).head(max_movies)
    ratings = ratings[ratings["movieId"].isin(keep.index)]
    movies = _normalise_movies(movies).merge(keep.reset_index(), on="movieId")
    movies["avg_rating"] = movies["avg_rating"].round(3)
    movies = movies.sort_values("movieId").reset_index(drop=True)

    out = out_root / name
    out.mkdir(parents=True, exist_ok=True)
    movies.to_csv(out / "movies.csv", index=False)
    ratings.astype({"userId": "int32", "movieId": "int32"}).to_csv(
        out / "ratings.csv.gz", index=False, compression="gzip")
    return out


def available_datasets(root: Path = PROCESSED_DIR) -> list[str]:
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if (p / "movies.csv").exists())


def load_processed(name: str, root: Path = PROCESSED_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    folder = root / name
    if not (folder / "movies.csv").exists():
        raise FileNotFoundError(f"Dataset '{name}' not found in {root}. Run scripts/prepare_data.py first.")
    movies = pd.read_csv(folder / "movies.csv").fillna({"genres": ""})
    ratings = pd.read_csv(folder / "ratings.csv.gz",
                          dtype={"userId": "int32", "movieId": "int32", "rating": "float32"})
    return movies, ratings


def train_test_split_by_user(ratings: pd.DataFrame, test_frac: float = 0.2, seed: int = 42
                             ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Hold out a random fraction of every user's ratings (at least one)."""
    rng = np.random.default_rng(seed)
    mask = rng.random(len(ratings)) < test_frac
    test = ratings[mask]
    train = ratings[~mask]
    return train.reset_index(drop=True), test.reset_index(drop=True)
