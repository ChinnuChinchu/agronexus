import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';

import { WeatherReport } from '../../core/models/weather.model';
import { WeatherService } from '../../core/weather.service';
import {
  clockLabel,
  conditionIcon,
  datePart,
  severityIcon,
  shortDateLabel,
  weekdayLabel,
} from './weather-utils';

interface WeatherError {
  message: string;
  needsProfile: boolean;
}

@Component({
  selector: 'app-weather',
  imports: [RouterLink, MatButtonModule, MatCardModule, MatIconModule, MatProgressBarModule],
  templateUrl: './weather.html',
  styleUrl: './weather.css',
})
export class Weather {
  private weatherService = inject(WeatherService);

  report = signal<WeatherReport | null>(null);
  loading = signal(true);
  error = signal<WeatherError | null>(null);

  today = computed(() => {
    const r = this.report();
    return r ? datePart(r.current.observed_at) : '';
  });

  icon = conditionIcon;
  severityIcon = severityIcon;
  clock = clockLabel;
  shortDate = shortDateLabel;

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);

    this.weatherService.get().subscribe({
      next: (report) => {
        this.report.set(report);
        this.loading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.report.set(null);
        this.loading.set(false);
        this.error.set(this.toError(err));
      },
    });
  }

  dayName(isoDate: string): string {
    return datePart(isoDate) === this.today() ? 'Today' : weekdayLabel(isoDate);
  }

  /** Day tag for slots that are not today, e.g. 'Fri'. */
  hourDay(iso: string): string {
    return datePart(iso) === this.today() ? '' : weekdayLabel(iso);
  }

  private toError(err: HttpErrorResponse): WeatherError {
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
    return { message: 'Something went wrong while loading the weather.', needsProfile: false };
  }
}
