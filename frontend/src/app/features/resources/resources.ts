import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';

import { IrrigationStatus, ResourcePlan } from '../../core/models/resources.model';
import { ResourcesService } from '../../core/resources.service';
import { fullDate } from '../market/market-utils';
import { shortDateLabel, weekdayLabel } from '../weather/weather-utils';

interface PageError {
  message: string;
  needsProfile: boolean;
}

const litresFormat = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });

const STATUS_ICONS: Record<IrrigationStatus, string> = {
  irrigate_soon: 'water_drop',
  plan_irrigation: 'schedule',
  not_needed: 'check_circle',
  flooded: 'waves',
  not_planted: 'hourglass_empty',
  no_guidance: 'help_outline',
};

@Component({
  selector: 'app-resources',
  imports: [RouterLink, MatButtonModule, MatCardModule, MatIconModule, MatProgressBarModule],
  templateUrl: './resources.html',
  styleUrl: './resources.css',
})
export class Resources {
  private resourcesService = inject(ResourcesService);

  plan = signal<ResourcePlan | null>(null);
  loading = signal(true);
  error = signal<PageError | null>(null);

  fullDate = fullDate;
  shortDate = shortDateLabel;

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);

    this.resourcesService.plan().subscribe({
      next: (plan) => {
        this.plan.set(plan);
        this.loading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.plan.set(null);
        this.loading.set(false);
        this.error.set(this.toError(err));
      },
    });
  }

  statusIcon(status: IrrigationStatus): string {
    return STATUS_ICONS[status] ?? 'help_outline';
  }

  litres(value: number): string {
    return litresFormat.format(value);
  }

  dayName(isoDate: string, asOf: string | null): string {
    return isoDate === asOf ? 'Today' : weekdayLabel(isoDate);
  }

  untilText(days: number | null): string {
    if (days === null) {
      return '';
    }
    if (days <= 0) {
      return 'very soon';
    }
    if (days < 60) {
      return `in about ${days} day${days === 1 ? '' : 's'}`;
    }
    return `in about ${Math.round(days / 30)} months`;
  }

  private toError(err: HttpErrorResponse): PageError {
    const detail = typeof err.error?.detail === 'string' ? err.error.detail : null;

    if (err.status === 400 || err.status === 404) {
      return {
        message: detail ?? 'We could not find your location. Please check your profile.',
        needsProfile: true,
      };
    }
    if (err.status === 503) {
      return {
        message: detail ?? 'The weather service is unavailable right now. Please try again.',
        needsProfile: false,
      };
    }
    if (err.status === 0) {
      return { message: 'Could not reach the server. Check your connection.', needsProfile: false };
    }
    return { message: 'Something went wrong while building your plan.', needsProfile: false };
  }
}
