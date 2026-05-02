export type Hit = {
  rank: number;
  is_code: string;
  title: string;
  scope: string;
  rerank_score: number;
  rrf_score: number;
  // The fields below are tolerant of older / partial backend responses —
  // ResultsList renders sensible defaults when they're missing.
  rationale?: string | null;
  confidence?: "high" | "medium" | "low";
  related_standards?: string[];
  categories?: string[];
};

export type SearchResponse = {
  query: string;
  expanded_query: string | null;
  material: string | null;
  application: string | null;
  hits: Hit[];
  latency_seconds: number;
  used_gemini: boolean;
  gemini_status?: "ok" | "rate_limited" | "disabled" | "error";
  gemini_message?: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

// localStorage keys for browser-stored LLM keys (set via the welcome modal)
export const GEMINI_LS_KEY = "bisCompass.geminiKey";
export const GROQ_LS_KEY = "bisCompass.groqKey";
export const KEY_SETUP_DONE = "bisCompass.keySetupDone";

function readBrowserKeys(): { gemini: string | null; groq: string | null } {
  if (typeof window === "undefined") return { gemini: null, groq: null };
  return {
    gemini: window.localStorage.getItem(GEMINI_LS_KEY) || null,
    groq: window.localStorage.getItem(GROQ_LS_KEY) || null,
  };
}

export async function search(
  query: string,
  opts: { rewrite?: boolean; rationales?: boolean; top_k?: number } = {},
): Promise<SearchResponse> {
  const keys = readBrowserKeys();
  // 60 s timeout: cold-cache backends can take ~30 s on first query.
  // Beyond that we'd rather show a clear error than spin forever.
  const res = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      rewrite: opts.rewrite ?? true,
      rationales: opts.rationales ?? true,
      top_k: opts.top_k ?? 5,
      gemini_api_key: keys.gemini,
      groq_api_key: keys.groq,
    }),
    cache: "no-store",
    signal: AbortSignal.timeout(60_000),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Search failed (${res.status}): ${text}`);
  }
  return res.json();
}

export type HealthInfo = {
  ok: boolean;
  llm_providers: string[];
  llm_primary: string | null;
  gemini: boolean;
};

/**
 * Probe the backend health endpoint. Retries 3× with linear backoff so a
 * cold-start backend (still loading models) doesn't trigger the
 * "no LLM providers" path in the welcome modal.
 *
 * Returns null only if all retries fail — meaning the backend is genuinely
 * unreachable, not just slow to start.
 */
export async function health(): Promise<HealthInfo | null> {
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await fetch(`${API_BASE}/health`, {
        cache: "no-store",
        signal: AbortSignal.timeout(5_000),
      });
      if (!res.ok) {
        if (attempt < 2) await new Promise(r => setTimeout(r, 1500 * (attempt + 1)));
        continue;
      }
      return await res.json();
    } catch {
      if (attempt < 2) await new Promise(r => setTimeout(r, 1500 * (attempt + 1)));
    }
  }
  return null;
}

export const SAMPLE_QUERIES = [
  "We are a small enterprise manufacturing 33 Grade Ordinary Portland Cement.",
  "Our company makes hollow lightweight concrete masonry blocks for non-load-bearing walls.",
  "What is the standard for precast concrete pipes used in water mains?",
  "Looking for the IS code on coarse and fine aggregates for structural concrete.",
  "We're producing corrugated asbestos cement roofing sheets.",
];
