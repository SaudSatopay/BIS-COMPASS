# BIS Compass — AI-Powered BIS Standard Recommender

**Sigma Squad × Bureau of Indian Standards Hackathon · April 2026**
**Theme:** Accelerating MSE Compliance — Automating BIS Standard Discovery

> Indian Micro and Small Enterprises spend **weeks** identifying which Bureau of Indian Standards (BIS) regulations apply to their products. **BIS Compass** does it in **under half a second** — describe your product in plain English and get the top 5 applicable standards with grounded rationale.

## TL;DR — Results on the public test set

| Metric            | Target | Achieved   |
| ----------------- | -----: | ---------: |
| **Hit Rate @3**   |  > 80% | **100.00%** |
| **MRR @5**        |  > 0.7 | **0.9333** |
| **Avg latency**   |  < 5 s | **0.45–0.85 s** ¹ |
| Standards indexed |      — | **559**    |

Scored locally with the organisers' [`eval_script.py`](eval_script.py).
¹ Measured on RTX 5060 Ti (Blackwell, 16 GB) with hot HF cache: 0.45 s. Independent verification on a different machine reported 0.85 s. Both well under the 5 s target.

> ⏱ **First run downloads ~5 GB of model weights** (`BAAI/bge-m3` + `BAAI/bge-reranker-v2-m3`) from HuggingFace — allow **3–5 minutes** on first invocation depending on your connection. All subsequent runs are fully offline (the [`offline guard`](src/offline_guard.py) auto-flips `HF_HUB_OFFLINE=1` once the cache is populated). Confirmed by the BIS Hackathon organisers as the expected pattern.

> 🖥 **Cross-hardware validated.** All three rulebook targets pass on both ends of the consumer-GPU range:
> | Hardware | rerank_k | Hit@3 | MRR@5 | Avg Latency |
> | --- | ---: | ---: | ---: | ---: |
> | **RTX 5060 Ti (16 GB)** — dev rig | 25 (full) | 100% | 0.9333 | **0.45 s** |
> | **RTX 2080 (8 GB)** — judges' rig (per organiser) | 25 (full) | 100%¹ | 0.9333¹ | **~0.7 s¹** |
> | **GTX 1650 (4 GB) / CPU-only torch** | 3 (auto-clamped) | 100% | 0.9500 | **3.71 s** |
>
> ¹ projected from RTX 5060 Ti results — same pipeline + same pool=25, RTX 2080 ≈ 1.5× slower than 5060 Ti on transformer inference. Still 7× under the 5 s rulebook target.
>
> The retriever auto-detects compute and clamps the cross-encoder rerank pool (`rerank_k`) on lower-end hardware so latency stays under target without changing behaviour on capable hardware. Override with `RERANK_K=N` or disable with `RERANK_K_NO_AUTO=1`. The auto-clamp ladder:
>
> | Detected hardware | `rerank_k` |
> | --- | ---: |
> | GPU ≥ 7.5 GB VRAM | 25 (full quality) |
> | GPU 5–7.5 GB VRAM | 18 |
> | GPU 3.5–5 GB VRAM | 10 |
> | GPU < 3.5 GB VRAM | 4 |
> | CPU only (no CUDA) | 3 |
>
> Hit@3 is unchanged across all tiers (the gold standard is consistently in the top-3 of the fused list). MRR@5 swings ≤ 0.05 points across tiers.

---

## 1 · Architecture at a glance

![Architecture](docs/architecture.png)

**Pipeline stages** (left to right):

1. **Ingest** — `pdf_parser.py` extracts 559 standards from the 929-page SP 21 PDF; emits both `parsed_standards.json` and an `is_code_whitelist.json` used for anti-hallucination.
2. **Index** — `bge-m3` produces 1024-d dense vectors stored in FAISS; `rank_bm25` produces the sparse index over title + scope + body.
3. **Retrieve** — at query time, both indices return their top-25 candidates. **Reciprocal Rank Fusion** (parameter-free, `1 / (60 + rank)`) merges the two ranked lists, then `bge-reranker-v2-m3` cross-encoder re-scores the top candidates with explicit query↔passage attention.
4. **Guard** — every IS code that survives is checked against the whitelist before being emitted, so the system literally cannot return an imaginary BIS standard.
5. **Serve** — `inference.py` writes top-5 to JSON for judges; the FastAPI demo UI optionally calls Gemini 2.0 Flash for a grounded one-line rationale per hit (UI-only, never in the eval path).

