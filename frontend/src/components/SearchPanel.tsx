"use client";

import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Sparkles, Zap, Loader2 } from "lucide-react";
import { useState, useTransition, useRef } from "react";
import { search, type SearchResponse, SAMPLE_QUERIES } from "@/lib/api";
import { ResultsList } from "./ResultsList";
import { StandardModal } from "./StandardModal";
import { cn } from "@/lib/cn";

export function SearchPanel() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [openCode, setOpenCode] = useState<string | null>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  const submit = (q?: string) => {
    const text = (q ?? query).trim();
    if (!text || isPending) return;
    setQuery(text);
    setError(null);
    setResponse(null);
    startTransition(async () => {
      try {
        const r = await search(text);
        setResponse(r);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Unknown error");
      }
    });
  };

  return (
    <section className="max-w-5xl mx-auto px-6 -mt-4 sm:mt-0">
      <motion.form
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.25, ease: "easeOut" }}
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="relative rounded-2xl border border-border bg-muted/30 backdrop-blur-sm shadow-2xl shadow-black/30"
      >
        <div className="absolute -inset-px rounded-2xl pointer-events-none opacity-60 bg-gradient-to-r from-accent/0 via-accent/30 to-accent-2/0 blur-md" />
        <div className="relative">
          <textarea
            ref={taRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                submit();
              }
            }}
            rows={3}
            placeholder="Describe your product — e.g. 'We manufacture hollow lightweight concrete masonry blocks for partition walls.'"
            className="w-full resize-none bg-transparent px-5 py-5 text-base sm:text-lg outline-none placeholder:text-muted-foreground/60"
          />
          <div className="flex items-center justify-between gap-3 px-3 pb-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground pl-2">
              <kbd className="rounded border border-border bg-background px-1.5 py-0.5 font-mono">⌘</kbd>
              <kbd className="rounded border border-border bg-background px-1.5 py-0.5 font-mono">↵</kbd>
              <span>to search</span>
            </div>
            <button
              type="submit"
              disabled={isPending || !query.trim()}
              className={cn(
                "group relative inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium",
                "bg-gradient-to-r from-accent to-accent-2 text-black",
                "hover:opacity-95 active:scale-[0.98] transition",
                "disabled:opacity-50 disabled:cursor-not-allowed",
              )}
            >
              {isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Sparkles className="size-4" />
              )}
              {isPending ? "Searching" : "Find standards"}
              <ArrowRight className="size-4 transition group-hover:translate-x-0.5" />
            </button>
          </div>
        </div>
      </motion.form>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.4 }}
        className="mt-4 flex flex-wrap gap-2 px-1"
      >
        <span className="text-xs text-muted-foreground self-center mr-1">Try:</span>
        {SAMPLE_QUERIES.slice(0, 4).map((q, i) => (
          <button
            key={i}
            onClick={() => {
              setQuery(q);
              submit(q);
            }}
            className="text-xs rounded-full border border-border bg-muted/40 px-3 py-1.5 hover:bg-muted hover:border-accent/50 transition"
          >
            {q.length > 70 ? q.slice(0, 67) + "…" : q}
          </button>
        ))}
      </motion.div>

      <AnimatePresence mode="wait">
        {error && (
          <motion.div
            key="err"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="mt-8 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm"
          >
            <div className="font-medium text-red-300">Search failed</div>
            <div className="text-red-300/80 mt-1 font-mono text-xs">{error}</div>
            <div className="text-muted-foreground mt-2">
              Make sure the FastAPI backend is running: <code className="font-mono">python -m src.api.main</code>
            </div>
          </motion.div>
        )}
        {response && !error && (
          <motion.div
            key="resp"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="mt-10"
          >
            <div className="flex flex-wrap items-baseline gap-3 mb-5">
              <h2 className="text-lg font-medium">Top {response.hits.length} BIS standards</h2>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-muted/60 border border-border px-2.5 py-1 text-xs text-muted-foreground">
                <Zap className="size-3 text-accent" />
                {response.latency_seconds.toFixed(2)}s
              </span>
              {response.used_gemini && (
                <span className="rounded-full bg-accent/10 border border-accent/30 px-2.5 py-1 text-xs text-accent">
                  AI rewrite + rationale
                </span>
              )}
              {response.material && (
                <span className="rounded-full bg-muted/60 border border-border px-2.5 py-1 text-xs text-muted-foreground capitalize">
                  {response.material}
                </span>
              )}
            </div>
            {response.gemini_status && response.gemini_status !== "ok" && !response.used_gemini && (
              <div className="mb-6 rounded-xl border border-amber-300/30 bg-amber-300/[0.06] px-4 py-3 text-sm">
                <div className="text-amber-300 font-medium mb-1">
                  AI rationale unavailable
                  <span className="ml-2 text-[10px] uppercase tracking-wider font-mono text-amber-300/70">
                    {response.gemini_status}
                  </span>
                </div>
                <div className="text-muted-foreground text-xs leading-relaxed">
                  {response.gemini_message ||
                    "Gemini call did not succeed. Retrieval results below are unaffected."}
                </div>
              </div>
            )}
            {response.expanded_query && (
              <div className="mb-6 rounded-xl border border-border bg-muted/20 p-4 text-sm text-muted-foreground">
                <div className="text-xs font-mono uppercase tracking-wider text-accent mb-2">
                  Expanded query
                </div>
                {response.expanded_query}
              </div>
            )}
            <ResultsList hits={response.hits} onOpen={setOpenCode} />
          </motion.div>
        )}
      </AnimatePresence>
      <StandardModal
        isCode={openCode}
        onClose={() => setOpenCode(null)}
        onOpen={setOpenCode}
      />
    </section>
  );
}
