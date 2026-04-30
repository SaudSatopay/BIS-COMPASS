"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, ExternalLink } from "lucide-react";
import { useEffect, useRef } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function ArchitectureModal({ open, onClose }: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Esc-to-close from the parent (backdrop has focus)
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  // Esc-to-close from inside the iframe (via postMessage)
  useEffect(() => {
    if (!open) return;
    const onMsg = (e: MessageEvent) => {
      if (e.data && e.data.type === "architecture-close") onClose();
    };
    window.addEventListener("message", onMsg);
    return () => window.removeEventListener("message", onMsg);
  }, [open, onClose]);

  // Lock body scroll while open
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  // Auto-focus the iframe so arrow keys work immediately
  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => iframeRef.current?.focus(), 250);
    return () => clearTimeout(t);
  }, [open]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="arch-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25 }}
          onClick={onClose}
          className="fixed inset-0 z-[60] flex items-center justify-center p-3 sm:p-6 backdrop-blur-md bg-black/75"
        >
          <motion.div
            key="arch-shell"
            initial={{ scale: 0.96, opacity: 0, y: 12 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.97, opacity: 0, y: 6 }}
            transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
            onClick={(e) => e.stopPropagation()}
            className="relative w-full h-full max-w-[1600px] max-h-[920px] rounded-2xl overflow-hidden border border-border bg-background shadow-2xl shadow-black/60"
          >
            {/* gradient hairline (matches hero) */}
            <div className="absolute inset-0 rounded-2xl pointer-events-none ring-1 ring-inset ring-white/[0.04]" />

            <iframe
              ref={iframeRef}
              src="/architecture.html"
              title="BIS Compass — Architecture"
              className="w-full h-full block bg-background"
              allow="autoplay"
            />

            {/* Top-right controls */}
            <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
              <a
                href="/architecture.html"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Open in new tab"
                title="Open in new tab"
                className="size-9 rounded-full bg-black/60 backdrop-blur-md border border-white/10 flex items-center justify-center text-white/70 hover:text-white hover:bg-black/80 hover:border-white/20 transition"
              >
                <ExternalLink className="size-4" />
              </a>
              <button
                onClick={onClose}
                aria-label="Close"
                title="Close (Esc)"
                className="size-9 rounded-full bg-black/60 backdrop-blur-md border border-white/10 flex items-center justify-center text-white/80 hover:text-white hover:bg-black/80 hover:border-white/20 transition"
              >
                <X className="size-4" />
              </button>
            </div>

            {/* Hint footer */}
            <div className="absolute bottom-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-black/50 backdrop-blur-md border border-white/[0.06] text-[10px] font-mono uppercase tracking-[0.2em] text-white/45 pointer-events-none whitespace-nowrap">
              Esc · ← → navigate · A autoplay
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
