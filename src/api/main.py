"""FastAPI backend for the demo UI.

Exposes a single /search endpoint that runs the hybrid RAG pipeline AND
generates grounded one-line rationales per hit via Gemini. The judge entry
point (inference.py) does not depend on this server — it imports the
retriever directly. This keeps the eval pipeline 100% local while the demo
gets the polished, AI-narrated UX.
"""
from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

from pathlib import Path  # noqa: E402

from src.offline_guard import enforce_offline_if_cached  # noqa: E402

enforce_offline_if_cached()

# IMPORT ORDER MATTERS. The retriever pulls in torch + transformers +
# faiss; LLMClient pulls in google.genai (which itself drags in grpc /
# protobuf). On some Windows configurations, loading google.genai BEFORE
# torch leaves protobuf in a state that segfaults the C-extension
# initialisation later in transformers. Importing torch/transformers
# first via Retriever pins protobuf's symbol table the way native CUDA
# code expects it, then google.genai is loaded into that environment
# without conflict. Caught by a cold-clone demo-boot test on Windows.
from src.retrieval.retriever import Retriever  # noqa: E402
from src.llm.llm_client import LLMClient  # noqa: E402


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(5, ge=1, le=20)
    rewrite: bool = True
    rationales: bool = True
    hyde: bool = False         # opt-in: HyDE adds 1 LLM call (~700ms)
    multi_query: bool = False  # opt-in: 1 extra LLM call, 3 paraphrased variants
    # Optional per-request LLM keys — frontend can pass these from the
    # browser's localStorage so judges can enable AI features without
    # touching the .env file. Falls back to env-configured client if absent.
    gemini_api_key: str | None = None
    groq_api_key: str | None = None


class HitOut(BaseModel):
    rank: int
    is_code: str
    title: str
    scope: str
    rerank_score: float
    rrf_score: float
    rationale: str | None = None
    confidence: str  # "high" | "medium" | "low"
    related_standards: list[str] = []
    categories: list[str] = []


def _confidence_band(rerank_score: float) -> str:
    """Bucket rerank sigmoid scores into UI-friendly bands.

    Calibrated on the bootstrap eval set via scripts/calibrate_confidence.py
    (results: data/results/confidence_calibration.json). Headline finding:
      - rerank_score >= 0.55  ->  85.7% of these hits were correct (HIGH)
      - 0.40 <= score < 0.55  ->  13.3% precision (MEDIUM — could be right)
      - score <  0.40         ->  effectively noise (LOW)
    """
    if rerank_score >= 0.55:
        return "high"
    if rerank_score >= 0.40:
        return "medium"
    return "low"


class SearchResponse(BaseModel):
    query: str
    expanded_query: str | None
    material: str | None
    application: str | None
    hits: list[HitOut]
    latency_seconds: float
    used_gemini: bool                    # legacy field — true if any LLM fired
    llm_provider: str | None             # "gemini" | "groq" | None
    llm_status: str                      # ok | fellback_to_groq | rate_limited | disabled | all_providers_failed
    llm_message: str | None = None
    # back-compat shims so older frontends don't break
    gemini_status: str
    gemini_message: str | None = None


STATE: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[api] Loading retriever ...")
    t = time.perf_counter()
    STATE["retriever"] = Retriever()
    print(f"[api]   ready in {time.perf_counter() - t:.1f}s")
    STATE["llm"] = LLMClient()
    print(f"[api] LLM providers ready: {STATE['llm'].providers or 'NONE'}")
    # Load cross-references (best-effort)
    import json as _json
    xref_path = Path("data/xrefs.json")
    if xref_path.exists():
        STATE["xrefs"] = _json.loads(xref_path.read_text(encoding="utf-8"))
        print(f"[api] Loaded {len(STATE['xrefs'])} cross-reference entries")
    else:
        STATE["xrefs"] = {}
    # Eager-load standards-by-code map. Doing this here (rather than
    # lazily in get_standard) avoids a thundering-herd race where two
    # concurrent first-time hits both parse the 5 MB JSON.
    standards_path = Path("data/parsed_standards.json")
    if standards_path.exists():
        records = _json.loads(standards_path.read_text(encoding="utf-8"))
        STATE["standards_by_code"] = {s["is_code"]: s for s in records}
        print(f"[api] Loaded {len(STATE['standards_by_code'])} standards into lookup map")
    else:
        STATE["standards_by_code"] = {}
    yield


