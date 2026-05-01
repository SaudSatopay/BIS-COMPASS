"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, ArrowRight, X, ExternalLink, Lock } from "lucide-react";
import { useEffect, useState } from "react";
import {
  health,
  GEMINI_LS_KEY,
  GROQ_LS_KEY,
  KEY_SETUP_DONE,
} from "@/lib/api";
import { cn } from "@/lib/cn";

/**
 * Shows once on first load when:
 *   - the backend has NO LLM provider configured (env vars missing), AND
 *   - the user hasn't already saved keys or explicitly skipped before.
 *
 * Gives judges three options:
 *   1. Paste a Gemini key (free at aistudio.google.com/apikey)
 *   2. Paste a Groq key (free at console.groq.com/keys)
 *   3. Skip — the retrieval system works fully without an LLM key
 *
 * Keys are stored only in window.localStorage and forwarded with each
 * /search request body — they never touch our codebase or any third
 * party other than the user's own local backend.
 */
export function WelcomeModal() {
  const [open, setOpen] = useState(false);
  const [gemini, setGemini] = useState("");
  const [groq, setGroq] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      // Don't show if user already made a choice
      const done =
        typeof window !== "undefined" &&
        window.localStorage.getItem(KEY_SETUP_DONE);
      if (done) return;

      // Don't show if user already has a key in localStorage
      const hasLocalKey =
        typeof window !== "undefined" &&
        (window.localStorage.getItem(GEMINI_LS_KEY) ||
          window.localStorage.getItem(GROQ_LS_KEY));
      if (hasLocalKey) return;

      // Don't show if backend already has env-configured providers
      const h = await health();
      if (cancelled) return;
      if (h && h.llm_providers && h.llm_providers.length > 0) return;

      // Otherwise: prompt
      setOpen(true);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const dismiss = () => {
    window.localStorage.setItem(KEY_SETUP_DONE, "1");
    setOpen(false);
  };

  const skip = () => {
    dismiss();
  };

  const save = () => {
    setSaving(true);
    if (gemini.trim()) {
      window.localStorage.setItem(GEMINI_LS_KEY, gemini.trim());
    }
    if (groq.trim()) {
      window.localStorage.setItem(GROQ_LS_KEY, groq.trim());
    }
    dismiss();
    setSaving(false);
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="welcome-bd"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25 }}
          onClick={skip}
          className="fixed inset-0 z-[70] flex items-center justify-center p-4 sm:p-6 backdrop-blur-md bg-black/70"
        >
          <motion.div
            key="welcome-card"
            initial={{ scale: 0.96, opacity: 0, y: 12 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.97, opacity: 0, y: 6 }}
            transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
            onClick={(e) => e.stopPropagation()}
            className="relative w-full max-w-[560px] rounded-2xl border border-border bg-background shadow-2xl shadow-black/60 overflow-hidden"
          >
            {/* atmospheric gradient */}
            <div
              aria-hidden
              className="absolute inset-0 pointer-events-none bg-gradient-to-br from-accent/[0.08] via-transparent to-accent-2/[0.08]"
            />
            <div
              aria-hidden
              className="absolute -top-32 -right-20 size-72 rounded-full bg-accent/15 blur-3xl pointer-events-none"
            />

            {/* close button */}
            <button
              onClick={skip}
              aria-label="Skip"
              className="absolute top-3 right-3 z-10 size-8 rounded-full bg-black/40 backdrop-blur-sm border border-white/10 flex items-center justify-center text-white/60 hover:text-white hover:bg-black/60 transition"
            >
              <X className="size-4" />
            </button>

            <div className="relative p-7 sm:p-8">
              {/* header */}
              <div className="flex items-center gap-3">
                <div className="size-10 rounded-xl bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center shrink-0 shadow-lg shadow-accent/20">
                  <Sparkles className="size-5 text-black" />
                </div>
                <div>
                  <div className="text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
                    Optional
                  </div>
                  <div className="text-lg font-semibold tracking-tight">
                    Enable AI rationale layer
                  </div>
                </div>
              </div>

              {/* description */}
              <p className="mt-5 text-sm text-muted-foreground leading-relaxed">
                BIS Compass works on{" "}
                <span className="text-foreground/85">pure retrieval</span> — 100%
                Hit@3, sub-second on GPU. To also get a one-line{" "}
                <span className="text-foreground/85">AI rationale</span> per
                result and a{" "}
                <span className="text-foreground/85">query expansion</span>{" "}
                panel, paste a free LLM API key below.
              </p>

              {/* Gemini input */}
              <label className="block mt-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono uppercase tracking-wider text-foreground/85">
                    Gemini API key
                  </span>
                  <a
                    href="https://aistudio.google.com/apikey"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] text-accent inline-flex items-center gap-1 hover:underline"
                  >
                    get one free
                    <ExternalLink className="size-3" />
                  </a>
                </div>
                <input
                  type="password"
                  value={gemini}
                  onChange={(e) => setGemini(e.target.value)}
                  placeholder="AIza..."
                  spellCheck={false}
                  autoComplete="off"
                  className="w-full rounded-lg border border-border bg-muted/40 px-3.5 py-2.5 text-sm font-mono text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-accent/60 transition"
                />
              </label>

              {/* Groq input */}
              <label className="block mt-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono uppercase tracking-wider text-foreground/85">
                    Groq API key{" "}
                    <span className="text-muted-foreground/60 lowercase">
                      (fallback)
                    </span>
                  </span>
                  <a
                    href="https://console.groq.com/keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] text-accent inline-flex items-center gap-1 hover:underline"
                  >
                    get one free
                    <ExternalLink className="size-3" />
                  </a>
                </div>
                <input
                  type="password"
                  value={groq}
                  onChange={(e) => setGroq(e.target.value)}
                  placeholder="gsk_..."
                  spellCheck={false}
                  autoComplete="off"
                  className="w-full rounded-lg border border-border bg-muted/40 px-3.5 py-2.5 text-sm font-mono text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-accent/60 transition"
                />
              </label>

              {/* privacy note */}
              <div className="mt-5 flex items-start gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2.5">
                <Lock className="size-3.5 text-muted-foreground mt-0.5 shrink-0" />
                <p className="text-[11.5px] text-muted-foreground leading-relaxed">
                  Keys live only in{" "}
                  <code className="font-mono text-foreground/80">
                    localStorage
                  </code>{" "}
                  on this browser, sent only to your local backend with each
                  search. Nothing is logged or transmitted anywhere else.
                </p>
              </div>

              {/* actions */}
              <div className="mt-6 flex flex-col-reverse sm:flex-row gap-2.5 justify-end">
                <button
                  onClick={skip}
                  className="px-4 py-2.5 rounded-xl text-sm border border-border bg-muted/40 text-muted-foreground hover:bg-muted hover:text-foreground transition"
                >
                  Skip — retrieval only
                </button>
                <button
                  onClick={save}
                  disabled={saving || (!gemini.trim() && !groq.trim())}
                  className={cn(
                    "px-5 py-2.5 rounded-xl text-sm font-medium inline-flex items-center justify-center gap-1.5 transition",
                    "bg-gradient-to-r from-accent to-accent-2 text-black shadow-lg shadow-accent/20",
                    "hover:opacity-95 active:scale-[0.98]",
                    "disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none",
                  )}
                >
                  Save & continue
                  <ArrowRight className="size-4" />
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
