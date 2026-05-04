"use client";

/**
 * EvalPanel — collapsible "Eval Sandbox" card on the main page.
 *
 * Lets a judge (or anyone) drop a private_dataset.json file in, runs every
 * query through the offline pipeline via /judge_search (NO LLM, parity with
 * inference.py), then displays Hit@3 / MRR@5 / Avg Latency at the end and
 * offers a results.json download that's drop-in compatible with
 * `python eval_script.py --results results.json`.
 *
 * Important: this panel intentionally does NOT use the demo /search endpoint
 * (which has Gemini rewriting / rationales). The metrics shown here MUST
 * match what `python inference.py` would produce on the same input — that's
 * the point.
 */

import { motion, AnimatePresence } from "framer-motion";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  Download,
  FileCheck2,
  FileJson,
  Loader2,
  Play,
  Upload,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import {
  avgLatency,
  countWithExpected,
  hitAt3,
  mrrAt5,
  type EvalRecord,
} from "@/lib/metrics";

type InputItem = { id: string; query: string; expected_standards?: string[] };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

// Soft cap — we'll still run, just nudge the user.
const SOFT_LIMIT = 200;

export function EvalPanel() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<InputItem[] | null>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [results, setResults] = useState<EvalRecord[] | null>(null);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Abort the in-flight /judge_search loop if the user navigates away or
  // collapses the panel mid-run. Without this the for-loop in `run()`
  // keeps firing requests after unmount.
  useEffect(() => () => abortRef.current?.abort(), []);

  const reset = () => {
    setItems(null);
    setFilename(null);
    setParseError(null);
    setResults(null);
    setRuntimeError(null);
    setProgress({ done: 0, total: 0 });
  };

  const loadFile = (file: File) => {
    setParseError(null);
    setResults(null);
    setRuntimeError(null);
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const text = String(reader.result || "");
        const data = JSON.parse(text);
        if (!Array.isArray(data)) {
          throw new Error("Expected a JSON array at the root.");
        }
        if (data.length === 0) {
          throw new Error("Array is empty — no queries to run.");
        }
        const cleaned: InputItem[] = [];
        for (let i = 0; i < data.length; i++) {
          const it = data[i] as unknown;
          if (typeof it !== "object" || it === null) {
            throw new Error(`Item ${i}: expected an object.`);
          }
          const obj = it as Record<string, unknown>;
          if (typeof obj.id !== "string" && typeof obj.id !== "number") {
            throw new Error(`Item ${i}: missing or invalid 'id'.`);
          }
          if (typeof obj.query !== "string" || obj.query.trim() === "") {
            throw new Error(`Item ${i}: missing or empty 'query'.`);
          }
          const exp = Array.isArray(obj.expected_standards)
            ? (obj.expected_standards as unknown[]).filter(
                (s): s is string => typeof s === "string",
              )
            : undefined;
          cleaned.push({
            id: String(obj.id),
            query: obj.query,
            expected_standards: exp,
          });
        }
        setItems(cleaned);
        setFilename(file.name);
      } catch (e: unknown) {
        setParseError(e instanceof Error ? e.message : String(e));
        setItems(null);
        setFilename(null);
      }
    };
    reader.onerror = () => setParseError("Could not read file.");
    reader.readAsText(file);
  };

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) loadFile(f);
  };

  const onDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const run = useCallback(async () => {
    if (!items || running) return;
    setRunning(true);
    setRuntimeError(null);
    setResults(null);
    setProgress({ done: 0, total: items.length });
    const out: EvalRecord[] = [];
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        try {
          const res = await fetch(`${API_BASE}/judge_search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: item.query }),
            cache: "no-store",
            signal: ctrl.signal,
          });
          if (!res.ok) {
            const txt = await res.text();
            throw new Error(`${res.status}: ${txt.slice(0, 200)}`);
          }
          const json = (await res.json()) as {
            retrieved_standards: string[];
            latency_seconds: number;
          };
          out.push({
            id: item.id,
            query: item.query,
            expected_standards: item.expected_standards,
            retrieved_standards: json.retrieved_standards,
            latency_seconds: json.latency_seconds,
          });
        } catch (e: unknown) {
          // Bubble cancellations; otherwise mirror inference.py behaviour:
          // empty retrieval + zero latency, keep running the batch.
          if ((e as { name?: string })?.name === "AbortError") throw e;
          out.push({
            id: item.id,
            query: item.query,
            expected_standards: item.expected_standards,
            retrieved_standards: [],
            latency_seconds: 0,
          });
        }
        setProgress({ done: i + 1, total: items.length });
      }
      setResults(out);
    } catch (e: unknown) {
      const name = (e as { name?: string })?.name;
      if (name !== "AbortError") {
        setRuntimeError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }, [items, running]);

  const cancel = () => {
    abortRef.current?.abort();
  };

  const download = () => {
    if (!results) return;
    const blob = new Blob([JSON.stringify(results, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "results.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const expectedCount = items ? countWithExpected(items as EvalRecord[]) : 0;
  const hr = results ? hitAt3(results) : null;
  const mrr = results ? mrrAt5(results) : null;
  const avgL = results ? avgLatency(results) : 0;
  const scoredCount = results ? countWithExpected(results) : 0;
  const overSoftLimit = items && items.length > SOFT_LIMIT;

  return (
    <section className="max-w-5xl mx-auto px-6 mt-16 sm:mt-20" id="eval">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
        className="rounded-2xl border border-border bg-muted/20 backdrop-blur-sm overflow-hidden"
      >
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left hover:bg-muted/30 transition"
          aria-expanded={open}
          aria-controls="eval-panel-body"
        >
          <div className="flex items-center gap-3 min-w-0">
            <FileCheck2 className="size-5 text-accent shrink-0" />
            <div className="min-w-0">
              <div className="text-[15px] font-semibold tracking-tight">
                Eval Sandbox
              </div>
              <div className="text-xs text-muted-foreground mt-0.5 truncate">
                Drop your private_dataset.json — runs the offline pipeline,
                shows Hit@3 / MRR@5 / Avg Latency
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="hidden sm:inline rounded-full bg-muted/60 border border-border px-2.5 py-1 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
              For judges
            </span>
            <ChevronDown
              className={cn(
                "size-5 text-muted-foreground transition-transform",
                open && "rotate-180",
              )}
            />
          </div>
        </button>

        <AnimatePresence initial={false}>
          {open && (
            <motion.div
              key="body"
              id="eval-panel-body"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3, ease: "easeOut" }}
              className="overflow-hidden border-t border-border"
            >
              <div className="p-5 sm:p-6 space-y-5">
                {/* Drop zone / file picker */}
                <div
                  onDrop={onDrop}
                  onDragOver={onDragOver}
                  onClick={() => fileInputRef.current?.click()}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      fileInputRef.current?.click();
                    }
                  }}
                  className={cn(
                    "rounded-xl border-2 border-dashed p-6 text-center transition cursor-pointer",
                    "hover:border-accent/50 hover:bg-accent/[0.03]",
                    parseError
                      ? "border-red-500/40 bg-red-500/5"
                      : items
                      ? "border-emerald-500/40 bg-emerald-500/[0.04]"
                      : "border-border bg-muted/20",
                  )}
                  role="button"
                  tabIndex={0}
                  aria-label="Upload private_dataset.json"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".json,application/json"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) loadFile(f);
                      // Reset so the same file can be re-selected after Reset
                      e.target.value = "";
                    }}
                    className="hidden"
                  />
                  <Upload
                    className={cn(
                      "mx-auto size-7",
                      items ? "text-emerald-400" : "text-muted-foreground",
                    )}
                  />
                  <div className="mt-3 text-sm">
                    {filename ? (
                      <span className="inline-flex items-center gap-1.5">
                        <FileJson className="size-4 text-accent" />
                        <span className="font-mono">{filename}</span>
                      </span>
                    ) : (
                      <span>
                        Drop{" "}
                        <span className="font-mono text-foreground/90">
                          private_dataset.json
                        </span>{" "}
                        here, or click to browse
                      </span>
                    )}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    Schema: array of{" "}
                    <span className="font-mono">
                      {"{ id, query, expected_standards? }"}
                    </span>
                  </div>
                </div>

                {parseError && (
                  <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm">
                    <div className="flex items-center gap-2 text-red-300 font-medium">
                      <AlertCircle className="size-4" /> Could not parse file
                    </div>
                    <div className="text-red-300/80 mt-1 font-mono text-xs break-words">
                      {parseError}
                    </div>
                  </div>
                )}

                {items && !parseError && (
                  <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/[0.06] px-4 py-3 text-sm">
                    <div className="flex items-center gap-2 text-emerald-300 font-medium">
                      <CheckCircle2 className="size-4" />
                      {items.length}{" "}
                      {items.length === 1 ? "query" : "queries"} detected
                    </div>
                    <div className="text-muted-foreground mt-1 text-xs leading-relaxed">
                      {expectedCount === items.length
                        ? "All have expected_standards — Hit@3 and MRR@5 will be computed."
                        : expectedCount > 0
                        ? `${expectedCount} of ${items.length} have expected_standards (metrics computed on those).`
                        : "No expected_standards found — only avg latency will be computed."}
                    </div>
                    {overSoftLimit && (
                      <div className="text-amber-300/80 mt-2 text-xs">
                        Heads up: {items.length} queries will take a few
                        minutes. You can cancel mid-run.
                      </div>
                    )}
                  </div>
                )}

                {/* Run / cancel controls */}
                <div className="flex flex-wrap items-center gap-3">
                  {!running ? (
                    <button
                      type="button"
                      onClick={run}
                      disabled={!items || !!parseError}
                      className={cn(
                        "inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium",
                        "bg-gradient-to-r from-accent to-accent-2 text-black",
                        "hover:opacity-95 active:scale-[0.98] transition",
                        "disabled:opacity-40 disabled:cursor-not-allowed",
                      )}
                    >
                      <Play className="size-4" />
                      Run evaluation
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={cancel}
                      className="inline-flex items-center gap-2 rounded-xl border border-border bg-muted/40 px-4 py-2.5 text-sm font-medium hover:bg-muted/60 transition"
                    >
                      <Loader2 className="size-4 animate-spin" />
                      Cancel
                    </button>
                  )}

                  {items && !running && (results || parseError === null) && (
                    <button
                      type="button"
                      onClick={reset}
                      className="text-xs text-muted-foreground hover:text-foreground transition"
                    >
                      Reset
                    </button>
                  )}
                </div>

                {/* Progress */}
                {running && (
                  <div>
                    <div className="flex items-center justify-between text-xs mb-2">
                      <span className="font-mono text-muted-foreground">
                        Processing {progress.done} / {progress.total}
                      </span>
                      <span className="font-mono text-muted-foreground">
                        {progress.total > 0
                          ? Math.round(
                              (progress.done / progress.total) * 100,
                            )
                          : 0}
                        %
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-accent to-accent-2 transition-all"
                        style={{
                          width:
                            progress.total > 0
                              ? `${
                                  (progress.done / progress.total) * 100
                                }%`
                              : "0%",
                        }}
                      />
                    </div>
                  </div>
                )}

                {runtimeError && (
                  <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm">
                    <div className="flex items-center gap-2 text-red-300 font-medium">
                      <AlertCircle className="size-4" /> Run failed
                    </div>
                    <div className="text-red-300/80 mt-1 font-mono text-xs break-words">
                      {runtimeError}
                    </div>
                    <div className="text-muted-foreground mt-2 text-xs">
                      Make sure the FastAPI backend is running:{" "}
                      <code className="font-mono">
                        python -m src.api.main
                      </code>
                    </div>
                  </div>
                )}

                {results && !runtimeError && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, ease: "easeOut" }}
                    className="space-y-4"
                  >
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <MetricCard
                        label="Hit Rate @3"
                        value={hr === null ? "—" : `${hr.toFixed(2)}%`}
                        target="target > 80%"
                        good={hr !== null && hr > 80}
                        bad={hr !== null && hr <= 80}
                        muted={hr === null}
                      />
                      <MetricCard
                        label="MRR @5"
                        value={mrr === null ? "—" : mrr.toFixed(4)}
                        target="target > 0.7"
                        good={mrr !== null && mrr > 0.7}
                        bad={mrr !== null && mrr <= 0.7}
                        muted={mrr === null}
                      />
                      <MetricCard
                        label="Avg Latency"
                        value={`${avgL.toFixed(2)} s`}
                        target="target < 5 s"
                        good={avgL < 5}
                        bad={avgL >= 5}
                      />
                    </div>

                    {scoredCount < results.length && scoredCount > 0 && (
                      <div className="text-xs text-muted-foreground">
                        Hit@3 / MRR@5 computed on {scoredCount} of{" "}
                        {results.length} queries with expected_standards.
                      </div>
                    )}

                    <div className="flex flex-wrap items-center gap-3 pt-1">
                      <button
                        type="button"
                        onClick={download}
                        className="inline-flex items-center gap-2 rounded-xl border border-border bg-muted/40 px-3.5 py-2 text-sm hover:bg-muted/60 hover:border-accent/40 transition"
                      >
                        <Download className="size-4" />
                        Download results.json
                      </button>
                      <span className="text-xs text-muted-foreground font-mono break-all">
                        Verify:{" "}
                        <span className="text-foreground/80">
                          python eval_script.py --results results.json
                        </span>
                      </span>
                    </div>
                  </motion.div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </section>
  );
}

function MetricCard({
  label,
  value,
  target,
  good,
  bad,
  muted,
}: {
  label: string;
  value: string;
  target: string;
  good?: boolean;
  bad?: boolean;
  muted?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border p-4",
        muted
          ? "border-border bg-muted/20"
          : good
          ? "border-emerald-500/30 bg-emerald-500/[0.05]"
          : bad
          ? "border-amber-400/30 bg-amber-400/[0.05]"
          : "border-border bg-muted/20",
      )}
    >
      <div className="text-xs uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div
        className={cn(
          "mt-1 text-2xl sm:text-3xl font-semibold tabular-nums",
          good && "text-emerald-300",
          bad && "text-amber-300",
        )}
      >
        {value}
      </div>
      <div className="mt-0.5 text-[11px] text-muted-foreground/70 font-mono">
        {target}
      </div>
    </div>
  );
}