app = FastAPI(title="BIS RAG Recommender", version="1.0", lifespan=lifespan)
# CORS: restrict to localhost only. The demo UI lives on :3000 same machine.
# Wide-open origins would let any LAN peer / visited website spend the
# user's HF / Gemini / Groq keys via this local backend's /search endpoint.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health():
    llm: LLMClient | None = STATE.get("llm")
    return {
        "ok": True,
        "llm_providers": llm.providers if llm else [],
        "llm_primary": llm._primary_name if llm and llm.enabled else None,
        # Back-compat field
        "gemini": bool(llm and llm.gemini is not None),
    }


class StandardDetail(BaseModel):
    is_code: str
    title: str
    scope: str
    revision: str | None
    page_start: int
    page_end: int
    full_text: str
    related_standards: list[str]
    categories: list[str]


# IS code shape: "IS 269: 1989", "IS 2185 (Part 1): 1979", etc.
# Restrict the URL parameter to this pattern so arbitrary input
# (path traversal probes, reflected-XSS smells) never reaches the
# lookup. Whitespace-tolerant.
import re as _re_mod  # noqa: E402

_IS_CODE_RE = _re_mod.compile(
    r"^IS\s*\d+(?:\s*\(Part\s*\d+(?:/\s*Sec\s*\d+)?\))?\s*:\s*\d{4}$",
    _re_mod.IGNORECASE,
)


