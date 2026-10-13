import { Component, computed, input, signal } from '@angular/core';

import { TrendPoint } from '../../../core/models/market.model';
import { chartDate, fullDate, inr, perKg } from '../market-utils';

interface Coord {
  x: number;
  y: number;
  p: TrendPoint;
}

@Component({
  selector: 'app-price-chart',
  template: `
    @let g = geometry();
    <div class="caption">
      @if (active(); as a) {
        <strong>{{ date(a.p.date) }}</strong>
        · {{ inr(a.p.median_modal) }} per quintal ({{ perKg(a.p.median_modal) }}) ·
        {{ a.p.markets }} market{{ a.p.markets === 1 ? '' : 's' }}
      }
    </div>

    <svg
      class="chart"
      [attr.viewBox]="'0 0 ' + width + ' ' + height"
      role="img"
      [attr.aria-label]="ariaLabel()"
      (pointermove)="onMove($event)"
      (pointerleave)="onLeave()"
    >
      @for (t of g.ticks; track $index) {
        <line class="grid" [attr.x1]="left" [attr.x2]="width - right" [attr.y1]="t.y" [attr.y2]="t.y" />
        <text class="ylabel" [attr.x]="left - 8" [attr.y]="t.y + 4">{{ t.label }}</text>
      }

      @if (g.area) {
        <path class="area" [attr.d]="g.area" />
      }
      <path class="line" [attr.d]="g.line" />

      @for (l of g.xLabels; track l.x) {
        <text class="xlabel" [attr.x]="l.x" [attr.y]="height - 8" [attr.text-anchor]="l.anchor">
          {{ l.label }}
        </text>
      }

      @if (active(); as a) {
        <line class="cursor" [attr.x1]="a.c.x" [attr.x2]="a.c.x" [attr.y1]="top" [attr.y2]="g.baseline" />
        <circle class="dot" [attr.cx]="a.c.x" [attr.cy]="a.c.y" r="5" />
      }
    </svg>
  `,
  styles: `
    :host {
      display: block;
    }
    .caption {
      min-height: 1.5em;
      font-size: 0.9rem;
      margin-bottom: 4px;
      color: #3b3b33;
    }
    .chart {
      width: 100%;
      height: auto;
      display: block;
      touch-action: pan-y;
    }
    .grid {
      stroke: #e3d8c4;
      stroke-width: 1;
    }
    .ylabel,
    .xlabel {
      font-size: 11px;
      fill: #6b6b60;
    }
    .ylabel {
      text-anchor: end;
    }
    .area {
      fill: var(--gold);
      opacity: 0.25;
    }
    .line {
      fill: none;
      stroke: var(--forest);
      stroke-width: 2.5;
      stroke-linejoin: round;
      stroke-linecap: round;
    }
    .cursor {
      stroke: var(--clay);
      stroke-width: 1;
      stroke-dasharray: 4 3;
    }
    .dot {
      fill: var(--gold);
      stroke: var(--forest);
      stroke-width: 2;
    }
  `,
})
export class PriceChart {
  points = input.required<TrendPoint[]>();
  hover = signal<number | null>(null);

  readonly width = 600;
  readonly height = 230;
  readonly left = 68;
  readonly right = 14;
  readonly top = 14;
  readonly bottom = 30;

  inr = inr;
  perKg = perKg;
  date = fullDate;

  geometry = computed(() => {
    const pts = this.points();
    const n = pts.length;
    const plotW = this.width - this.left - this.right;
    const plotH = this.height - this.top - this.bottom;
    const baseline = this.top + plotH;

    if (n === 0) {
      return {
        coords: [] as Coord[],
        line: '',
        area: '',
        ticks: [] as { y: number; label: string }[],
        xLabels: [] as { x: number; label: string; anchor: string }[],
        baseline,
      };
    }

    const values = pts.map((p) => p.median_modal);
    let min = Math.min(...values);
    let max = Math.max(...values);
    if (min === max) {
      min -= 50;
      max += 50;
    }
    const pad = (max - min) * 0.1;
    const lo = min - pad;
    const hi = max + pad;

    const xAt = (i: number) =>
      n === 1 ? this.left + plotW / 2 : this.left + (i / (n - 1)) * plotW;
    const yAt = (v: number) => this.top + (1 - (v - lo) / (hi - lo)) * plotH;

    const coords: Coord[] = pts.map((p, i) => ({ x: xAt(i), y: yAt(p.median_modal), p }));
    const line = coords
      .map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(1)},${c.y.toFixed(1)}`)
      .join(' ');
    const area =
      n > 1
        ? `${line} L${coords[n - 1].x.toFixed(1)},${baseline} L${coords[0].x.toFixed(1)},${baseline} Z`
        : '';

    const ticks = [hi, (hi + lo) / 2, lo].map((v) => ({
      y: yAt(v),
      label: inr(Math.round(v)),
    }));

    const labelIndexes = [...new Set([0, Math.floor((n - 1) / 2), n - 1])];
    const xLabels = labelIndexes.map((i) => ({
      x: coords[i].x,
      label: chartDate(pts[i].date),
      anchor: i === 0 && n > 1 ? 'start' : i === n - 1 && n > 1 ? 'end' : 'middle',
    }));

    return { coords, line, area, ticks, xLabels, baseline };
  });

  active = computed(() => {
    const coords = this.geometry().coords;
    if (coords.length === 0) {
      return null;
    }
    const index = Math.min(this.hover() ?? coords.length - 1, coords.length - 1);
    const c = coords[index];
    return { c, p: c.p };
  });

  ariaLabel = computed(() => {
    const pts = this.points();
    if (pts.length === 0) {
      return 'Price trend chart with no data';
    }
    const first = pts[0];
    const last = pts[pts.length - 1];
    return (
      `Price trend from ${fullDate(first.date)} to ${fullDate(last.date)}. ` +
      `Latest median price ${inr(last.median_modal)} per quintal.`
    );
  });

  onMove(event: PointerEvent): void {
    const coords = this.geometry().coords;
    if (coords.length === 0) {
      return;
    }
    const svg = event.currentTarget as SVGSVGElement;
    const rect = svg.getBoundingClientRect();
    if (rect.width === 0) {
      return;
    }
    const x = (event.clientX - rect.left) * (this.width / rect.width);

    let best = 0;
    let bestDistance = Infinity;
    coords.forEach((c, i) => {
      const distance = Math.abs(c.x - x);
      if (distance < bestDistance) {
        bestDistance = distance;
        best = i;
      }
    });
    this.hover.set(best);
  }

  onLeave(): void {
    this.hover.set(null);
  }
}
