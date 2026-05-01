"""LLMClient — provider-agnostic facade with automatic Gemini → Groq failover.

Used by `src/api/main.py`. Public surface matches GeminiClient/GroqClient so
the rest of the codebase doesn't care which provider answered.

Behaviour:
  - On startup, tries to construct GeminiClient and GroqClient. Whichever
    succeeds is enabled. If neither, the client runs in "no-op" mode and
    every method returns a graceful empty result.
  - For each call we try the primary provider (Gemini by default — it's the
    one we built against and tested most). If Gemini raises a quota /
    rate-limit error, we transparently retry on Groq.
  - The `last_status` and `last_message` attributes are updated after every
    call so the API can surface honest UX state ("ok" / "rate_limited" /
    "fellback_to_groq" / "all_providers_failed" / "disabled").

Order of providers is configurable via `LLM_PRIMARY` env var ("gemini" or
"groq"); default is "gemini".
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from src.llm.gemini_client import GeminiClient, RewrittenQuery as _RQ


@dataclass
class _Status:
    status: str
    message: str | None
    provider: str | None  # "gemini" / "groq" / None


# Detect quota / rate-limit signals from either provider. Gemini raises
# google.api_core errors with "RESOURCE_EXHAUSTED" / 429 in the body;
# Groq raises groq.RateLimitError. We treat both as recoverable.
def _is_quota_error(exc: Exception) -> bool:
    msg = (str(exc) or "").lower()
    if "ratelimit" in msg or "rate_limit" in msg or "rate limit" in msg:
        return True
    if "resource_exhausted" in msg or "quota" in msg or "429" in msg:
        return True
    # Also detect groq's typed exception when available
    try:
        from groq import RateLimitError as _GroqRL
        if isinstance(exc, _GroqRL):
            return True
    except Exception:
        pass
    return False


class LLMClient:
    def __init__(
        self,
        gemini_api_key: str | None = None,
        groq_api_key: str | None = None,
        verbose: bool = True,
    ):
        primary = (os.getenv("LLM_PRIMARY") or "gemini").lower().strip()
        if primary not in {"gemini", "groq"}:
            primary = "gemini"

        self.gemini: GeminiClient | None = None
        self.groq = None  # type: ignore[assignment]

        # Try Gemini
        try:
            self.gemini = GeminiClient(api_key=gemini_api_key)
            if verbose:
                print(f"[llm] Gemini ready ({self.gemini.model_name})")
        except Exception as e:
            if verbose:
                print(f"[llm] Gemini unavailable: {e}")

        # Try Groq (lazy import so its dependency doesn't bog down env init)
        try:
            from src.llm.groq_client import GroqClient
            self.groq = GroqClient(api_key=groq_api_key)
            if verbose:
                print(f"[llm] Groq ready ({self.groq.model_name})")
        except Exception as e:
            if verbose:
                print(f"[llm] Groq unavailable: {e}")

        self._primary_name = primary
        self.last = _Status(
            status="ok" if (self.gemini or self.groq) else "disabled",
            message=None if (self.gemini or self.groq) else "No LLM API keys configured.",
            provider=None,
        )

    # ------------------------------------------------------------------
    @property
    def enabled(self) -> bool:
        return self.gemini is not None or self.groq is not None

    @property
    def providers(self) -> list[str]:
        out = []
        if self.gemini is not None: out.append("gemini")
        if self.groq is not None: out.append("groq")
        return out

    def _ordered_clients(self):
        """Yield (name, client) in primary→fallback order, skipping unavailable."""
        order = [self._primary_name, "groq" if self._primary_name == "gemini" else "gemini"]
        for name in order:
            client = self.gemini if name == "gemini" else self.groq
            if client is not None:
                yield name, client

    def _try_call(self, method_name: str, *args, **kwargs):
        """Call `method_name` on each provider in order until one returns a
        non-empty result. Sets self.last to reflect what happened."""
        if not self.enabled:
            self.last = _Status(status="disabled", message="No LLM API keys configured.", provider=None)
            return None

        attempted: list[tuple[str, str]] = []
        for name, client in self._ordered_clients():
            try:
                method = getattr(client, method_name)
                result = method(*args, **kwargs)
                # "Empty" result heuristic per method — let caller distinguish
                if _is_empty(method_name, result):
                    attempted.append((name, "empty result"))
                    continue
                self.last = _Status(
                    status="fellback_to_groq" if name == "groq" and self._primary_name == "gemini" else "ok",
                    message=None,
                    provider=name,
                )
                return result
            except Exception as e:
                attempted.append((name, str(e)[:160]))
                if _is_quota_error(e):
                    # Try the next provider
                    continue
                # Non-quota error — also try next, but record the cause
                continue

        # All providers failed
        why = "; ".join(f"{n}: {m}" for n, m in attempted) or "no providers responded"
        self.last = _Status(status="all_providers_failed", message=why, provider=None)
        return None

    # ----- Public surface (matches GeminiClient/GroqClient) -----
    def rewrite_query(self, query: str) -> _RQ:
        out = self._try_call("rewrite_query", query)
        if isinstance(out, _RQ):
            return out
        # graceful fallback — no rewrite
        return _RQ(expanded=query, material=None, application=None, spec_type=None)

    def hyde_passage(self, query: str) -> str | None:
        return self._try_call("hyde_passage", query)

    def multi_query_variants(self, query: str, n: int = 3) -> list[str]:
        return self._try_call("multi_query_variants", query, n) or []

    def generate_rationales(self, query: str, standards: list[dict]) -> list[dict]:
        return self._try_call("generate_rationales", query, standards) or []

    def generate_eval_query(self, standard: dict) -> str | None:
        return self._try_call("generate_eval_query", standard)


def _is_empty(method_name: str, result: Any) -> bool:
    """Each method has a different empty-result signature."""
    if method_name == "rewrite_query":
        # When the underlying client fails to call the LLM, GeminiClient/GroqClient
        # both fall back to RewrittenQuery(expanded=input_query, material=None,
        # application=None, spec_type=None). That looks superficially populated
        # but contains no real LLM output — treat as empty so the wrapper can
        # try the next provider.
        if not result:
            return True
        m = getattr(result, "material", None)
        a = getattr(result, "application", None)
        s = getattr(result, "spec_type", None)
        return not (m or a or s)
    if method_name == "hyde_passage":
        return not result or not isinstance(result, str) or not result.strip()
    if method_name == "multi_query_variants":
        return not isinstance(result, list) or len(result) == 0
    if method_name == "generate_rationales":
        return not isinstance(result, list) or len(result) == 0
    if method_name == "generate_eval_query":
        return not result or not isinstance(result, str) or not result.strip()
    return result is None
