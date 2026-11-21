"""Sanity checks on the bundled real MovieLens data (skipped if not present)."""
import pytest

from src.data import available_datasets
from src import MovieRecommender

pytestmark = pytest.mark.skipif("ml-small" not in available_datasets(), reason="ml-small not prepared")


@pytest.fixture(scope="module")
def rec():
    return MovieRecommender("ml-small")


def test_toy_story_neighbours_are_family_movies(rec):
    genres = " ".join(rec.recommend("Toy Story", n=5)["genres"])
    assert "Animation" in genres or "Children" in genres


def test_top_rated_sorted(rec):
    scores = rec.top_rated(10)["score"].tolist()
    assert scores == sorted(scores, reverse=True)
