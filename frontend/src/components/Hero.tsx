"use client";

import { motion } from "framer-motion";

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-border">
      <div className="absolute inset-0 bg-grid pointer-events-none" />
      <div className="absolute -top-40 left-1/2 -translate-x-1/2 h-[420px] w-[820px] rounded-full bg-accent/10 blur-3xl pointer-events-none" />
      <div className="absolute top-20 right-[10%] h-72 w-72 rounded-full bg-accent-2/15 blur-3xl pointer-events-none" />

      <div className="relative max-w-5xl mx-auto px-6 pt-20 pb-12 sm:pt-28 sm:pb-16">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="inline-flex items-center gap-2 rounded-full border border-border bg-muted/40 px-3 py-1 text-xs text-muted-foreground"
        >
          <span className="size-1.5 rounded-full bg-accent animate-pulse" />
          BIS SP 21 · 559 standards indexed · cement · steel · concrete · aggregates
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.05, ease: "easeOut" }}
          className="mt-6 text-4xl sm:text-6xl font-semibold tracking-tight leading-[1.05]"
        >
          Find your{" "}
          <span className="bg-gradient-to-r from-accent via-amber-300 to-accent-2 bg-clip-text text-transparent">
            Indian Standard
          </span>
          <br />
          in seconds, not weeks.
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.15, ease: "easeOut" }}
          className="mt-5 max-w-2xl text-base sm:text-lg text-muted-foreground leading-relaxed"
        >
          Describe your building-material product in plain English. Our hybrid RAG engine
          (BM25 + bge-m3 dense + cross-encoder rerank) returns the top BIS standards with
          grounded rationale — typically under half a second.
        </motion.p>
      </div>
    </section>
  );
}
