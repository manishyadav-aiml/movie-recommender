# Evaluation on ml-small (k=10, 300 test users)

| model | precision@10 | recall@10 | hit_rate@10 | ndcg@10 | coverage |
|---|---|---|---|---|---|
| Popularity baseline | 0.1263 | 0.1008 | 0.6433 | 0.1591 | 0.0126 |
| Content only (genres) | 0.042 | 0.0406 | 0.3 | 0.0521 | 0.2238 |
| Collaborative only | 0.1623 | 0.1228 | 0.6733 | 0.2055 | 0.1337 |
| Hybrid (default) | 0.1623 | 0.1347 | 0.7133 | 0.2152 | 0.149 |

Hold-out: 20% of each user's ratings; relevant = held-out rating >= 4.
