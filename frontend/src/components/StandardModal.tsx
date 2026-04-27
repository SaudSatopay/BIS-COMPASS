"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, FileText, Tag, BookOpen, ExternalLink } from "lucide-react";
import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

type StandardDetail = {
  is_code: string;
  title: string;
  scope: string;
  revision: string | null;
  page_start: number;
  page_end: number;
  full_text: string;
  related_standards: string[];
  categories: string[];
};

export function StandardModal({ isCode, onClose, onOpen }: {
  isCode: string | null;
  onClose: () => void;
  onOpen: (code: string) => void;
}) {
  const [data, setData] = useState<StandardDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isCode) {
      setData(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);
    fetch(`${API_BASE}/standards/${encodeURIComponent(isCode)}`)
      .then(async (r) => {
        if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
        return r.json();
      })
      .then((j: StandardDetail) => {
        if (!cancelled) setData(j);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isCode]);

  // Esc-to-close
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isCode) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isCode, onClose]);

  return (
    <AnimatePresence>
      {isCode && (
        <motion.div
          key="overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            key="dialog"
            initial={{ opacity: 0, y: 24, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.98 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            onClick={(e) => e.stopPropagation()}
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[min(880px,92vw)] max-h-[88vh] flex flex-col rounded-2xl border border-border bg-muted/40 backdrop-blur-md shadow-2xl shadow-black/40 overflow-hidden"
          >
            <div className="flex items-start justify-between gap-4 px-6 py-5 border-b border-border">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-mono text-lg font-semibold tracking-tight">
                    {isCode}
                  </span>
                  {data?.revision && (
                    <span className="text-xs px-2 py-0.5 rounded-md bg-background border border-border text-muted-foreground">
                      {data.revision}
                    </span>
                  )}
                  {data?.categories && data.categories.length > 0 && (
                    <div className="flex gap-1 flex-wrap">
                      {data.categories.map((c) => (
                        <span
                          key={c}
                          className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-accent/10 text-accent border border-accent/30"
                        >
                          <Tag className="size-2.5" />
                          {c}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                {data && (
                  <h3 className="mt-1 text-base sm:text-lg font-medium leading-snug">
                    {data.title}
                  </h3>
                )}
              </div>
              <button
                onClick={onClose}
                className="flex-shrink-0 size-8 rounded-lg flex items-center justify-center hover:bg-background/60 transition"
                aria-label="Close"
              >
                <X className="size-4" />
              </button>
            </div>

            <div className="flex-1 overflow-auto px-6 py-5 space-y-5">
              {loading && (
                <div className="text-sm text-muted-foreground py-12 text-center">
                  Loading standard...
                </div>
              )}
              {error && (
                <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm">
                  <div className="font-medium text-red-300">Failed to load</div>
                  <div className="text-red-300/80 mt-1 font-mono text-xs">{error}</div>
                </div>
              )}
              {data && (
                <>
                  <section>
                    <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-accent mb-2">
                      <BookOpen className="size-3" />
                      Scope
                    </div>
                    <p className="text-sm leading-relaxed text-foreground/95">
                      {data.scope || <span className="text-muted-foreground italic">No scope summary extracted.</span>}
                    </p>
                  </section>

                  <section>
                    <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-accent mb-2">
                      <FileText className="size-3" />
                      Source · SP 21 page {data.page_start}
                      {data.page_end !== data.page_start ? `–${data.page_end}` : ""}
                    </div>
                    <pre className="text-[12px] leading-relaxed font-mono whitespace-pre-wrap text-foreground/85 max-h-[320px] overflow-auto rounded-lg border border-border bg-background/40 p-4">
                      {data.full_text.slice(0, 4000)}
                      {data.full_text.length > 4000 && "\n\n…"}
                    </pre>
                  </section>

                  {data.related_standards.length > 0 && (
                    <section>
                      <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-accent mb-2">
                        <ExternalLink className="size-3" />
                        Cross-referenced standards
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {data.related_standards.map((r) => (
                          <button
                            key={r}
                            onClick={() => onOpen(r)}
                            className="font-mono text-xs rounded-md bg-background border border-border px-2.5 py-1 text-foreground/90 hover:border-accent/50 hover:text-accent transition"
                          >
                            {r}
                          </button>
                        ))}
                      </div>
                    </section>
                  )}
                </>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
