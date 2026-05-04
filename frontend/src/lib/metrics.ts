/**
 * Eval Sandbox metrics — mirrors the math in `eval_script.py` exactly so
 * the numbers we display in-browser match what judges will see when they
 * run `python eval_script.py --results results.json` on the downloaded
 * output.
 *
 * Keep this file in lock-step with eval_script.py. If the rulebook ever
 * changes the formulas, update both.
 */

export type EvalRecord = {
  id: string;
  query: string;
  expected_standards?: string[];
  retrieved_standards: string[];
  latency_seconds: number;
};

/** Whitespace-stripped, lowercased — same as eval_script.normalize_std. */
function normalize(s: string): string {
  return String(s).replace(/\s+/g, "").toLowerCase();
}

function withExpected(records: EvalRecord[]): EvalRecord[] {
  return records.filter(
    (r) => Array.isArray(r.expected_standards) && r.expected_standards.length > 0,
  );
}

/**
 * Hit Rate @3, expressed as a percentage 0–100.
 * Returns null if no record has expected_standards (nothing to score).
 */
export function hitAt3(records: EvalRecord[]): number | null {
  const scored = withExpected(records);
  if (scored.length === 0) return null;
  let hits = 0;
  for (const r of scored) {
    const expected = new Set((r.expected_standards || []).map(normalize));
    const top3 = (r.retrieved_standards || []).slice(0, 3).map(normalize);
    if (top3.some((s) => expected.has(s))) hits++;
  }
  return (hits / scored.length) * 100;
}

/**
 * Mean Reciprocal Rank @5. Returns null if no record has expected_standards.
 */
export function mrrAt5(records: EvalRecord[]): number | null {
  const scored = withExpected(records);
  if (scored.length === 0) return null;
  let sum = 0;
  for (const r of scored) {
    const expected = new Set((r.expected_standards || []).map(normalize));
    const top5 = (r.retrieved_standards || []).slice(0, 5).map(normalize);
    let mrr = 0;
    for (let rank = 0; rank < top5.length; rank++) {
      if (expected.has(top5[rank])) {
        mrr = 1 / (rank + 1);
        break;
      }
    }
    sum += mrr;
  }
  return sum / scored.length;
}

/**
 * Average latency in seconds. Computed over ALL records (matches
 * eval_script.py — denominator is total queries, not just scored ones).
 */
export function avgLatency(records: EvalRecord[]): number {
  if (records.length === 0) return 0;
  let total = 0;
  for (const r of records) total += r.latency_seconds || 0;
  return total / records.length;
}

/** Number of records that have non-empty expected_standards. */
export function countWithExpected(records: EvalRecord[]): number {
  return withExpected(records).length;
}
