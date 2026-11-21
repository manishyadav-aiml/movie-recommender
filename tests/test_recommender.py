"""Tests run on a small synthetic MovieLens-style dataset, so they are fast and need no downloads."""
import pandas as pd
import pytest

from src import MovieNotFoundError, MovieRecommender
from src.data import clean_title, train_test_split_by_user
from tests.helpers import make_engine


@pytest.fixture(scope="module")
def rec():
    return make_engine()


def test_clean_title_moves_article_and_year():
    assert clean_title("Matrix, The (1999)") == ("The Matrix", 1999)
    assert clean_title("Toy Story (1995)") == ("Toy Story", 1995)


def test_similar_movies_share_taste_group(rec):
    out = rec.recommend("Alien (1990)", n=3, min_ratings=1)["title"].tolist()
    assert {t.split(" (")[0] for t in out} <= {"Blade Runner", "The Matrix", "Terminator", "Robocop"}


def test_never_recommends_itself(rec):
    assert "Alien (1990)" not in rec.recommend("Alien", n=9, min_ratings=1)["title"].values


def test_profile_recommendations_follow_taste(rec):
    out = rec.recommend_for_ratings({"Toy Story": 5, "Up": 5}, n=3, min_ratings=1)["title"].tolist()
    assert all(t.split(" (")[0] in {"Finding Nemo", "Coco", "Shrek"} for t in out)


def test_user_recommendations_exclude_seen(rec):
    seen = {rec.movies.at[i, "display"] for i in rec._user_hist[1]}
    assert not seen & set(rec.recommend_for_user(1, n=5, min_ratings=1)["title"])


def test_fuzzy_and_substring_matching(rec):
    assert rec.resolve_title("toy story") == "Toy Story (1990)"
    assert rec.resolve_title("Finding Nemoo") == "Finding Nemo (1990)"


def test_unknown_title_raises(rec):
    with pytest.raises(MovieNotFoundError):
        rec.recommend("zzzzzz qqqq")


def test_invalid_inputs(rec):
    with pytest.raises(ValueError):
        rec.recommend("Alien", n=0)
    with pytest.raises(ValueError):
        rec.recommend_for_ratings({})
    with pytest.raises(ValueError):
        rec.recommend_for_user(99999)
    with pytest.raises(ValueError):
        MovieRecommender("test", weights=(0.5, 0.5, 0.5), movies=rec.movies, ratings=rec.ratings)


def test_genre_filter(rec):
    out = rec.top_rated(5, genre="Animation", min_ratings=1)
    assert out["genres"].str.contains("Animation").all()


def test_split_has_no_overlap_and_all_rows():
    df = pd.DataFrame({"userId": [1] * 50, "movieId": range(50), "rating": 4.0})
    tr, te = train_test_split_by_user(df, 0.2, 1)
    assert len(tr) + len(te) == 50 and not set(tr["movieId"]) & set(te["movieId"])