@app.get("/standards/{is_code}", response_model=StandardDetail)
def get_standard(is_code: str):
    """Fetch the full record for one IS code (used by the detail modal).

    is_code must match the IS-code grammar — invalid input gets a generic
    404 without echoing the user-supplied string back.
    """
    from fastapi import HTTPException
    if not _IS_CODE_RE.match(is_code or ""):
        raise HTTPException(404, "IS code not found")

    standards = STATE.get("standards_by_code") or {}
    s = standards.get(is_code)
    if not s:
        # Tolerant lookup — match by normalised form
        norm = _re_mod.sub(r"\s+", "", is_code).lower()
        for code, rec in standards.items():
            if rec.get("is_code_norm") == norm:
                s = rec
                break
    if not s:
        raise HTTPException(404, "IS code not found")
    related = (STATE.get("xrefs") or {}).get(s["is_code"], [])
    from src.retrieval.metadata import detect_categories
    blob = f"{s['title']} {s.get('scope') or ''}"
    cats = sorted(detect_categories(blob))
    return StandardDetail(
        is_code=s["is_code"],
        title=s["title"],
        scope=s.get("scope") or "",
        revision=s.get("revision"),
        page_start=s["page_start"],
        page_end=s["page_end"],
        full_text=s.get("full_text") or "",
        related_standards=related,
        categories=cats,
    )


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    retriever: Retriever = STATE["retriever"]
    # If the request carries per-request LLM keys (sent by the frontend from
    # browser localStorage), build a one-off client; otherwise use the
    # process-wide one constructed from env.
    llm: LLMClient | None
    if req.gemini_api_key or req.groq_api_key:
        try:
            llm = LLMClient(
                gemini_api_key=req.gemini_api_key or None,
                groq_api_key=req.groq_api_key or None,
                verbose=False,
            )
        except Exception:  # noqa: BLE001
            llm = STATE.get("llm")
    else:
        llm = STATE.get("llm")
    used_gemini = False  # legacy bool — true if any LLM produced output
    expanded = None
    material = None
    application = None

    # Status reflects the LAST LLM call's outcome (best signal for the UI).
    # Initialised to "disabled" if neither provider is configured, else "ok".
    llm_status = "disabled" if (llm is None or not llm.enabled) else "ok"
    llm_message: str | None = (
        None if (llm is not None and llm.enabled)
        else "No LLM API keys configured (GEMINI_API_KEY / GROQ_API_KEY). "
             "Retrieval still works; AI rewrite and rationales are off."
    )
    llm_provider: str | None = None

    def _note_call(stage: str, fired: bool):
        nonlocal llm_status, llm_message, llm_provider, used_gemini
        if llm is None:
            return
        if fired:
            used_gemini = True
            llm_provider = llm.last.provider
            # Promote to "fellback_to_groq" if that's what happened
            if llm.last.status == "fellback_to_groq" and llm_status != "fellback_to_groq":
                llm_status = "fellback_to_groq"
                llm_message = (
                    "Gemini quota exhausted on this request — automatically "
                    "fell back to Groq (Llama 3.3 70B). Retrieval is unchanged."
                )
        else:
            # Only downgrade status if we haven't already noted success in this request
            if llm_status == "ok":
                llm_status = "rate_limited"
                llm_message = (
                    f"LLM call ({stage}) returned no result. "
                    f"Tried providers: {llm.providers}. "
                    "Retrieval is unaffected."
                )

    t0 = time.perf_counter()

    dense_query = None
    if req.rewrite and llm is not None and llm.enabled:
        rw = llm.rewrite_query(req.query)
        if rw.expanded and rw.expanded.strip() != req.query.strip():
            dense_query = rw.expanded
            expanded = rw.expanded
            material = rw.material
            application = rw.application
            _note_call("rewrite_query", True)
        else:
            _note_call("rewrite_query", False)

    # HyDE: if enabled, fold a hypothetical-doc passage into the dense query.
    if req.hyde and llm is not None and llm.enabled:
        h = llm.hyde_passage(req.query)
        if h:
            dense_query = f"{dense_query or req.query}\n\n{h}"
            _note_call("hyde_passage", True)
        else:
            _note_call("hyde_passage", False)

    multi_qs: list[str] = []
    if req.multi_query and llm is not None and llm.enabled:
        multi_qs = llm.multi_query_variants(req.query, n=3)
        if multi_qs:
            _note_call("multi_query", True)
        else:
            _note_call("multi_query", False)

    hits = retriever.search(
        req.query, dense_query=dense_query, multi_queries=multi_qs
    )[: req.top_k]

    rationales: list[dict] = []
    if req.rationales and llm is not None and llm.enabled and hits:
        rationales = llm.generate_rationales(
            req.query,
            [{"is_code": h.is_code, "title": h.title, "scope": h.scope} for h in hits],
        )
        _note_call("rationales", bool(rationales))

    rationale_by_code = {r.get("is_code"): r.get("reason") for r in rationales if isinstance(r, dict)}
    whitelist = retriever.whitelist_norm
    import re as _re
    # Phrases the LLM uses when it concludes a candidate doesn't really apply.
    # We strip such rationales — they're confusing on items we're still
    # showing (rank 4 / 5 are "related but secondary" by design, not "wrong").
    _NEGATIVE_PATTERNS = _re.compile(
        r"\b(?:doesn'?t|does\s+not|not\s+(?:directly\s+)?(?:apply|applicable|relevant|related)|"
        r"unrelated|inapplicable|irrelevant|n/?a)\b",
        _re.IGNORECASE,
    )
    hits_out: list[HitOut] = []
    for h in hits:
        reason = rationale_by_code.get(h.is_code)
        if reason:
            # Hallucination guard: reject rationales that mention IS codes
            # outside the SP 21 whitelist.
            for found in _re.findall(r"IS\s*\d+\s*(?:\(Part[^)]+\))?\s*:\s*\d{4}", reason):
                norm = _re.sub(r"\s+", "", found).lower()
                if norm not in whitelist:
                    reason = None
                    break
        if reason and _NEGATIVE_PATTERNS.search(reason):
            # Suppress "does not apply" / "not directly applicable" on hits
            # we're recommending — these are confusing UX. The card still
            # ranks the standard normally; we just hide the disqualifying note.
            reason = None
        related = (STATE.get("xrefs") or {}).get(h.is_code, [])[:4]
        hits_out.append(HitOut(
            rank=h.rank,
            is_code=h.is_code,
            title=h.title,
            scope=h.scope,
            rerank_score=round(h.rerank_score, 4),
            rrf_score=round(h.rrf_score, 4),
            rationale=reason,
            confidence=_confidence_band(h.rerank_score),
            related_standards=related,
            categories=list(h.categories),
        ))

    return SearchResponse(
        query=req.query,
        expanded_query=expanded,
        material=material,
        application=application,
        hits=hits_out,
        latency_seconds=round(time.perf_counter() - t0, 3),
        used_gemini=used_gemini,
        llm_provider=llm_provider,
        llm_status=llm_status,
        llm_message=llm_message,
        # Back-compat fields the existing UI still reads.
        gemini_status=llm_status if llm_status != "fellback_to_groq" else "ok",
        gemini_message=llm_message,
    )


def main():
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    # Bind 127.0.0.1, not 0.0.0.0 — the demo backend should be reachable
    # only from the same machine. Override with HOST=0.0.0.0 if you really
    # need LAN access (e.g., remote demo screensharing).
    host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
