"""Run offline evaluation and save results/evaluation_<dataset>.{json,md}.
Usage: python -m scripts.evaluate --dataset ml-1m
"""
import argparse

from src.evaluation import evaluate, save_results

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="ml-1m")
    ap.add_argument("--users", type=int, default=500)
    a = ap.parse_args()
    df = evaluate(a.dataset, n_users=a.users)
    print(df.to_string(index=False))
    print("Saved", save_results(df))
