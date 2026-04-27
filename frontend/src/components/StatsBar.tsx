"use client";

import { motion } from "framer-motion";

const STATS = [
  { label: "Hit Rate @3", value: "100%", note: "target > 80%" },
  { label: "MRR @5", value: "0.93", note: "target > 0.7" },
  { label: "Avg latency", value: "<1s", note: "target < 5s · GPU" },
  { label: "Standards indexed", value: "559", note: "BIS SP 21" },
];

export function StatsBar() {
  return (
    <section className="max-w-5xl mx-auto px-6 mt-16 sm:mt-20">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {STATS.map((s, i) => (
          <motion.div
            key={s.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.5 + i * 0.07, ease: "easeOut" }}
            className="rounded-xl border border-border bg-muted/20 p-4"
          >
            <div className="text-xs uppercase tracking-wider text-muted-foreground">
              {s.label}
            </div>
            <div className="mt-1 text-2xl sm:text-3xl font-semibold tabular-nums">
              {s.value}
            </div>
            <div className="mt-0.5 text-[11px] text-muted-foreground/70 font-mono">
              {s.note}
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
