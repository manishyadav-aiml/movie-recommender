"""Command line interface for the Movie Recommendation System.

Examples:
    python cli.py "The Matrix" -n 5
    python cli.py "Toy Story" --genre Comedy
    python cli.py --rate "The Godfather=5" "Pulp Fiction=4.5" --genre Crime
    python cli.py --user 42
    python cli.py --top 10 --genre Sci-Fi
    python cli.py "Inception" --dataset ml-25m-top
"""
import argparse

from src import MovieNotFoundError, MovieRecommender


def main() -> None:
    p = argparse.ArgumentParser(description="Movie Recommendation System")
    p.add_argument("title", nargs="?", help="Movie you liked")
    p.add_argument("-n", type=int, default=10, help="Number of results (default 10)")
    p.add_argument("--genre", help="Filter results by genre")
    p.add_argument("--dataset", help="Processed dataset name (ml-small, ml-1m, ml-25m-top)")
    p.add_argument("--rate", nargs="+", metavar="TITLE=RATING", help="Your ratings, e.g. 'Heat=4.5'")
    p.add_argument("--user", type=int, help="Recommend for an existing MovieLens user id")
    p.add_argument("--top", type=int, help="Show top-rated movies instead")
    args = p.parse_args()

    rec = MovieRecommender(args.dataset)
    try:
        if args.top:
            result = rec.top_rated(args.top, args.genre)
        elif args.rate:
            ratings = {}
            for item in args.rate:
                title, _, value = item.rpartition("=")
                ratings[title] = float(value)
            result = rec.recommend_for_ratings(ratings, args.n, args.genre)
        elif args.user:
            print(f"User {args.user} top-rated movies:\n{rec.user_history(args.user, 5).to_string(index=False)}\n")
            result = rec.recommend_for_user(args.user, args.n, args.genre)
        elif args.title:
            print(f"Because you liked: {rec.resolve_title(args.title)}\n")
            result = rec.recommend(args.title, args.n, args.genre)
        else:
            p.print_help()
            return
    except (MovieNotFoundError, ValueError) as err:
        print(f"Error: {err}")
        return
    print("No matching movies found." if result.empty else result.to_string(index=False))


if __name__ == "__main__":
    main()
