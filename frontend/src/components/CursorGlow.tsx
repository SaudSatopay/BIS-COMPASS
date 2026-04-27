"use client";

import { motion, useMotionValue, useSpring } from "framer-motion";
import { useEffect } from "react";

/**
 * Subtle cursor-following glow. Fixed to viewport, pointer-events none, low
 * opacity. Adds a sense of depth without being noisy.
 */
export function CursorGlow() {
  const mx = useMotionValue(-200);
  const my = useMotionValue(-200);
  const x = useSpring(mx, { stiffness: 80, damping: 22, mass: 0.4 });
  const y = useSpring(my, { stiffness: 80, damping: 22, mass: 0.4 });

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      mx.set(e.clientX);
      my.set(e.clientY);
    };
    window.addEventListener("pointermove", onMove);
    return () => window.removeEventListener("pointermove", onMove);
  }, [mx, my]);

  return (
    <motion.div
      aria-hidden
      style={{
        translateX: x,
        translateY: y,
        x: "-50%",
        y: "-50%",
      }}
      className="pointer-events-none fixed top-0 left-0 z-0 size-[420px] rounded-full"
    >
      <div className="size-full rounded-full bg-accent/15 blur-3xl" />
    </motion.div>
  );
}
