"""Thin wrapper around Google Gemini for: query rewriting, rationale, eval-set generation.

Uses the modern `google-genai` SDK with structured-output JSON mode. Falls back
to the original query if the API errors so retrieval still runs end-to-end.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types


@dataclass
class RewrittenQuery:
    expanded: str
    material: str | None
    application: str | None
    spec_type: str | None


_QUERY_REWRITE_PROMPT = """You are an expert in Indian building-material standards (BIS).
Given a natural-language product description from a small Indian manufacturer,
expand it into a search-friendly query for a vector search over the SP 21 corpus
of BIS standards on building materials.

Return JSON with these keys:
  - "expanded": one paragraph (<= 200 words) restating the product, naming the
    material, application area, and any technical descriptors. Use BIS terminology
    (e.g. "ordinary Portland cement 33 grade", "lightweight aggregate concrete
    block", "precast reinforced concrete pipe"). DO NOT invent IS codes.
  - "material": one of: cement, concrete, steel, aggregate, brick, tile, pipe,
    glass, paint, wood, asbestos, polymer, gypsum, lime, other
  - "application": short phrase (e.g. "structural concrete", "roofing", "masonry mortar")
    or null
  - "spec_type": one of: specification, testing, dimensions, chemical, physical,
    method, classification, code-of-practice

User query: {query}"""


_RATIONALE_PROMPT = """You are advising an Indian small enterprise on BIS compliance.
For each retrieved standard below, write ONE sentence (<= 25 words) explaining
why it applies. Cite ONLY the IS codes provided — never invent codes.

User product: {query}

Retrieved standards:
{standards_block}

Return JSON: {{"rationales": [{{"is_code": "...", "reason": "..."}}, ...]}}.
One entry per standard above, in the same order."""


_MULTI_QUERY_PROMPT = """You are an expert in Indian building-material standards (BIS).
The user query below is going through a vector + lexical retrieval system over
the BIS SP 21 corpus. Generate {n} additional paraphrased query variants that
might surface complementary candidate standards. Variants should:

  - Preserve the user's intent and any specific technical tokens (e.g. M30, 33
    grade, Part 2). DO NOT drop or generalise these.
  - Differ in phrasing (terminology level, formality, sentence structure).
  - Each be a complete, standalone query.
  - Use BIS-style terminology where natural.

DO NOT invent IS code numbers.

User query: {query}

Return JSON: {{"variants": ["...", "...", ...]}}.  No commentary."""


_HYDE_PROMPT = """You are an expert in Indian building-material standards (BIS).
Given a natural-language product description from a small Indian manufacturer,
write a SHORT (50-120 words) synthetic 'standard summary' paragraph that
describes what an applicable BIS standard for this product would cover.

Use BIS terminology and SP 21 phrasing patterns: e.g. "Specification for
manufacture, chemical and physical requirements of...", "Scope: covers...",
"Requirements include...". This synthetic passage will be embedded for
retrieval — its purpose is to look like a real SP 21 standard summary, not
to be factually new.

DO NOT invent IS code numbers (no "IS 269", no "IS 8112"). Refer to "the
applicable Indian Standard" instead.

User query: {query}

Return JSON: {{"hyde": "..."}}."""


_EVAL_QUERY_PROMPT = """Simulate a small Indian manufacturer asking about which BIS
standard applies to their product. Read the standard below and write ONE realistic
natural question an MSE owner might ask — varied tone (manufacturing, compliance,
certification, testing, supplier). DO NOT mention the IS code or year.
Return JSON: {{"query": "..."}}.

Standard: {is_code} — {title}
Scope: {scope}"""


def _strip_fences(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```\s*$", "", s)
    return s.strip()


def _extract_json(text: str) -> Any:
    text = _strip_fences(text or "")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try to find a JSON object/array within the text
    for pattern in (r"\{[\s\S]*\}", r"\[[\s\S]*\]"):
        m = re.search(pattern, text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                continue
    return None


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY missing. Add it to .env")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def _generate_json(self, prompt: str, max_output_tokens: int = 1024) -> Any:
        try:
            resp = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=max_output_tokens,
                    response_mime_type="application/json",
                    # Disable thinking — these prompts are short and we don't want
                    # Gemini 2.5 Flash to silently burn the output budget on
                    # internal reasoning tokens.
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            return _extract_json(resp.text or "")
        except Exception as e:
            print(f"[gemini] generate_content failed: {e}")
            return None

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

    def generate_rationales(self, query: str, standards: list[dict]) -> list[dict]:
        block = "\n".join(
            f"- {s['is_code']} — {s['title']}: {s.get('scope', '')[:200]}"
            for s in standards
        )
        data = self._generate_json(
            _RATIONALE_PROMPT.format(query=query, standards_block=block),
            max_output_tokens=1500,
        ) or {}
        if not isinstance(data, dict):
            return []
        rats = data.get("rationales") or []
        return rats if isinstance(rats, list) else []

    def multi_query_variants(self, query: str, n: int = 3) -> list[str]:
        """Return n paraphrased query variants. Empty list on failure."""
        data = self._generate_json(
            _MULTI_QUERY_PROMPT.format(query=query, n=n), max_output_tokens=600
        ) or {}
        if not isinstance(data, dict):
            return []
        v = data.get("variants") or []
        return [s.strip() for s in v if isinstance(s, str) and s.strip()][:n]

    def hyde_passage(self, query: str) -> str | None:
        """HyDE: generate a hypothetical standard summary for the query.

        Returns the generated passage as a string, or None if generation
        failed. The passage is meant to be embedded alongside (or instead of)
        the raw query — it tends to live in the same vector neighbourhood as
        real standard summaries, improving recall on paraphrased / colloquial
        queries.
        """
        data = self._generate_json(_HYDE_PROMPT.format(query=query), max_output_tokens=600) or {}
        if not isinstance(data, dict):
            return None
        h = data.get("hyde")
        return h.strip() if isinstance(h, str) and h.strip() else None

    def generate_eval_query(self, standard: dict) -> str | None:
        prompt = _EVAL_QUERY_PROMPT.format(
            is_code=standard["is_code"],
            title=standard["title"],
            scope=(standard.get("scope") or "")[:600],
        )
        data = self._generate_json(prompt, max_output_tokens=300) or {}
        if not isinstance(data, dict):
            return None
        q = data.get("query")
        return q.strip() if isinstance(q, str) and q.strip() else None
