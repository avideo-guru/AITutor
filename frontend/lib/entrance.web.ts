// GSAP entrance stagger for elements tagged dataSet={{ animate: "1" }}.
// Web only — native resolves entrance.ts (no-op).

import { gsap } from "gsap";
import { useLayoutEffect } from "react";

export function useEntrance() {
  useLayoutEffect(() => {
    const els = document.querySelectorAll('[data-animate="1"]');
    if (!els.length) return;
    const tween = gsap.fromTo(
      els,
      { opacity: 0, y: 16 },
      { opacity: 1, y: 0, duration: 0.7, stagger: 0.07, ease: "power3.out", delay: 0.05 },
    );
    return () => {
      tween.kill();
    };
  }, []);
}
