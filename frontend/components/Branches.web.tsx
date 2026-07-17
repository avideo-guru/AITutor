// Generative math-lattice art — adapted from Anthony Fu's ArtPlum
// (github.com/antfu/antfu.me, src/components/ArtPlum.vue, MIT). The growth
// engine is his: a queue of draw steps executed ~40fps, each with a 50%
// chance to defer one frame so growth fronts stagger, seeds entering from
// the viewport edges, culled 100px out of bounds. The drawing rule is
// deliberately different: antfu bends every segment by a random ±15°, which
// reads as a plum tree; here paths run dead straight and occasionally fork
// at exactly ±60°, so every line lies on a triangular lattice and the result
// reads as geometry — right for a JEE/NEET product. Tuned against rendered
// output: fixed 10px segments, per-tree budget so all four corners grow.
// Web only — native resolves Branches.tsx (null).

import React, { useEffect, useRef } from "react";

import { useTheme } from "@/lib/theme";

const R90 = Math.PI / 2;
const R180 = Math.PI;
const ANGLE = Math.PI / 3; // strict 60° forks — the geometry knob
const SEGMENT = 10; // fixed segment length keeps vertices on the lattice
const YOUNG = 40; // segments during which a tree always continues + forks more
const TREE_BUDGET = 1100; // per-seed segment cap so no corner starves another
const FPS = 40;

export function Branches() {
  const t = useTheme();
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const parent = canvas?.parentElement;
    if (!canvas || !parent) return;

    const w = parent.clientWidth;
    const h = parent.clientHeight;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.lineWidth = 1;
    ctx.strokeStyle = t.dot;

    const { random } = Math;
    let steps: Array<() => void> = [];
    let prevSteps: Array<() => void> = [];
    let raf = 0;
    let lastTime = performance.now();
    const interval = 1000 / FPS;

    const step = (x: number, y: number, rad: number, counter: { value: number }) => {
      counter.value += 1;
      const nx = x + SEGMENT * Math.cos(rad);
      const ny = y + SEGMENT * Math.sin(rad);

      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(nx, ny);
      ctx.stroke();

      if (counter.value > TREE_BUDGET) return;
      if (nx < -100 || nx > w + 100 || ny < -100 || ny > h + 100) return;

      const young = counter.value < YOUNG;
      const forkRate = young ? 0.15 : 0.08;
      if (young || random() < 0.88) steps.push(() => step(nx, ny, rad, counter));
      if (random() < forkRate) steps.push(() => step(nx, ny, rad + ANGLE, counter));
      if (random() < forkRate) steps.push(() => step(nx, ny, rad - ANGLE, counter));
    };

    const frame = () => {
      raf = requestAnimationFrame(frame);
      if (performance.now() - lastTime < interval) return;

      prevSteps = steps;
      steps = [];
      lastTime = performance.now();

      if (!prevSteps.length) {
        cancelAnimationFrame(raf);
        return;
      }

      prevSteps.forEach((fn) => {
        if (random() < 0.5) steps.push(fn);
        else fn();
      });
    };

    const randomMiddle = () => random() * 0.6 + 0.2;
    steps = [
      () => step(randomMiddle() * w, -5, R90, { value: 0 }),
      () => step(randomMiddle() * w, h + 5, -R90, { value: 0 }),
      () => step(-5, randomMiddle() * h, 0, { value: 0 }),
      () => step(w + 5, randomMiddle() * h, R180, { value: 0 }),
    ];
    if (w < 500) steps = steps.slice(0, 2);

    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [t.dot]);

  return (
    <canvas
      ref={ref}
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
        // keep the middle calm — the lattice lives at the edges
        maskImage: "radial-gradient(circle, transparent, black)",
        WebkitMaskImage: "radial-gradient(circle, transparent, black)",
      }}
    />
  );
}
