import { AfterViewInit, Component, ElementRef, NgZone, OnDestroy, ViewChild } from '@angular/core';

type Fn = () => void;

const R90 = Math.PI / 2;
const R15 = Math.PI / 12;
// Neutral gray (antfu.me's exact stroke) — legible on both cream and dark themes
const COLOR = '#88888825';
const MIN_BRANCH = 30;
const LEN = 6;
const FPS_INTERVAL = 1000 / 40;

/**
 * Generative "plum branch" background, ported from antfu.me's ArtPlum.vue.
 * Branches grow inward from the viewport edges; each segment randomly forks
 * at ±15° until it wanders off-screen or the growth queue empties.
 */
@Component({
  selector: 'app-art-plum',
  standalone: true,
  template: `
    <div class="plum-container" aria-hidden="true">
      <canvas #plumCanvas></canvas>
    </div>
  `,
  styles: [`
    .plum-container {
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 0;
      mask-image: radial-gradient(circle, transparent, black);
      -webkit-mask-image: radial-gradient(circle, transparent, black);
    }
  `]
})
export class ArtPlumComponent implements AfterViewInit, OnDestroy {
  @ViewChild('plumCanvas', { static: true }) canvasRef!: ElementRef<HTMLCanvasElement>;

  private ctx!: CanvasRenderingContext2D;
  private steps: Fn[] = [];
  private prevSteps: Fn[] = [];
  private rafId = 0;
  private lastTime = 0;
  private stopped = false;
  private width = 0;
  private height = 0;
  private resizeTimer: ReturnType<typeof setTimeout> | undefined;

  constructor(private zone: NgZone) {}

  ngAfterViewInit(): void {
    // The animation never touches component state, so keep it out of change detection
    this.zone.runOutsideAngular(() => {
      this.start();
      window.addEventListener('resize', this.onResize);
    });
  }

  ngOnDestroy(): void {
    cancelAnimationFrame(this.rafId);
    window.removeEventListener('resize', this.onResize);
    clearTimeout(this.resizeTimer);
  }

  private onResize = () => {
    clearTimeout(this.resizeTimer);
    this.resizeTimer = setTimeout(() => this.start(), 300);
  };

  private start(): void {
    cancelAnimationFrame(this.rafId);

    const canvas = this.canvasRef.nativeElement;
    this.width = window.innerWidth;
    this.height = window.innerHeight;

    const dpr = window.devicePixelRatio || 1;
    canvas.style.width = `${this.width}px`;
    canvas.style.height = `${this.height}px`;
    canvas.width = this.width * dpr;
    canvas.height = this.height * dpr;

    this.ctx = canvas.getContext('2d')!;
    this.ctx.scale(dpr, dpr);
    this.ctx.lineWidth = 1;
    this.ctx.strokeStyle = COLOR;

    const randomMiddle = () => Math.random() * 0.6 + 0.2;
    this.steps = [
      () => this.step(randomMiddle() * this.width, -5, R90, { value: 0 }),
      () => this.step(randomMiddle() * this.width, this.height + 5, -R90, { value: 0 }),
      () => this.step(-5, randomMiddle() * this.height, 0, { value: 0 }),
      () => this.step(this.width + 5, randomMiddle() * this.height, Math.PI, { value: 0 }),
    ];
    if (this.width < 500) {
      this.steps = this.steps.slice(0, 2);
    }

    this.prevSteps = [];
    this.stopped = false;
    this.lastTime = performance.now();
    this.rafId = requestAnimationFrame(this.frame);
  }

  private frame = () => {
    if (this.stopped) return;
    this.rafId = requestAnimationFrame(this.frame);

    if (performance.now() - this.lastTime < FPS_INTERVAL) return;
    this.lastTime = performance.now();

    this.prevSteps = this.steps;
    this.steps = [];

    if (!this.prevSteps.length) {
      this.stopped = true;
      cancelAnimationFrame(this.rafId);
      return;
    }

    for (const fn of this.prevSteps) {
      // Randomly defer half the pending segments a frame so growth looks organic
      if (Math.random() < 0.5) this.steps.push(fn);
      else fn();
    }
  };

  private step(x: number, y: number, rad: number, counter: { value: number }): void {
    const length = Math.random() * LEN;
    counter.value += 1;

    const nx = x + length * Math.cos(rad);
    const ny = y + length * Math.sin(rad);

    this.ctx.beginPath();
    this.ctx.moveTo(x, y);
    this.ctx.lineTo(nx, ny);
    this.ctx.stroke();

    const rad1 = rad + Math.random() * R15;
    const rad2 = rad - Math.random() * R15;

    if (nx < -100 || nx > this.width + 100 || ny < -100 || ny > this.height + 100) return;

    // Fork eagerly while the branch is young, then thin out
    const rate = counter.value <= MIN_BRANCH ? 0.8 : 0.5;
    if (Math.random() < rate) this.steps.push(() => this.step(nx, ny, rad1, counter));
    if (Math.random() < rate) this.steps.push(() => this.step(nx, ny, rad2, counter));
  }
}
