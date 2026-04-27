# Retrieval ablation


## public test set (10 queries)

| Variant | Description | Hit@3 | MRR@5 | Avg latency |
|---|---|---:|---:|---:|
| `dense_only` | bge-m3 dense + FAISS only | 100.00% | 1.0000 | 0.028s |
| `bm25_only` | BM25 sparse only | 100.00% | 1.0000 | 0.001s |
| `hybrid_rrf` | BM25 + dense + RRF (no rerank) | 100.00% | 1.0000 | 0.002s |
| `hybrid_rerank` | BM25 + dense + RRF + cross-encoder rerank | 100.00% | 0.9333 | 0.457s |
| `full` | Hybrid + ColBERT + rerank + category boost (production) | 100.00% | 0.9333 | 0.567s |
| `full_phrase_cite` | Production + phrase boost + citation prior (ablation) | 100.00% | 0.8667 | 0.427s |

## bootstrap test set (18 queries)

| Variant | Description | Hit@3 | MRR@5 | Avg latency |
|---|---|---:|---:|---:|
| `dense_only` | bge-m3 dense + FAISS only | 88.89% | 0.8241 | 0.030s |
| `bm25_only` | BM25 sparse only | 72.22% | 0.6296 | 0.002s |
| `hybrid_rrf` | BM25 + dense + RRF (no rerank) | 83.33% | 0.8556 | 0.002s |
| `hybrid_rerank` | BM25 + dense + RRF + cross-encoder rerank | 88.89% | 0.9028 | 0.562s |
| `full` | Hybrid + ColBERT + rerank + category boost (production) | 88.89% | 0.9028 | 0.548s |
| `full_phrase_cite` | Production + phrase boost + citation prior (ablation) | 83.33% | 0.6574 | 0.451s |