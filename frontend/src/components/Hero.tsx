"use client";

import { motion } from "framer-motion";
import { ArrowDown, ArrowRight, Sparkles, PlayCircle } from "lucide-react";
import { useState } from "react";
import { ArchitectureModal } from "./ArchitectureModal";

const STATS = [
  { value: "100%", label: "Hit@3" },
  { value: "0.93", label: "MRR@5" },
  { value: "<1s", label: "latency" },
  { value: "559", label: "standards" },
];

export function Hero() {
  const [archOpen, setArchOpen] = useState(false);

  const scrollToSearch = () => {
    document.getElementById("search")?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  };

  return (
    <section className="relative min-h-[100svh] flex items-center justify-center overflow-hidden border-b border-border">
      {/* Atmosphere */}
      <div className="absolute inset-0 bg-grid pointer-events-none" />

      {/* Drifting glow orbs */}
      <motion.div
        aria-hidden
        animate={{ x: [0, 40, 0], y: [0, 25, 0] }}
        transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
        className="absolute -top-40 -left-40 h-[640px] w-[640px] rounded-full bg-accent/15 blur-3xl pointer-events-none"
      />
      <motion.div
        aria-hidden
        animate={{ x: [0, -30, 0], y: [0, -40, 0] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
        className="absolute -bottom-40 -right-40 h-[540px] w-[540px] rounded-full bg-accent-2/15 blur-3xl pointer-events-none"
      />

      {/* Content */}
      <div className="relative z-10 max-w-5xl mx-auto px-6 py-8 sm:py-10 text-center">
        {/* Eyebrow */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="inline-flex items-center gap-2 rounded-full border border-border bg-muted/40 backdrop-blur-md px-3.5 py-1.5 text-[11px] font-mono tracking-wider uppercase text-muted-foreground"
        >
          <span className="size-1.5 rounded-full bg-accent animate-pulse shadow-[0_0_8px_rgb(var(--accent))]" />
          BIS SP 21 · 559 Standards · Building Materials
        </motion.div>

        {/* Massive headline — display font, tight tracking, editorial accent */}
        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.08, ease: [0.16, 1, 0.3, 1] }}
          className="font-display mt-5 font-bold tracking-[-0.055em] leading-[0.88] text-balance"
          style={{ fontSize: "clamp(2.5rem, 8vw, 7rem)" }}
        >
          <span className="block text-foreground/95">Find your</span>
          <span className="block bg-gradient-to-br from-accent via-amber-300 to-accent-2 bg-clip-text text-transparent pb-1">
            Indian Standard
          </span>
          <span className="block text-foreground/90">
            in{" "}
            <span className="font-serif-italic font-normal text-foreground/95 tracking-normal">
              seconds
            </span>
            , not weeks.
          </span>
        </motion.h1>

        {/* Subhead */}
        <motion.p
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.18, ease: "easeOut" }}
          className="mt-5 max-w-2xl mx-auto text-sm sm:text-base text-muted-foreground leading-relaxed"
        >
          Describe your product in plain English. A hybrid RAG engine —{" "}
          <span className="text-foreground/80">BM25 + bge-m3 dense + cross-encoder rerank</span>{" "}
          — returns the top BIS standards with grounded rationale, in under a
          second.
        </motion.p>

        {/* Inline stat row */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.26, ease: "easeOut" }}
          className="mt-7 flex flex-wrap items-center justify-center gap-x-8 gap-y-3"
        >
          {STATS.map((s, i) => (
            <div key={s.label} className="flex items-baseline gap-2">
              <span className="text-xl sm:text-2xl font-semibold tabular-nums tracking-tight bg-gradient-to-r from-accent to-accent-2 bg-clip-text text-transparent">
                {s.value}
              </span>
              <span className="text-[11px] uppercase tracking-wider font-mono text-muted-foreground">
                {s.label}
              </span>
              {i < STATS.length - 1 && (
                <span className="hidden sm:inline ml-4 text-muted-foreground/40">·</span>
              )}
            </div>
          ))}
        </motion.div>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.36, ease: "easeOut" }}
          className="mt-8 flex flex-wrap gap-3 justify-center"
        >
          <button
            onClick={scrollToSearch}
            className="group relative inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-medium bg-gradient-to-r from-accent to-accent-2 text-black hover:opacity-95 active:scale-[0.98] transition shadow-lg shadow-accent/20"
          >
            <Sparkles className="size-4" />
            Try the demo
            <ArrowRight className="size-4 transition group-hover:translate-x-0.5" />
          </button>
          <motion.button
            onClick={() => setArchOpen(true)}
            animate={{
              boxShadow: [
                "0 0 0 0 rgba(250, 145, 90, 0)",
                "0 0 0 6px rgba(250, 145, 90, 0.10)",
                "0 0 0 0 rgba(250, 145, 90, 0)",
              ],
            }}
            transition={{
              duration: 2.6,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 1.2,
            }}
            className="group relative inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-medium border border-border bg-muted/30 backdrop-blur-md text-foreground/90 hover:bg-muted/60 hover:border-accent/50 transition"
          >
            <span className="relative flex items-center justify-center">
              <motion.span
                aria-hidden
                animate={{ scale: [1, 1.6, 1.6], opacity: [0.5, 0, 0] }}
                transition={{
                  duration: 2.6,
                  repeat: Infinity,
                  ease: "easeOut",
                  delay: 1.2,
                }}
                className="absolute inset-0 rounded-full bg-accent/40"
              />
              <PlayCircle className="relative size-4 opacity-80 transition group-hover:opacity-100 group-hover:text-accent" />
            </span>
            Watch architecture
          </motion.button>
        </motion.div>

        {/* Built-by line */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.5 }}
          className="mt-7 text-[10.5px] font-mono tracking-wider uppercase text-muted-foreground/55"
        >
          Built solo · Team Sigma Squad · BIS Hackathon 2026
        </motion.div>
      </div>

      {/* Scroll indicator */}
      <motion.button
        onClick={scrollToSearch}
        aria-label="Scroll to search"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1, y: [0, 8, 0] }}
        transition={{
          opacity: { duration: 0.6, delay: 0.8 },
          y: { duration: 2.4, repeat: Infinity, ease: "easeInOut", delay: 1 },
        }}
        className="absolute bottom-5 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1.5 text-muted-foreground hover:text-foreground transition group"
      >
        <span className="text-[10px] font-mono uppercase tracking-[0.2em] opacity-70 group-hover:opacity-100">
          Scroll
        </span>
        <ArrowDown className="size-4 opacity-70 group-hover:opacity-100" />
      </motion.button>

      {/* Inline architecture animation modal */}
      <ArchitectureModal open={archOpen} onClose={() => setArchOpen(false)} />
    </section>
  );
}
