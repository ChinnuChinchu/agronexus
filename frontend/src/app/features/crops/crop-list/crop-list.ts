import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';

import { CropService } from '../../../core/crop.service';
import { Crop, CropStatus } from '../../../core/models/crop.model';

type StatusFilter = 'all' | CropStatus;

@Component({
  selector: 'app-crop-list',
  imports: [
    DatePipe,
    RouterLink,
    MatButtonModule,
    MatButtonToggleModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
  ],
  templateUrl: './crop-list.html',
  styleUrl: './crop-list.css',
})
export class CropList {
  private cropService = inject(CropService);

  crops = signal<Crop[]>([]);
  loading = signal(true);
  error = signal(false);
  filter = signal<StatusFilter>('all');

  constructor() {
    this.load();
  }

  load(): void {
    const requested = this.filter();
    this.loading.set(true);
    this.error.set(false);

    this.cropService.list(requested === 'all' ? null : requested).subscribe({
      next: (list) => {
        if (this.filter() !== requested) {
          return;
        }
        this.crops.set(list);
        this.loading.set(false);
      },
      error: () => {
        if (this.filter() !== requested) {
          return;
        }
        this.error.set(true);
        this.loading.set(false);
      },
    });
  }

  onFilterChange(value: StatusFilter): void {
    this.filter.set(value);
    this.load();
  }

  statusLabel(status: CropStatus): string {
    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  ageLabel(days: number): string {
    if (days < 60) {
      return `${days} day${days === 1 ? '' : 's'}`;
    }
    const months = Math.floor(days / 30.4375);
    if (months < 24) {
      return `${months} months`;
    }
    const years = Math.floor(months / 12);
    const rest = months % 12;
    return rest ? `${years} yr ${rest} mo` : `${years} yr`;
  }

  harvestInfo(crop: Crop): { text: string; overdue: boolean } | null {
    const g = crop.growth;
    if (crop.status !== 'growing') {
      return null;
    }
    if (g.stage === 'Planned') {
      return { text: 'Planting date is in the future', overdue: false };
    }
    if (g.days_to_harvest === null) {
      return { text: `Age: ${this.ageLabel(g.age_days)}`, overdue: false };
    }
    if (g.is_overdue) {
      const late = Math.abs(g.days_to_harvest);
      return { text: `Overdue by ${late} day${late === 1 ? '' : 's'}`, overdue: true };
    }
    if (g.days_to_harvest === 0) {
      return { text: 'Harvest due today', overdue: false };
    }
    if (g.days_to_harvest === 1) {
      return { text: 'Harvest tomorrow', overdue: false };
    }
    return { text: `${g.days_to_harvest} days to harvest`, overdue: false };
  }
}
