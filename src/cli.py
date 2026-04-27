"""Interactive CLI for BIS Compass.

Usage:
    python -m src.cli                          # interactive REPL
    python -m src.cli "Portland slag cement"   # one-shot

Hits are printed as a tidy ranked table with confidence colours. Useful for
quick smoke-testing without spinning up the front-end.
"""
from __future__ import annotations

import argparse
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from src.offline_guard import enforce_offline_if_cached  # noqa: E402

enforce_offline_if_cached()

# ANSI colour codes (degrade gracefully on unsupported terminals).
def _supports_colour() -> bool:
    return sys.stdout.isatty() and sys.platform != "emscripten"


_C = {
    "reset":   "\x1b[0m",
    "dim":     "\x1b[2m",
    "bold":    "\x1b[1m",
    "accent":  "\x1b[38;2;250;145;90m",   # orange
    "rose":    "\x1b[38;2;220;80;130m",   # accent-2
    "green":   "\x1b[38;2;52;211;153m",
    "amber":   "\x1b[38;2;252;211;77m",
    "muted":   "\x1b[38;2;154;154;176m",
} if True else {}


def c(key: str, s: str) -> str:
    if not _supports_colour():
        return s
    return f"{_C.get(key, '')}{s}{_C['reset']}"


def _confidence_label(score: float) -> str:
    if score >= 0.65:
        return c("green", "HIGH  ")
    if score >= 0.35:
        return c("amber", "MEDIUM")
    return c("rose", "LOW   ")


def render_hits(query: str, hits, latency: float):
    print()
    print(c("dim", f'> "{query}"'))
    print(c("dim", f"  {latency * 1000:.0f}ms · top {len(hits)}"))
    print()
    print(
        c("muted", "  ##  ") +
        c("muted", " IS code".ljust(30)) +
        c("muted", " confidence".ljust(12)) +
        c("muted", " title")
    )
    print(c("muted", "  " + "-" * 78))
    for h in hits:
        rank = c("bold", f"  #{h.rank}".ljust(5))
        code = c("accent", f" {h.is_code}".ljust(30))
        conf = f" {_confidence_label(h.rerank_score)}".ljust(12 + 5)  # +5 for ANSI
        title = h.title[:55]
        print(f"{rank} {code} {conf} {title}")
        if h.scope:
            scope = h.scope[:90].rstrip()
            print(c("dim", f"      {scope}{'…' if len(h.scope) > 90 else ''}"))
    print()


def main():
    ap = argparse.ArgumentParser(
        description="BIS Compass — interactive CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("query", nargs="?", help="One-shot query. If omitted, enters REPL.")
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    print(c("bold", "BIS Compass"), c("dim", "· loading retriever (this is a one-time cost)..."))
    t0 = time.perf_counter()
    from src.retrieval.retriever import Retriever
    R = Retriever(final_k=args.top_k)
    print(c("dim", f"  ready in {time.perf_counter() - t0:.1f}s"))

    if args.query:
        t = time.perf_counter()
        hits = R.search(args.query)
        render_hits(args.query, hits, time.perf_counter() - t)
        return

    # REPL
    print(c("muted", "  Type a product description and hit Enter. Ctrl+C / Ctrl+D / 'exit' to quit."))
    while True:
        try:
            q = input(c("accent", "▶ ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not q:
            continue
        if q.lower() in {"exit", "quit", ":q"}:
            return
        t = time.perf_counter()
        try:
            hits = R.search(q)
        except Exception as e:
            print(c("rose", f"  error: {e}"))
            continue
        render_hits(q, hits, time.perf_counter() - t)


if __name__ == "__main__":
    main()
