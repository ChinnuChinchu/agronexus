import { Component, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';
import { catchError, forkJoin, map, of, switchMap } from 'rxjs';

import { CropService } from '../../core/crop.service';
import { MarketService } from '../../core/market.service';
import { Crop } from '../../core/models/crop.model';
import { PriceTrend } from '../../core/models/market.model';
import {
  chartDate,
  changeClass,
  changeIcon,
  changeText,
  inr,
  perKg,
  signalTitle,
} from './market-utils';

interface SnapshotRow {
  cropTypeId: number;
  name: string;
  mine: boolean;
  trend: PriceTrend;
}

const MAX_ROWS = 3;

@Component({
  selector: 'app-market-snapshot',
  imports: [RouterLink, MatButtonModule, MatCardModule, MatIconModule, MatProgressBarModule],
  template: `
    <div class="section-header">
      <h2>Market prices</h2>
      <a mat-button routerLink="/market">View all</a>
    </div>

    @if (loading()) {
      <mat-progress-bar mode="indeterminate" />
    } @else if (error()) {
      <mat-card>
        <mat-card-content class="empty error">
          <mat-icon class="big-icon">cloud_off</mat-icon>
          <p>Could not load market prices.</p>
          <button mat-stroked-button (click)="load()">Retry</button>
        </mat-card-content>
      </mat-card>
    } @else if (rows().length === 0) {
      <mat-card>
        <mat-card-content class="empty">
          <mat-icon class="big-icon">storefront</mat-icon>
          <p>No market price data is available for your state yet.</p>
        </mat-card-content>
      </mat-card>
    } @else {
      <mat-card class="market-card">
        <mat-card-content>
          @for (r of rows(); track r.cropTypeId) {
            <a class="row" routerLink="/market">
              <div class="crop">
                <span class="name">{{ r.name }}</span>
                @if (r.mine) {
                  <span class="chip">Your crop</span>
                }
                @if (r.trend.as_of) {
                  <span class="asof">as of {{ date(r.trend.as_of) }}</span>
                }
              </div>

              <div class="price">
                <strong>{{ inr(r.trend.latest_modal ?? 0) }}</strong>
                <span class="unit">
                  /quintal · {{ perKg(r.trend.latest_modal ?? 0) }}
                </span>
              </div>

              <div class="meta">
                @if (r.trend.change_7d_pct !== null) {
                  <span [class]="'change ' + changeClass(r.trend.change_7d_pct)">
                    <mat-icon>{{ changeIcon(r.trend.change_7d_pct) }}</mat-icon>
                    {{ changeText(r.trend.change_7d_pct) }} (7 days)
                  </span>
                }
                @if (r.trend.signal; as s) {
                  @if (s.label !== 'insufficient_data') {
                    <span [class]="'sig ' + s.label">{{ signalTitle(s.label) }}</span>
                  }
                }
              </div>
            </a>
          }

          @if (anyStale()) {
            <p class="note">
              <mat-icon>history</mat-icon>
              These are past prices (the latest data available), not today's rates.
            </p>
          }
        </mat-card-content>
      </mat-card>
    }
  `,
  styles: `
    h2 {
      color: var(--forest);
      margin: 24px 0 12px;
    }
    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .market-card {
      border-top: 4px solid var(--forest);
    }
    .row {
      display: grid;
      grid-template-columns: 1.4fr 1.2fr 1.4fr;
      gap: 8px 16px;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid #e8dfcf;
      text-decoration: none;
      color: inherit;
    }
    .row:hover {
      background: var(--sand-light);
    }
    .crop {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 2px 8px;
    }
    .name {
      font-weight: 700;
      color: var(--forest);
    }
    .asof {
      width: 100%;
      font-size: 0.75rem;
      color: #6b6b60;
    }
    .chip {
      padding: 1px 8px;
      border-radius: 10px;
      background: var(--gold);
      color: #2b1f00;
      font-size: 0.7rem;
      font-weight: 600;
    }
    .price strong {
      font-size: 1.15rem;
      color: var(--forest);
    }
    .unit {
      display: block;
      font-size: 0.75rem;
      color: #6b6b60;
    }
    .meta {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 4px 10px;
    }
    .change {
      display: inline-flex;
      align-items: center;
      gap: 2px;
      font-size: 0.85rem;
      font-weight: 600;
    }
    .change mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }
    .change.up {
      color: var(--forest);
    }
    .change.down {
      color: #a8442a;
    }
    .change.flat {
      color: #6b6b60;
    }
    .sig {
      padding: 2px 10px;
      border-radius: 10px;
      font-size: 0.75rem;
      font-weight: 600;
      background: var(--sand-light);
      color: #3b3b33;
    }
    .sig.above_average {
      background: #dfeadf;
      color: var(--forest);
    }
    .sig.below_average {
      background: #f8e3dc;
      color: #8a3a22;
    }
    .note {
      display: flex;
      align-items: center;
      gap: 6px;
      margin: 12px 0 0;
      font-size: 0.8rem;
      color: #6b6b60;
    }
    .note mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      color: #8a6200;
    }
    .empty {
      text-align: center;
      padding: 16px;
      color: #6b6b60;
    }
    .empty.error {
      color: #8a3a22;
    }
    .big-icon {
      font-size: 40px;
      width: 40px;
      height: 40px;
      color: var(--forest);
    }
    @media (max-width: 640px) {
      .row {
        grid-template-columns: 1fr;
      }
    }
  `,
})
export class MarketSnapshot {
  private marketService = inject(MarketService);
  private cropService = inject(CropService);

  rows = signal<SnapshotRow[]>([]);
  loading = signal(true);
  error = signal(false);

  anyStale = computed(() => this.rows().some((r) => r.trend.stale));

  inr = inr;
  perKg = perKg;
  date = chartDate;
  changeText = changeText;
  changeIcon = changeIcon;
  changeClass = changeClass;
  signalTitle = signalTitle;

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(false);

    forkJoin({
      available: this.marketService.crops(),
      growing: this.cropService.list('growing').pipe(catchError(() => of([] as Crop[]))),
    })
      .pipe(
        switchMap(({ available, growing }) => {
          const mine = new Set(growing.map((c) => c.crop_type.id));
          const ordered = [...available].sort(
            (a, b) => Number(mine.has(b.crop_type_id)) - Number(mine.has(a.crop_type_id)),
          );
          const picked = ordered.slice(0, MAX_ROWS);
          if (picked.length === 0) {
            return of([] as SnapshotRow[]);
          }
          return forkJoin(
            picked.map((crop) =>
              this.marketService.trend(crop.crop_type_id, 30).pipe(
                map(
                  (trend): SnapshotRow | null => ({
                    cropTypeId: crop.crop_type_id,
                    name: crop.name,
                    mine: mine.has(crop.crop_type_id),
                    trend,
                  }),
                ),
                catchError(() => of(null)),
              ),
            ),
          ).pipe(map((rows) => rows.filter((r): r is SnapshotRow => r !== null && r.trend.has_data)));
        }),
      )
      .subscribe({
        next: (rows) => {
          this.rows.set(rows);
          this.loading.set(false);
        },
        error: () => {
          this.error.set(true);
          this.loading.set(false);
        },
      });
  }
}
