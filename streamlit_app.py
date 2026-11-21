"""Streamlit app for the Movie Recommendation System (MovieLens data).

Run with:  streamlit run streamlit_app.py
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src import MovieRecommender
from src.data import available_datasets
from src.recommender import default_dataset

st.set_page_config(page_title="Movie Recommender", page_icon="🎬", layout="wide")


@st.cache_resource(show_spinner="Loading data and training models...")
def get_engine(dataset: str) -> MovieRecommender:
    return MovieRecommender(dataset)


def show_results(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No movies match these filters. Try relaxing them.")
        return
    for _, row in df.iterrows():
        left, right = st.columns([5, 2])
        with left:
            st.markdown(f"**{row['title']}**")
            st.caption(f"{row['genres']}")
            if "why" in row:
                st.write(f"*Because:* {row['why']}")
        with right:
            st.markdown(f"⭐ {row['avg_rating']:.2f}  ·  {row['n_ratings']:,} ratings")
            st.progress(min(max(float(row["score"]), 0.0), 1.0), text=f"match {row['score']:.2f}")
        st.divider()


datasets = available_datasets()
if not datasets:
    st.error("No processed dataset found. Run `python -m scripts.prepare_data` (see README).")
    st.stop()

with st.sidebar:
    st.header("Settings")
    dataset = st.selectbox("Dataset", datasets, index=datasets.index(default_dataset())
                           if default_dataset() in datasets else 0)
    rec = get_engine(dataset)
    n = st.slider("Number of recommendations", 3, 20, 10)
    genre = st.selectbox("Genre filter", ["Any"] + rec.all_genres)
    min_ratings = st.slider("Minimum number of ratings", 1, 500, 20,
                            help="Hide movies that very few people have rated.")
    st.caption(f"{len(rec.movies):,} movies · {len(rec.ratings):,} ratings · {rec.ratings['userId'].nunique():,} users")
genre_filter = None if genre == "Any" else genre

st.title("🎬 Movie Recommendation System")
st.caption("Hybrid recommender: item-based collaborative filtering + genre similarity + popularity, "
           "trained on MovieLens ratings.")

tab_similar, tab_profile, tab_user, tab_top, tab_eval = st.tabs(
    ["Similar movies", "My taste profile", "Existing user", "Top rated", "Evaluation"])

with tab_similar:
    choice = st.selectbox("Pick a movie you like", rec.titles, key="similar_choice")
    if st.button("Recommend", type="primary", key="go_similar"):
        info = rec.details(choice)
        st.subheader(info["title"])
        st.caption(f"{info['genres']} · avg rating {info['avg_rating']:.2f} from {info['n_ratings']:,} users")
        show_results(rec.recommend(choice, n, genre_filter, min_ratings))

with tab_profile:
    st.write("Choose a few movies and rate them. The more you add, the better the recommendations.")
    picks = st.multiselect("Movies you have seen", rec.titles, key="profile_picks")
    ratings = {t: st.slider(t, 0.5, 5.0, 4.0, 0.5, key=f"rate_{t}") for t in picks}
    if st.button("Get my recommendations", type="primary", key="go_profile"):
        if not ratings:
            st.warning("Pick at least one movie first.")
        else:
            show_results(rec.recommend_for_ratings(ratings, n, genre_filter, min_ratings))

with tab_user:
    uid = st.selectbox("MovieLens user id", rec.user_ids, key="uid")
    if st.button("Show recommendations for this user", type="primary", key="go_user"):
        st.markdown("**Their top-rated movies**")
        st.dataframe(rec.user_history(uid, 8), hide_index=True, use_container_width=True)
        st.markdown("**Recommended for them**")
        show_results(rec.recommend_for_user(uid, n, genre_filter, min_ratings))

with tab_top:
    st.caption("Ranked with a Bayesian weighted rating, so movies with few votes do not dominate.")
    show_results(rec.top_rated(n, genre_filter, max(min_ratings, 50)))

with tab_eval:
    file = Path("results") / f"evaluation_{dataset}.json"
    st.subheader("Dataset insights")
    c1, c2 = st.columns(2)
    genre_counts = pd.Series([g for gs in rec.movies["genres"] for g in gs.split("|") if g]).value_counts()
    c1.markdown("**Movies per genre**"); c1.bar_chart(genre_counts)
    c2.markdown("**Ratings given (1–5 stars)**")
    c2.bar_chart(rec.ratings["rating"].round().astype(int).value_counts().sort_index())
    st.subheader("Model comparison")
    if file.exists():
        data = json.loads(file.read_text())
        st.dataframe(pd.DataFrame(data["results"]), hide_index=True, use_container_width=True)
        info = data["info"]
        st.caption(f"Held out 20% of every user's ratings; {info['users']} test users; relevant = held-out "
                   f"rating ≥ 4. Reproduce: `python -m scripts.evaluate --dataset {dataset}`")
    else:
        st.info(f"Run `python -m scripts.evaluate --dataset {dataset}` to generate results.")
