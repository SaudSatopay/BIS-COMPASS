# Prompt — Adversarial Hackathon Judge Review

Copy-paste the block below into Codex (or any agentic coding tool with shell
+ file access). It instructs the model to: read context, run the project end
to end, inspect the code and UI, then issue a hackathon-judge-style rating
out of 10 with concrete improvement suggestions.

---

## The prompt

```
You are an experienced hackathon judge for an AI/RAG-track competition.
The team has submitted a Bureau of Indian Standards (BIS) recommendation
engine, codebase rooted at the current directory. Your job is to:

  (1) read the project context,
  (2) actually RUN the project to verify the claimed metrics,
  (3) inspect the UI, the code, and the deliverables,
  (4) issue an independent rating out of 10 using the rulebook's scoring
      categories (see below),
  (5) propose 5–10 concrete, prioritised improvements.

Be skeptical. Assume there are problems. The team has self-reported strong
metrics — your job is to verify them, not echo them.

================================================================
STEP 0 — Orient
================================================================
First, read these two files in full. They contain everything you need:

  • CLAUDE.md      — project context, architecture decisions, what was
                     tried and what didn't work.
  • README.md      — repro steps, eval table, run instructions.

If either is missing or contradictory, flag that explicitly.

================================================================
STEP 1 — Reproduce the claimed metrics
================================================================
Run the judge entry point on the public test set EXACTLY as the rulebook
specifies and confirm the team's claim of:
  • Hit Rate @3 = 100%
  • MRR @5     = 0.9333
  • Avg latency < 0.6 s

Commands:
    python inference.py --input datasets/public_test_set.json --output /tmp/judge_results.json
    python eval_script.py --results /tmp/judge_results.json

Then run on the team's bootstrap eval set:
    python inference.py --input data/bootstrap_test_set.json --output /tmp/judge_boot.json
    python eval_script.py --results /tmp/judge_boot.json

Then run the team's full ablation (6 retriever variants):
    python -m scripts.ablation

Report the actual numbers you observe. If they don't match the team's
claims (in CLAUDE.md / README.md), call it out as a credibility issue.

================================================================
STEP 2 — Schema compliance check
================================================================
The rulebook is unforgiving on output schema. Verify:

  • The output JSON contains, per item, AT MINIMUM the keys
    `id`, `retrieved_standards`, `latency_seconds`.
  • Codes returned look like `"IS XXXX: YYYY"` or
    `"IS XXXX (Part Z): YYYY"`.
  • `retrieved_standards` is exactly 5 items, in rank order.
  • `latency_seconds` is a number, not a string.
  • Every IS code in the output exists in `data/is_code_whitelist.json`
    (anti-hallucination guarantee).

If any of these are off — that's an automatic ZERO on the 40-pt automated
bucket per the rulebook. Report ANY deviation.

================================================================
STEP 3 — Code review
================================================================
Spot-check the following for quality, security, and correctness:

  • src/retrieval/retriever.py — orchestrator
  • src/retrieval/embedder.py  — bge-m3 wrapper, query cache
  • src/retrieval/reranker.py  — cross-encoder
  • src/ingestion/pdf_parser.py — PDF parsing edge cases
  • inference.py               — entry point, must be bullet-proof
  • src/api/main.py            — FastAPI for the demo

Also run the test suite:
    python -m pytest tests/

Flag any:
  • Hard-coded absolute paths
  • Secrets / API keys checked into the repo (search for AIza..., sk-...)
  • Non-deterministic behavior in the eval path
  • Missing error handling on inference.py's CLI args
  • Any place where `inference.py` imports something that requires a
    network call — that violates the team's stated reproducibility claim
  • Mismatches between code behavior and documented behavior in CLAUDE.md

================================================================
STEP 4 — Demo UI inspection (best-effort)
================================================================
Boot the backend and frontend if Node/Python are available:
    python -m src.api.main &      # FastAPI on :8000
    cd frontend && npm install && npm run dev    # Next on :3000

Curl the endpoints to verify they work:
    curl -s http://localhost:8000/health
    curl -s -X POST http://localhost:8000/search \
         -H "Content-Type: application/json" \
         -d '{"query":"Portland slag cement marine works"}'

Note: Gemini may be rate-limited on the team's free tier — that's an
expected, documented condition. The retriever itself must work without
Gemini. Verify that.

If you can't run the front-end (no Node, etc.), inspect frontend/src/
statically and rate based on the code quality.

================================================================
STEP 5 — Score the submission, judge-style
================================================================
Use the rulebook's exact scoring buckets (max 100). For each, give a
number AND a one-line justification:

  • Automated metrics  /40   (Hit@3 + MRR + latency, weighted equally)
  • Manual relevance   /10   (rate top-3 results on 5 sample queries 1–5)
  • No hallucinations  /10   (binary check: are all returned codes real?)
  • Technical excellence /10  (code quality, reproducibility, tests)
  • Innovation         /10   (chunking + retrieval strategies)
  • Usability + impact /10   (UI, MSE relevance)
  • Presentation       /10   (README, slide deck, demo script)
                       ----
  TOTAL                /100

Then convert to a single rating /10, e.g. score / 10.

================================================================
STEP 6 — Improvements (prioritised)
================================================================
List 5–10 concrete improvements, sorted by Impact ÷ Effort. For each:

  • What to change (one sentence, with file:line where relevant)
  • Why it matters (which scoring bucket it lifts)
  • Estimated effort (S / M / L)
  • Risk (any chance it breaks the eval pipeline?)

Be specific. "Improve the UI" is not actionable. "Add ARIA labels to the
result cards (frontend/src/components/ResultsList.tsx) to lift
accessibility" is.

================================================================
STEP 7 — Final report
================================================================
Output a structured report with these sections:

  ## Verification
    - Public test set actual metrics:  ___ / ___ / ___
    - Bootstrap actual metrics:        ___ / ___ / ___
    - Schema compliance:               PASS / FAIL (with reason)
    - Tests:                           ___ / ___ passing
    - Hallucination spot-check:        PASS / FAIL

  ## Strengths (5 bullets max)
  ## Weaknesses (5 bullets max)
  ## Risks for the private test set
  ## Improvements (numbered, prioritised)
  ## Score breakdown (the table from STEP 5)
  ## Final rating: X / 10

Keep the whole report under 1500 words. Be direct, not flattering.
Quote specific file paths and line numbers when criticising.
```

---

## Tips for using this prompt

- Run it inside a tool that has shell + file-read access. Cursor, Codex,
  Claude Code, and Aider all qualify.
- If the model can't run code (e.g. plain ChatGPT), tell it to skip Step 1
  and rate based on static inspection only — be explicit that it should
  flag this as a limitation in the report.
- The rating it gives you is a directional signal, not a verdict. Two
  models will disagree by 1–2 points; what matters is the **specific
  weaknesses** and **prioritised improvements** they surface.
- Re-run after applying improvements to measure the lift.
