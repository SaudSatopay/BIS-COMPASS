"use client";

import { motion } from "framer-motion";
import { Hit } from "@/lib/api";
import { CheckCircle2, AlertTriangle, ShieldCheck, CircleDot } from "lucide-react";

type ConfidenceBand = "high" | "medium" | "low";
const CONFIDENCE_META: Record<ConfidenceBand, { label: string; color: string; icon: React.ElementType }> = {
  high:   { label: "High confidence",   color: "text-emerald-400 border-emerald-400/30 bg-emerald-400/[0.06]", icon: ShieldCheck },
  medium: { label: "Medium confidence", color: "text-amber-300  border-amber-300/30  bg-amber-300/[0.06]",  icon: CircleDot },
  low:    { label: "Low confidence",    color: "text-rose-300   border-rose-300/30   bg-rose-300/[0.06]",   icon: AlertTriangle },
};

export function ResultsList({
  hits,
  onOpen,
}: {
  hits: Hit[];
  onOpen?: (isCode: string) => void;
}) {
  if (!hits.length)
    return (
      <div className="rounded-xl border border-border bg-muted/20 px-5 py-10 text-center text-muted-foreground">
        No matching standards found. Try rewording your query.
      </div>
    );

  return (
    <ol className="space-y-3">
      {hits.map((h, i) => (
        <motion.li
          key={h.is_code + i}
          initial={{ opacity: 0, y: 14, scale: 0.99 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.45, delay: i * 0.06, ease: [0.22, 1, 0.36, 1] }}
          whileHover={{ y: -2 }}
          onMouseMove={(e) => {
            const t = e.currentTarget;
            const r = t.getBoundingClientRect();
            t.style.setProperty("--mx", `${e.clientX - r.left}px`);
            t.style.setProperty("--my", `${e.clientY - r.top}px`);
          }}
          className="group relative rounded-xl border border-border bg-muted/20 p-5 hover:border-accent/40 transition overflow-hidden cursor-pointer"
          style={{
            backgroundImage:
              "radial-gradient(420px circle at var(--mx,50%) var(--my,50%), rgb(250 145 90 / 0.06), transparent 50%)",
          }}
          onClick={() => onOpen?.(h.is_code)}
        >
          <div className="absolute left-0 top-0 h-full w-1 rounded-l-xl bg-gradient-to-b from-accent to-accent-2 opacity-0 group-hover:opacity-100 transition" />
          <div className="flex items-start gap-4">
            <div className="flex flex-col items-center pt-1">
              <span className="inline-flex size-8 items-center justify-center rounded-lg bg-background border border-border font-mono text-sm tabular-nums">
                {h.rank}
              </span>
              <div className="mt-2 text-[10px] uppercase tracking-wider text-muted-foreground/70">
                Score
              </div>
              <div className="mt-1 font-mono text-sm text-accent tabular-nums">
                {(h.rerank_score * 100).toFixed(0)}%
              </div>
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="font-mono text-base font-semibold tracking-tight">
                  {h.is_code}
                </span>
                <span className="text-xs px-2 py-0.5 rounded-md bg-background border border-border text-muted-foreground uppercase tracking-wider">
                  Specification
                </span>
                {(() => {
                  // Defensive: tolerate older backends that don't return
                  // `confidence` — fall back to deriving it from rerank_score
                  // using the same calibrated thresholds as the API.
                  const conf =
                    h.confidence ??
                    (h.rerank_score >= 0.55 ? "high" : h.rerank_score >= 0.40 ? "medium" : "low");
                  const meta = CONFIDENCE_META[conf] ?? CONFIDENCE_META.medium;
                  const Icon = meta.icon;
                  return (
                    <span
                      className={`inline-flex items-center gap-1.5 text-[11px] px-2 py-0.5 rounded-md border uppercase tracking-wider ${meta.color}`}
                      title={`Rerank score: ${(h.rerank_score * 100).toFixed(1)}%`}
                    >
                      <Icon className="size-3" />
                      {meta.label}
                    </span>
                  );
                })()}
              </div>
              <h3 className="mt-1 text-base sm:text-lg font-medium leading-snug">
                {h.title}
              </h3>
              {h.scope && (
                <p className="mt-2 text-sm text-muted-foreground leading-relaxed line-clamp-3">
                  {h.scope}
                </p>
              )}

              {h.rationale && (
                <div className="mt-3 flex gap-2.5 rounded-lg border border-accent/20 bg-accent/[0.04] px-3.5 py-2.5">
                  <CheckCircle2 className="size-4 text-accent flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="text-[11px] uppercase tracking-wider font-medium text-accent mb-0.5">
                      Why this applies
                    </div>
                    <p className="text-sm leading-relaxed">{h.rationale}</p>
                  </div>
                </div>
              )}

              {(h.related_standards ?? []).length > 0 && (
                <div className="mt-3">
                  <div className="text-[11px] uppercase tracking-wider text-muted-foreground/70 mb-1.5">
                    Related standards (cited in body)
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {(h.related_standards ?? []).map((rc) => (
                      <button
                        key={rc}
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpen?.(rc);
                        }}
                        className="font-mono text-[11px] rounded-md bg-background border border-border px-2 py-0.5 text-muted-foreground hover:border-accent/40 hover:text-foreground transition"
                      >
                        {rc}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.li>
      ))}
    </ol>
  );
}
