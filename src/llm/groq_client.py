"""Groq client — drop-in fallback for GeminiClient.

Same public surface as GeminiClient (`rewrite_query`, `hyde_passage`,
`multi_query_variants`, `generate_rationales`, `generate_eval_query`) so
`LLMClient` can swap them transparently when Gemini hits its free-tier quota.

Groq exposes an OpenAI-compatible chat-completions API. We use Llama 3.3 70B
by default — it's free-tier on Groq and roughly matches Gemini Flash quality
for these short prompts.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from groq import Groq, RateLimitError, APIStatusError

# IMPORTANT: import the SAME RewrittenQuery dataclass that GeminiClient uses,
# so the LLMClient wrapper's isinstance() checks work whichever provider answered.
from src.llm.gemini_client import RewrittenQuery


# We deliberately keep the prompts identical in spirit to the Gemini ones so
# behaviour is consistent across providers. Each enforces `response_format =
# json_object` so we don't have to parse free-form text.

_QUERY_REWRITE_PROMPT = """You are an expert in Indian building-material standards (BIS).
Given a natural-language product description from a small Indian manufacturer,
expand it into a search-friendly query for a vector search over the SP 21 corpus.

Return JSON with these keys:
  - "expanded": one paragraph (<= 200 words) restating the product, naming the
    material, application area, and any technical descriptors. Use BIS terminology
    (e.g. "ordinary Portland cement 33 grade", "lightweight aggregate concrete
    block", "precast reinforced concrete pipe"). DO NOT invent IS codes.
  - "material": one of: cement, concrete, steel, aggregate, brick, tile, pipe,
    glass, paint, wood, asbestos, polymer, gypsum, lime, other
  - "application": short phrase, or null
  - "spec_type": one of: specification, testing, dimensions, chemical, physical,
    method, classification, code-of-practice

User query: {query}"""


_HYDE_PROMPT = """You are an expert in Indian building-material standards (BIS).
Given a natural-language product description from a small Indian manufacturer,
write a SHORT (50-120 words) synthetic 'standard summary' paragraph that
describes what an applicable BIS standard for this product would cover.

Use BIS terminology and SP 21 phrasing patterns. DO NOT invent IS code numbers.
Refer to "the applicable Indian Standard" instead.

User query: {query}

Return JSON: {{"hyde": "..."}}."""


_MULTI_QUERY_PROMPT = """You are an expert in Indian building-material standards (BIS).
Generate {n} additional paraphrased variants of the user query that might
surface complementary candidate standards. Variants should:
  - Preserve the user's intent and any specific technical tokens (M30, 33 grade,
    Part 2). DO NOT drop or generalise these.
  - Differ in phrasing.
  - Be complete, standalone queries.
  - Use BIS-style terminology where natural.

DO NOT invent IS code numbers.

User query: {query}

Return JSON: {{"variants": ["...", ...]}}."""


_RATIONALE_PROMPT = """You are advising an Indian small enterprise on BIS compliance.
For each retrieved standard below, write ONE sentence (<= 25 words) explaining
why it applies. Cite ONLY the IS codes provided — never invent codes.

User product: {query}

Retrieved standards:
{standards_block}

Return JSON: {{"rationales": [{{"is_code": "...", "reason": "..."}}, ...]}}.
One entry per standard above, in the same order."""


_EVAL_QUERY_PROMPT = """Simulate a small Indian manufacturer asking about which BIS
standard applies to their product. Read the standard below and write ONE realistic
natural question an MSE owner might ask — varied tone (manufacturing, compliance,
certification, testing, supplier). DO NOT mention the IS code or year.

Standard: {is_code} — {title}
Scope: {scope}

Return JSON: {{"query": "..."}}."""


def _extract_json(text: str) -> Any:
    text = (text or "").strip()
    # Strip ``` fences if the model adds them (Llama sometimes does)
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for pat in (r"\{[\s\S]*\}", r"\[[\s\S]*\]"):
            m = re.search(pat, text)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
    return None


class GroqClient:
    """OpenAI-shape Groq client. Same public surface as GeminiClient."""

    # Class-level error type that LLMClient uses to detect quota exhaustion
    # (mirrors what we look for from Gemini).
    QUOTA_EXCEEDED_TYPES: tuple[type[Exception], ...] = (RateLimitError,)

    def __init__(self, api_key: str | None = None, model: str | None = None):
        api_key = api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY missing. Add it to .env")
        self.client = Groq(api_key=api_key)
        self.model_name = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # -- Internal helpers -----------------------------------------------------
    def _generate_json(self, prompt: str, max_tokens: int = 1024) -> Any:
        """Single chat completion in JSON mode. Returns parsed JSON or None on
        failure. Re-raises RateLimitError so the LLMClient wrapper can route
        around quota issues — every other error returns None (graceful)."""
        try:
            resp = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You return strict JSON. No commentary, no markdown fences."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=max_tokens,
            )
            text = resp.choices[0].message.content or ""
            return _extract_json(text)
        except RateLimitError:
            raise
        except APIStatusError as e:
            print(f"[groq] API error: {e.status_code} {e.message[:150] if hasattr(e, 'message') else e}")
            return None
        except Exception as e:
            print(f"[groq] generate_content failed: {e}")
            return None

    # -- Public API (mirrors GeminiClient) -----------------------------------
    def rewrite_query(self, query: str) -> RewrittenQuery:
        data = self._generate_json(_QUERY_REWRITE_PROMPT.format(query=query)) or {}
        if not isinstance(data, dict):
            data = {}
        return RewrittenQuery(
            expanded=(data.get("expanded") or query).strip(),
            material=data.get("material"),
            application=data.get("application"),
            spec_type=data.get("spec_type"),
        )

    def hyde_passage(self, query: str) -> str | None:
        data = self._generate_json(_HYDE_PROMPT.format(query=query), max_tokens=600) or {}
        if not isinstance(data, dict):
            return None
        h = data.get("hyde")
        return h.strip() if isinstance(h, str) and h.strip() else None

    def multi_query_variants(self, query: str, n: int = 3) -> list[str]:
        data = self._generate_json(_MULTI_QUERY_PROMPT.format(query=query, n=n), max_tokens=600) or {}
        if not isinstance(data, dict):
            return []
        v = data.get("variants") or []
        return [s.strip() for s in v if isinstance(s, str) and s.strip()][:n]

    def generate_rationales(self, query: str, standards: list[dict]) -> list[dict]:
        block = "\n".join(
            f"- {s['is_code']} — {s['title']}: {s.get('scope', '')[:200]}"
            for s in standards
        )
        data = self._generate_json(
            _RATIONALE_PROMPT.format(query=query, standards_block=block), max_tokens=1500
        ) or {}
        if not isinstance(data, dict):
            return []
        rats = data.get("rationales") or []
        return rats if isinstance(rats, list) else []

    def generate_eval_query(self, standard: dict) -> str | None:
        prompt = _EVAL_QUERY_PROMPT.format(
            is_code=standard["is_code"],
            title=standard["title"],
            scope=(standard.get("scope") or "")[:600],
        )
        data = self._generate_json(prompt, max_tokens=300) or {}
        if not isinstance(data, dict):
            return None
        q = data.get("query")
        return q.strip() if isinstance(q, str) and q.strip() else None