### Why this design wins

| Decision                                   | Reason                                                                                                                      |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| **bge-m3** for dense embeddings            | SOTA on multilingual + technical retrieval, 1024-d, runs at fp16 on consumer GPU                                            |
| **bge-reranker-v2-m3** cross-encoder       | Sub-200ms on 25 candidates; corrects dense recall errors with explicit query↔passage attention                              |
| **Hybrid (BM25 + dense + RRF)**            | BM25 captures rare technical tokens (`M30`, `OPC33`, `mortice`); dense captures semantics. Fused with parameter-free RRF.   |
| **IS-code whitelist** (extracted from corpus) | Hard guarantee that no recommendation is hallucinated — every returned code exists in SP 21.                              |
| **FAISS over Qdrant**                      | 559 docs is small; FAISS is one `pip install`, zero Docker, fully reproducible on judges' machines.                         |
| **Gemini for UI only, never for retrieval**| Eval pipeline is 100% local — no API key required for `inference.py`. Gemini only powers the demo's rewrite and rationales. |

---

## 2 · Reproducing our results

### 2.0 One-command setup + demo boot — recommended for judges

A single command sets up the environment, scores the public eval, AND boots the demo UI in your browser. Pick the entry point for your OS:

```cmd
setup.bat              :: Windows (double-click or run in cmd)
```
```bash
bash setup.sh          # macOS / Linux
```

The Windows / Unix wrappers call `setup.py` then `start.py` in sequence. To run them separately (e.g., setup-only on a CI box, or boot the demo without re-running setup), invoke the Python scripts directly:

```bash
python setup.py        # one-shot env setup + indices + eval, then exits
python start.py        # boot backend on :8000 + frontend on :3000
```

`setup.py` is **idempotent** — it skips PDF parsing and index builds if their output files already exist, so re-running takes ~10 s once the cache is warm.

⏱ **Expected first-run time on a fresh machine** (validated on a real fresh-clone test):

| Setup | Total time | Notes |
| --- | --- | --- |
| With HF token (`setup.py` prompts for a free one in 30 s) | **~5 min** | Recommended |
| Anonymous HF download (rate-limited)                       | **~9–15 min** | Measured: **535 s on a laptop link** |
| Subsequent runs (everything cached, fully offline)         | **~10 s**  | Idempotent — skips parse + index |

The dominant cost is the one-time HuggingFace download. We **pre-filter** the download to drop ONNX, OpenVINO, and redundant weight-format variants the libraries never use — keeping `model.safetensors` for `bge-reranker-v2-m3` and `pytorch_model.bin` for `bge-m3` (the only weight file that repo ships). This cuts wire size from ~12 GB (full repos) to ~5 GB without changing model behaviour. The two models download in **parallel** (`ThreadPoolExecutor`) with **`max_workers=16`** per-file concurrency. A post-download verifier checks both repos have a usable weight file before claiming step 2 done.

What the script does, with progress and timing for every step:
1. Pre-flight checks (Python version, free disk)
2. `pip install -r requirements.txt`
3. Parse SP 21 PDF → `parsed_standards.json` + `is_code_whitelist.json`
4. Build FAISS dense index (downloads `bge-m3` on first run)
5. Build BM25 sparse index
6. Warm-up `inference.py` on the public test set (downloads `bge-reranker-v2-m3` on first run)
7. Score the warm-up with `eval_script.py`

If you'd rather run the steps individually, §2.2–§2.5 below walks through them.

### 2.1 Prerequisites

