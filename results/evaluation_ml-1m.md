# Evaluation on ml-1m (k=10, 600 test users)

| model | precision@10 | recall@10 | hit_rate@10 | ndcg@10 | coverage |
|---|---|---|---|---|---|
| Popularity baseline | 0.0792 | 0.0429 | 0.4417 | 0.0932 | 0.0117 |
| Content only (genres) | 0.037 | 0.0271 | 0.25 | 0.0431 | 0.5009 |
| Collaborative only | 0.183 | 0.1062 | 0.6883 | 0.221 | 0.1212 |
| Hybrid (default) | 0.2093 | 0.1351 | 0.76 | 0.2561 | 0.1519 |

Hold-out: 20% of each user's ratings; relevant = held-out rating >= 4.
