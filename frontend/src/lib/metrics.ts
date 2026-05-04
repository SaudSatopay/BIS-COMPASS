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
 *
 * Mirrors eval_script.py exactly: divides hits by **total queries**
 * (not just those with expected_standards), so a partially-labelled
 * test set displays the same percentage in this UI as `eval_script.py
 * --results <download>` would print on the CLI.
 *
 * Returns null only when there are zero records OR when not a single
 * record has expected_standards (in which case any number we return
 * would print as 0% and confuse a judge who'd misread that as
 * "system failed").
 */
export function hitAt3(records: EvalRecord[]): number | null {
  if (records.length === 0) return null;
  if (withExpected(records).length === 0) return null;
  let hits = 0;
  for (const r of records) {
    const expected = new Set((r.expected_standards || []).map(normalize));
    if (expected.size === 0) continue; // record contributes 0 to numerator
    const top3 = (r.retrieved_standards || []).slice(0, 3).map(normalize);
    if (top3.some((s) => expected.has(s))) hits++;
  }
  return (hits / records.length) * 100;
}

/**
 * Mean Reciprocal Rank @5. Same parity rule as hitAt3 — denominator is
 * total queries, matching eval_script.py.
 */
export function mrrAt5(records: EvalRecord[]): number | null {
  if (records.length === 0) return null;
  if (withExpected(records).length === 0) return null;
  let sum = 0;
  for (const r of records) {
    const expected = new Set((r.expected_standards || []).map(normalize));
    if (expected.size === 0) continue;
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
  return sum / records.length;
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