* **Python 3.10–3.12** (validated). 3.13 may work; 3.14+ has incomplete ML-wheel coverage (numpy 2.2.6 / torch 2.11.0 don't yet ship Python 3.14 wheels — `setup.py` will warn).
* **Node.js ≥ 20.10** (Next.js 16 requires it). The frontend's `npm install` in `start.py` will pull what's needed.
* **NVIDIA GPU with driver ≥ 555** (optional but recommended). `setup.py` auto-detects via `nvidia-smi` and installs the `cu128` torch wheel — covers Turing / Ampere / Ada / Hopper / Blackwell (RTX 20-50xx). On a CPU-only box the CPU torch wheel installs instead and the auto-clamp ladder shrinks the rerank pool to keep per-query latency under target.

### 2.2 Install

```bash
# Clone & enter
git clone <this-repo> bis-compass
cd bis-compass

# Create + activate venv (recommended)
python -m venv venv
source venv/bin/activate          # Linux / macOS
# .\venv\Scripts\activate         # Windows PowerShell

pip install -r requirements.txt
```

> **Note on torch wheel selection.** When you run the unified `setup.py` (recommended in §2.0), it auto-detects an NVIDIA GPU via `nvidia-smi` and installs the right torch wheel:
> | Detected | torch wheel | Notes |
> | --- | --- | --- |
> | NVIDIA GPU (driver ≥ 555) | `cu128` (CUDA 12.8) | Covers Turing / Ampere / Ada / Hopper / Blackwell — RTX 20-50xx |
> | No GPU | CPU wheel | Smaller, faster install |
> | NVIDIA driver < 555 | set `TORCH_NO_CUDA=1` first | Forces CPU wheel; still passes targets |
>
> If you've installed torch yourself before running `setup.py`, the script detects it and leaves your install alone.

### 2.3 Build the indices (one-time, ~3 min including model download)

```bash
# 1. Parse the SP 21 PDF -> parsed_standards.json + is_code_whitelist.json
python -m src.ingestion.pdf_parser

# 2. Build the FAISS dense index (downloads bge-m3 on first run)
python -m src.retrieval.index

# 3. Build the BM25 sparse index
python -m src.retrieval.bm25_index
```

### 2.4 Run the judge entry point

The hackathon spec requires a single CLI entry point. We honour it:

```bash
python inference.py --input datasets/public_test_set.json --output team_results.json
```

Output schema (matches the organisers' `sample_output.json` exactly):

```json
[
  {
    "id": "PUB-01",
    "query": "We are a small enterprise manufacturing 33 Grade Ordinary Portland Cement...",
    "expected_standards": ["IS 269: 1989"],
    "retrieved_standards": ["IS 269: 1989", "IS 8043: 1991", "IS 12269: 1987", "IS 8112: 1989", "IS 12330: 1988"],
    "latency_seconds": 0.742
  }
]
```

### 2.5 Score the run

```bash
python eval_script.py --results team_results.json
```

Expected output:

```
========================================
   BIS HACKATHON EVALUATION RESULTS
========================================
Total Queries Evaluated : 10
Hit Rate @3             : 100.00%   (Target: >80%)
MRR @5                  : 0.9333    (Target: >0.7)
Avg Latency             : 0.47 sec  (Target: <5 seconds)
========================================
```

> **Note on first-run latency.** The reported `latency_seconds` does NOT include the one-time model load (~10 s for bge-m3 + bge-reranker on GPU). Per-query retrieval (the only thing the eval script measures) is well under 1 s.

### 2.6 Defensive engineering for judge reproducibility

The setup and runtime paths are hardened against common reproducibility failure modes — most of these were surfaced by adversarial cold-clone testing on multiple machines:

| Failure mode | Defence |
| --- | --- |
| Microsoft Store python.exe stub on PATH (Win 10/11 default) | `setup.bat` rejects `WindowsApps` paths and validates each candidate runs `sys.version_info >= (3, 10)` before using it |
| HF cache has model directories but partial weights | `offline_guard.py` walks the snapshot dir and only flips `HF_HUB_OFFLINE` when a usable `model.safetensors` or `pytorch_model.bin` is present |
| HF Xet downloader needs symlinks (Win without Developer Mode) | `setup.py` empirically probes whether the OS allows `os.symlink`; if not, persists `HF_HUB_DISABLE_XET=1` to `.env` so backend / inference subprocesses inherit it |
| `bge-m3` ships only `pytorch_model.bin` (no SafeTensors) — naive filters drop weights | Per-model ignore lists; post-download verifier confirms a usable weights file exists in each cache dir before claiming success |
| Cross-encoder reranker OOMs on 4 GB cards | Auto-clamp ladder picks `rerank_k` based on detected VRAM; defaults to a safe small pool on any introspection failure |
| Backend cold-start exceeds 3 minutes on weak GPUs | `start.py` watchdog set to 300 s with a heartbeat every 30 s |
| Ctrl+C leaves Next.js node grandchild bound to :3000 | `start.py` cleanup uses `taskkill /F /T /PID` to recursively kill the process tree on Windows |
| `LLMClient` import order can leave protobuf in a broken state and segfault transformers | `src/api/main.py` imports `Retriever` (torch + transformers) **before** `LLMClient` (google.genai + grpc) |
| Wide CORS / `0.0.0.0` bind + per-request API keys in `/search` body | Backend bound to `127.0.0.1`; CORS origins restricted to `http://localhost:3000`; `/search` validates `query` length and `top_k` range; `/standards/{is_code}` validates against an IS-code regex before lookup |
| Cold `health()` fails → spurious "no LLM providers" modal | Frontend retries `/health` 3× with backoff before declaring the backend offline |
| Pasted API keys carry quotes / zero-width chars | Welcome modal sanitises pasted keys (strip quotes / ZWSP / whitespace) and validates against `/^[A-Za-z0-9_-]{20,}$/` with inline error |
| `/search` fetch hangs forever on cold backend | 60 s `AbortSignal.timeout` so judges see a clear failure rather than a spinning UI |

### 2.7 Running on the judges' private test set

The rulebook §3.3 specifies the judges run:

```bash
python inference.py --input hidden_private_dataset.json --output team_results.json
```

This is identical in shape to §2.4 — only the `--input` filename differs. The private file contains a JSON array of `{ "id": "...", "query": "..." }` objects (same schema as `datasets/public_test_set.json`). The query field is passed through the **same hybrid retrieval pipeline against the SP 21 indices** built by `setup.py` — confirmed by the BIS Hackathon organisers in chat: *"private dataset consists of new queries, same knowledge base."*

After the run, `team_results.json` will contain one record per input item:

```json
{ "id": "...", "retrieved_standards": [...top-5...], "latency_seconds": 0.46 }
```

Then the organisers' `eval_script.py` is run against `team_results.json` to compute Hit@3 / MRR@5 / Avg Latency. No additional steps required.

### 2.8 Modifying the input corpus

If you want to point this pipeline at a **different source PDF** (for example, swapping SP 21 for another BIS standards summary), three steps after `setup.py` has already run once:

```bash
# 1. Replace the source PDF
cp <your_corpus>.pdf datasets/dataset.pdf

# 2. Re-parse and rebuild the artifacts the rest of the pipeline reads
PARSER_FORCE=1 python -m src.ingestion.pdf_parser
python -c "from src.retrieval.index import build_index; from pathlib import Path; build_index(Path('data/parsed_standards.json'), Path('data/index'), force=True)"
python -c "from src.retrieval.bm25_index import build_index; from pathlib import Path; build_index(Path('data/parsed_standards.json'), Path('data/index'), force=True)"

# 3. Re-run inference on whatever queries you want against the new corpus
python inference.py --input <your_queries.json> --output <your_results.json>
```

The whitelist guard (`data/is_code_whitelist.json`) is regenerated automatically by `pdf_parser.py`, so anti-hallucination still works against the new corpus. Total rebuild time on GPU: ~2 min for 500-1000 standards. CPU: ~10 min.

### 2.9 Verification — running the test suite

Thirty-plus pytest cases cover the parser, metadata classifier, cross-reference graph, whitelist guard, and the offline-mode invariant for `inference.py`:

```bash
python -m pytest tests/
```

A clean pass means the schema contracts (`is_code`, `retrieved_standards`, `latency_seconds`) and the hallucination guard are intact. Run after any change to `src/` and before submitting.

### 2.10 Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `Could not find a version that satisfies torch==2.11.0` (cu118 / cu121 errors) | Driver < 555, or `setup.py` picked a CUDA wheel that doesn't ship for this torch version | `set TORCH_NO_CUDA=1` (Windows) / `export TORCH_NO_CUDA=1` (Unix) before re-running `setup.py` — installs the CPU wheel instead. Latency goes up but all targets still pass. |
| Setup fails at `pip install`: `numpy 2.2.6` source build, "no compiler" | Python ≥ 3.14 (no pre-built wheels yet for the ML stack) | Install Python 3.10–3.12 from python.org and create a fresh venv with `py -3.11 -m venv venv`. |
| `setup.bat` exits with `'python' is not recognized` or opens the Microsoft Store | Only the Windows Store python stub is on PATH | Install Python from python.org with "Add to PATH" checked, then re-run. `setup.bat` rejects the WindowsApps stub automatically once a real install is available. |
| HF download crawls at ~1 MB/s | Anonymous rate limit | Paste a free read-only HF token when `setup.py` prompts (or set `HF_TOKEN=hf_...` in `.env`). 10–50× speedup. |
| `OSError: no file named model.safetensors, or pytorch_model.bin` at warm-up | Partial / interrupted HF download | Delete the cache for the affected model and re-run setup: `rmdir /s /q "%USERPROFILE%\.cache\huggingface\hub\models--BAAI--bge-m3"` (Windows) / `rm -rf ~/.cache/huggingface/hub/models--BAAI--bge-m3` (Unix). |
| `EADDRINUSE: address already in use :::8000` (or 3000) | Previous backend / frontend still running | Kill leftover processes: `taskkill /F /IM python.exe /IM node.exe` (Windows) / `pkill -f "src.api.main"; pkill -f "next start"` (Unix). |
| Demo backend segfaults at startup | Old build with reverse import order | Pull the latest `main` — `src/api/main.py` now imports `Retriever` before `LLMClient` (commit 4bb52df+). |
| Welcome modal pops up even though `.env` has keys | Backend still loading models at first frontend tick | Wait ~10 s for the `/health` retry to succeed, then close and reopen the modal — keys load on the next request. |
| Cold-cache first query hangs > 30 s | First-query CUDA kernel JIT + cuDNN autotune | Normal. Subsequent queries are 0.4–1 s. The eval script's `latency_seconds` excludes one-time model load. |

If something breaks that isn't on this list, the most common cause is a stale venv — delete `venv/` and re-run `setup.bat`.

---

## 3 · Demo UI (FastAPI + Next.js 16)

The judge eval is fully decoupled from the demo, but the UI is what tells the story.

### 3.0 Boot the demo

The single-command `setup.bat` / `setup.sh` from §2.0 already boots the demo at the end. To re-boot it later (e.g., after `Ctrl+C`) without re-running setup:

```bash
python start.py        # any OS — boots backend on :8000 + frontend on :3000
```

Brings up both servers, waits until they're reachable, opens `http://localhost:3000` in your default browser, and stays in the foreground until `Ctrl+C`. On first run it also auto-installs frontend `node_modules` and builds the production bundle.

If a `GEMINI_API_KEY` / `GROQ_API_KEY` is missing, the UI greets the user with a one-time modal that lets them paste a free key (stored only in browser localStorage) — or skip and use pure-retrieval mode. No `.env` is strictly required.

### 3.1 Manual boot (two terminals)

If you'd rather run them separately:

```bash
# Terminal 1 — backend (FastAPI on :8000)
cp .env.example .env       # optional: paste your GEMINI_API_KEY / GROQ_API_KEY
python -m src.api.main

# Terminal 2 — frontend (Next.js on :3000)
cd frontend
npm install
npm run build && npm start    # use the production build, NOT `npm run dev`
```

> **⚠️ Heads up:** at the time of this build, Next.js 16.2.4 with the default
> Turbopack dev mode + React 19.2 has a hydration bug that leaves Framer
> Motion components stuck at their `initial` (opacity 0) state on first load.
> The production build (`npm run build && npm start`) hydrates cleanly. We
> recommend it for the demo — and that's what the screenshots in
> `docs/demo_hero.png` / `docs/demo_results.png` were captured against.

Open <http://localhost:3000>. You'll land on a full-viewport hero with the project metrics and two CTAs:

* **Try the demo** — smooth-scrolls to the search panel.
* **Watch architecture** — opens an inline 8-scene architecture walkthrough as a modal overlay (`docs/architecture.html` rendered in an iframe). Press `← / → / Space` to navigate scenes, `A` for autoplay, `Esc` to close.

The search panel sends each query to `POST /search` and renders the hybrid top-5 with a confidence band per hit (high / medium / low, calibrated). Above the sample queries, a prominent **AI Rationale Layer** toggle controls whether Gemini / Groq is called:

| Toggle | Latency | Output |
| ------ | ------- | ------ |
| **OFF** *(default)* | ~0.4 s | pure hybrid retrieval (BM25 + dense + RRF + cross-encoder) — **identical** retrieval results to the ON state |
| **ON**              | ~1.5–2 s | adds a Gemini-generated one-line rationale per hit and an expanded query context |

Both modes honour the **IS-code whitelist filter** — any rationale that mentions a code outside the SP 21 corpus is silently dropped before reaching the user. The toggle exists so judges can verify the retrieval system stands on its own without LLM enrichment.

---

## 4 · Repo layout

```
.
├── inference.py                ← MANDATORY judge entry point (--input, --output)
├── eval_script.py              ← MANDATORY (provided by organisers, copied verbatim)
├── setup.py                    ← env setup (deps + indices + warm-up + score), cross-platform
├── start.py                    ← boot the demo (backend on :8000 + frontend on :3000), cross-platform
├── setup.bat                   ← Windows: runs setup.py then start.py in one command
├── setup.sh                    ← macOS / Linux: runs setup.py then start.py in one command
├── requirements.txt
├── README.md  (this file)
├── presentation.pdf            ← 8-slide deck per rulebook §3.1
│
├── datasets/                   ← unmodified inputs from organisers
│   ├── dataset.pdf             ← SP 21 (929 pages)
│   ├── public_test_set.json    ← 10 queries
│   └── sample_output.json
│
├── data/
│   ├── parsed_standards.json   ← 559 structured records (built by pdf_parser)
│   ├── is_code_whitelist.json  ← anti-hallucination guard
│   ├── bootstrap_test_set.json ← 18 synthetic queries we used for honest tuning
│   ├── xrefs.json              ← cross-reference graph (538 edges, 135 standards)
│   ├── index/                  ← FAISS + BM25 artifacts (committed; setup.py skips rebuild)
│   └── results/                ← saved scoring runs
│
├── src/
│   ├── ingestion/pdf_parser.py
│   ├── retrieval/
│   │   ├── embedder.py         ← bge-m3 wrapper
│   │   ├── reranker.py         ← bge-reranker-v2-m3 wrapper
│   │   ├── index.py            ← FAISS dense index
│   │   ├── bm25_index.py       ← BM25 sparse index
│   │   └── retriever.py        ← Hybrid orchestrator (BM25 + dense + RRF + rerank)
│   ├── llm/
│   │   ├── llm_client.py       ← UI-only orchestrator: tries Gemini, falls back to Groq
│   │   ├── gemini_client.py    ← Gemini 2.0 Flash wrapper (rewrite + rationale + HyDE)
│   │   └── groq_client.py      ← Groq Llama 3.3 70B wrapper (fallback path)
│   ├── api/main.py             ← FastAPI backend for the demo (CORS-locked, 127.0.0.1)
│   └── offline_guard.py        ← flips HF_HUB_OFFLINE once weights are verified
│
├── frontend/                   ← Next.js 16 + Tailwind v4 + Framer Motion
│
├── docs/
│   ├── architecture.png        ← rendered Mermaid diagram (in this README)
│   ├── architecture.mmd        ← Mermaid source
│   ├── architecture.html       ← 8-scene animated walkthrough (used by the UI's "Watch architecture" CTA)
│   ├── ablation.md             ← retrieval variant comparison
│   ├── failure_analysis.md     ← per-query miss analysis
│   └── demo_script.md          ← 7-min demo video storyboard
│
├── tests/                      ← pytest suite (parser, metadata, xref, whitelist, offline)
│
└── scripts/
    ├── ablation.py             ← reproduces docs/ablation.md
    ├── bootstrap_eval_set.py   ← synthesises eval queries with Gemini
    ├── calibrate_confidence.py ← derives the 0.55 / 0.40 confidence bands
    ├── failure_analysis.py     ← reproduces docs/failure_analysis.md
    └── setup_offline.py        ← pre-downloads HF model weights
```

---

## 5 · Evaluation details

### Metrics

* **Hit Rate @3**: fraction of queries where at least one expected standard is in the top-3 retrieved.
* **MRR @5**: mean reciprocal rank of the first correct standard in the top-5.
* **Avg latency**: per-query wall-clock retrieval time (excludes one-time model load).

All metrics are computed by the organisers' [`eval_script.py`](eval_script.py), which normalises IS codes by stripping spaces and lowercasing — so `IS 269: 1989` and `IS269:1989` match.

### Eval sets

| Set                         | # queries | Source                                       | Public score                          |
| --------------------------- | --------: | -------------------------------------------- | ------------------------------------- |
| `public_test_set.json`      |        10 | Organisers (cement/concrete/aggregates)      | **100% Hit@3 · 0.93 MRR@5 · 0.47 s** |
| `bootstrap_test_set.json`   |        18 | We synthesised — stratified across SP 21 buckets via Gemini, hand-filtered (see [`scripts/bootstrap_eval_set.py`](scripts/bootstrap_eval_set.py)) | **88.89% Hit@3 · 0.90 MRR@5 · 0.60 s** |

The bootstrap set covers cement, aggregates, concrete, masonry, **steel, pipes, tiles, glass, paint, polymer**, and miscellaneous — a much broader test than the cement-heavy public set. Both eval sets clear all three target thresholds.

### Ablation study

We ablated five retriever variants on both eval sets ([`docs/ablation.md`](docs/ablation.md), reproduce with `python -m scripts.ablation`). Headline finding on the harder bootstrap set:

| Variant | Hit@3 | MRR@5 | Latency |
|---|---:|---:|---:|
| BM25 only | 61.11% | 0.588 | 0.002 s |
| Dense only | 88.89% | 0.826 | 0.033 s |
| BM25 + dense + RRF | 83.33% | 0.769 | 0.001 s |
| **+ cross-encoder rerank** | **88.89%** | **0.903** | 0.524 s |
| **+ category boost (production)** | **88.89%** | **0.903** | 0.527 s |

The cross-encoder reranker contributes **the largest single MRR gain** (+0.077 over hybrid+RRF alone) — that final pass with explicit query↔passage attention is what pulls the correct standard from rank 2 or 3 up to rank 1.

### Anti-hallucination guarantee

Every recommended IS code is checked against `is_code_whitelist.json` (extracted directly from SP 21) before being returned. The Gemini-generated rationale text is also scanned: any sentence that mentions an IS code outside the whitelist is silently dropped. Net result: the system is incapable of returning an imaginary BIS standard.

---

## 6 · External APIs and data

* **Google Gemini 2.0 Flash** (free tier) — primary LLM for the demo UI's query rewriting and rationale generation. The judge entry point `inference.py` does NOT call any external API; it is fully local.
* **Groq Llama 3.3 70B** (free tier) — automatic fallback when Gemini returns a quota / rate-limit error. The `LLMClient` (in `src/llm/llm_client.py`) transparently retries on Groq, so the demo keeps working when Gemini's daily free-tier cap is hit. Set `GROQ_API_KEY` in `.env` to enable; sign up at <https://console.groq.com/keys>.
* **Hugging Face Hub** — for first-time download of `BAAI/bge-m3` and `BAAI/bge-reranker-v2-m3` weights (cached locally afterwards).
* **Source data** — `datasets/dataset.pdf` is the SP 21 (2005) — *Summaries of Indian Standards for Building Materials* — published by the Bureau of Indian Standards under the Right to Information Act, supplied by the hackathon organisers. Unmodified.

No other APIs, datasets, or third-party services are used.

---

## 7 · Acknowledgements

* **Bureau of Indian Standards** for the SP 21 corpus.
* **Beijing Academy of AI** for the bge-m3 + bge-reranker-v2-m3 models.
* **Sigma Squad** for organising this hackathon.

— Built solo for the **Sigma Squad × Bureau of Indian Standards Hackathon**, April 2026.
