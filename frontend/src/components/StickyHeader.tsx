"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { Sparkles } from "lucide-react";

export function StickyHeader() {
  const { scrollY } = useScroll();
  const opacity = useTransform(scrollY, [0, 200, 400], [0, 0, 1]);
  const blur = useTransform(scrollY, [0, 400], [0, 16]);
  const backdropFilter = useTransform(blur, (b) => `blur(${b}px)`);

  return (
    <motion.header
      style={{ opacity, backdropFilter }}
      className="fixed top-0 inset-x-0 z-40 border-b border-border/40 bg-background/60"
    >
      <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <Sparkles className="size-4 text-accent" />
          <span className="font-medium">BIS Compass</span>
          <span className="text-muted-foreground hidden sm:inline">·</span>
          <span className="text-muted-foreground hidden sm:inline">559 standards · sub-second retrieval</span>
        </div>
        <div className="hidden sm:flex items-center gap-3 text-xs text-muted-foreground font-mono">
          <span>Hit@3 100%</span>
          <span className="text-accent">·</span>
          <span>MRR 0.93</span>
          <span className="text-accent">·</span>
          <span>&lt;1s</span>
        </div>
      </div>
    </motion.header>
  );
}
