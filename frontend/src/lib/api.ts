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

export async function search(
  query: string,
  opts: { rewrite?: boolean; rationales?: boolean; top_k?: number } = {},
): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      rewrite: opts.rewrite ?? true,
      rationales: opts.rationales ?? true,
      top_k: opts.top_k ?? 5,
    }),
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Search failed (${res.status}): ${text}`);
  }
  return res.json();
}

export const SAMPLE_QUERIES = [
  "We are a small enterprise manufacturing 33 Grade Ordinary Portland Cement.",
  "Our company makes hollow lightweight concrete masonry blocks for non-load-bearing walls.",
  "What is the standard for precast concrete pipes used in water mains?",
  "Looking for the IS code on coarse and fine aggregates for structural concrete.",
  "We're producing corrugated asbestos cement roofing sheets.",
];
