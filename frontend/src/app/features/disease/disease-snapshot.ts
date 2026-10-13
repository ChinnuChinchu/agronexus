import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';

import { DiseaseService } from '../../core/disease.service';
import { ScanLevel, ScanRead } from '../../core/models/disease.model';

const LEVEL_LABELS: Record<ScanLevel, string> = {
  strong: 'Strong match',
  possible: 'Possible match',
  uncertain: 'Not sure',
};

@Component({
  selector: 'app-disease-snapshot',
  imports: [DatePipe, RouterLink, MatButtonModule, MatCardModule, MatIconModule],
  template: `
    <div class="section-header">
      <h2>Crop disease check</h2>
      <a mat-button routerLink="/disease">Open</a>
    </div>

    <mat-card class="disease-card">
      <mat-card-content>
        <div class="cta">
          <mat-icon class="cta-icon">biotech</mat-icon>
          <div class="cta-text">
            <strong>Check a leaf for disease</strong>
            <span>Take a photo of a tomato or maize leaf and get a suggestion.</span>
          </div>
          <a mat-flat-button routerLink="/disease">
            <mat-icon>photo_camera</mat-icon>
            Check a leaf
          </a>
        </div>

        @if (last(); as s) {
          <div class="last">
            <div class="last-label">Last check</div>
            <a class="scan" routerLink="/disease">
              <div class="scan-main">
                <div class="scan-title">{{ title(s) }}</div>
                <div class="scan-sub">
                  {{ s.crop_name }} · {{ s.created_at | date: 'd MMM y, h:mm a' }}
                </div>
              </div>
              <span [class]="'chip ' + chipClass(s)">{{ chipLabel(s) }}</span>
            </a>
          </div>
        }

        <p class="fine">
          Suggestions only, not a diagnosis. Confirm with your Krishi Bhavan before treating.
        </p>
      </mat-card-content>
    </mat-card>
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
    .disease-card {
      border-top: 4px solid var(--forest);
    }
    .cta {
      display: flex;
      align-items: center;
      gap: 14px;
      flex-wrap: wrap;
    }
    .cta-icon {
      font-size: 36px;
      width: 36px;
      height: 36px;
      color: var(--clay);
    }
    .cta-text {
      flex: 1;
      min-width: 200px;
      display: flex;
      flex-direction: column;
    }
    .cta-text strong {
      color: var(--forest);
    }
    .cta-text span {
      font-size: 0.9rem;
      color: #6b6b60;
    }
    .last {
      margin-top: 16px;
      padding-top: 12px;
      border-top: 1px solid #e8dfcf;
    }
    .last-label {
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #6b6b60;
      margin-bottom: 4px;
    }
    .scan {
      display: flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
      color: inherit;
    }
    .scan-main {
      flex: 1;
      min-width: 0;
    }
    .scan-title {
      font-weight: 600;
      color: var(--forest);
    }
    .scan-sub {
      font-size: 0.8rem;
      color: #6b6b60;
    }
    .chip {
      padding: 2px 10px;
      border-radius: 12px;
      font-size: 0.78rem;
      font-weight: 600;
      white-space: nowrap;
    }
    .chip.strong {
      background: #dfeadf;
      color: var(--forest);
    }
    .chip.possible {
      background: #fbe8b9;
      color: #6b4a00;
    }
    .chip.uncertain,
    .chip.mismatch {
      background: var(--sand);
      color: #3b3b33;
    }
    .fine {
      margin: 14px 0 0;
      font-size: 0.8rem;
      color: #6b6b60;
    }
  `,
})
export class DiseaseSnapshot {
  private service = inject(DiseaseService);

  last = signal<ScanRead | null>(null);

  constructor() {
    // The button works without the history, so a failed load is deliberately silent.
    this.service.history(1).subscribe({
      next: (list) => this.last.set(list[0] ?? null),
      error: () => this.last.set(null),
    });
  }

  title(scan: ScanRead): string {
    if (scan.status === 'crop_mismatch') {
      return `Doesn't look like a ${scan.crop_name} leaf`;
    }
    if (scan.status === 'uncertain') {
      return 'Not sure';
    }
    if (scan.healthy) {
      return scan.level === 'strong' ? 'Looks healthy' : 'Possibly healthy';
    }
    return scan.result_name ?? 'Unknown';
  }

  chipClass(scan: ScanRead): string {
    return scan.status === 'crop_mismatch' ? 'mismatch' : scan.level;
  }

  chipLabel(scan: ScanRead): string {
    return scan.status === 'crop_mismatch' ? 'Wrong crop?' : LEVEL_LABELS[scan.level];
  }
}
