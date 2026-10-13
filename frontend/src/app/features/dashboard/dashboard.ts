import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { CropService } from '../../core/crop.service';
import { Crop } from '../../core/models/crop.model';
import { WeatherReport } from '../../core/models/weather.model';
import { WeatherService } from '../../core/weather.service';
import { conditionIcon, severityIcon } from '../weather/weather-utils';
import { MarketSnapshot } from '../market/market-snapshot';
import { ResourcesSnapshot } from '../resources/resources-snapshot';
import { DiseaseSnapshot } from '../disease/disease-snapshot';

interface ModuleCard {
  title: string;
  description: string;
  icon: string;
}

interface WeatherError {
  message: string;
  needsProfile: boolean;
}

@Component({
  selector: 'app-dashboard',
  imports: [
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
    MarketSnapshot,
    ResourcesSnapshot,
    DiseaseSnapshot
  ],
  template: `
    <h1>Welcome, {{ displayName() }} 👋</h1>

    @if (profileIncomplete()) {
      <mat-card class="notice">
        <mat-card-content>
          <p>
            <strong>Complete your profile.</strong>
            Add your district, state and farm size so weather and market insights can be
            tailored to your farm.
          </p>
          <a mat-flat-button routerLink="/profile">Update profile</a>
        </mat-card-content>
      </mat-card>
    }

    <section class="crops">
      <div class="section-header">
        <h2>Your crops</h2>
        <a mat-button routerLink="/crops">View all</a>
      </div>

      @if (loading()) {
        <mat-progress-bar mode="indeterminate" />
      } @else if (error()) {
        <div class="message error">
          <p>Could not load your crops.</p>
          <button mat-stroked-button (click)="loadCrops()">Retry</button>
        </div>
      } @else if (growing().length === 0) {
        <mat-card>
          <mat-card-content class="empty">
            <mat-icon class="big-icon">grass</mat-icon>
            <p>No crops are growing right now. Add a crop to start tracking it.</p>
            <a mat-flat-button routerLink="/crops/new">Add crop</a>
          </mat-card-content>
        </mat-card>
      } @else {
        <div class="stats">
          <a class="stat" routerLink="/crops">
            <span class="number">{{ growing().length }}</span>
            <span class="label">Growing</span>
          </a>
          <div class="stat">
            <span class="number">{{ dueSoon().length }}</span>
            <span class="label">Harvest due in 14 days</span>
          </div>
          <div class="stat" [class.alert]="overdue().length > 0">
            <span class="number">{{ overdue().length }}</span>
            <span class="label">Overdue</span>
          </div>
        </div>

        @if (nextHarvests().length > 0) {
          <mat-card class="next">
            <mat-card-content>
              <h3>Next harvests</h3>
              <ul>
                @for (c of nextHarvests(); track c.id) {
                  <li>
                    <a [routerLink]="['/crops', c.id]">
                      <span class="crop-name">{{ c.name }}</span>
                      <span class="crop-type">{{ c.crop_type.name }}</span>
                    </a>
                    <span class="when">{{ dueLabel(c.growth.days_to_harvest!) }}</span>
                  </li>
                }
              </ul>
            </mat-card-content>
          </mat-card>
        }
      }
    </section>
    <app-resources-snapshot />
    <section class="weather">
      <div class="section-header">
        <h2>Weather</h2>
        <a mat-button routerLink="/weather">Full forecast</a>
      </div>

      @if (weatherLoading()) {
        <mat-progress-bar mode="indeterminate" />
      } @else if (weatherError(); as e) {
        <mat-card>
          <mat-card-content class="empty">
            <mat-icon class="big-icon">{{ e.needsProfile ? 'location_off' : 'cloud_off' }}</mat-icon>
            <p>
              {{
                e.needsProfile
                  ? 'Add your village or district in your profile to see the weather.'
                  : e.message
              }}
            </p>
            @if (e.needsProfile) {
              <a mat-flat-button routerLink="/profile">Update profile</a>
            } @else {
              <button mat-stroked-button (click)="loadWeather()">Retry</button>
            }
          </mat-card-content>
        </mat-card>
      } @else if (weather(); as w) {
        <mat-card class="weather-card">
          <mat-card-content>
            <div class="w-main">
              <mat-icon [class]="'w-icon cond ' + w.current.condition.icon">
                {{ icon(w.current.condition.icon) }}
              </mat-icon>
              <div>
                <div class="w-temp">{{ w.current.temp_c }}°C</div>
                <div class="w-desc">{{ w.current.condition.label }}</div>
                <div class="w-loc">
                  <mat-icon>place</mat-icon>
                  {{ w.location.name }}@if (w.location.state) {, {{ w.location.state }} }
                </div>
              </div>
              <div class="w-extra">
                <span>Humidity {{ w.current.humidity_pct }}%</span>
                <span>Wind {{ w.current.wind_kmh }} km/h</span>
                @if (w.daily[0]; as today) {
                  <span>Rain chance today {{ today.rain_chance_pct }}%</span>
                }
              </div>
            </div>

            @if (w.advisories[0]; as a) {
              <div [class]="'advisory ' + a.severity">
                <mat-icon>{{ severityIcon(a.severity) }}</mat-icon>
                <div>
                  <div class="adv-title">{{ a.title }}</div>
                  <div class="adv-message">{{ a.message }}</div>
                  @if (w.advisories.length > 1) {
                    <a routerLink="/weather" class="more">
                      +{{ w.advisories.length - 1 }} more
                    </a>
                  }
                </div>
              </div>
            }
          </mat-card-content>
        </mat-card>
      }
    </section>
    <app-market-snapshot />
    <app-disease-snapshot />
  `,
  styles: `
    h1 {
      color: var(--forest);
    }
    h2 {
      color: var(--forest);
      margin: 24px 0 12px;
    }
    h3 {
      margin: 8px 0;
      color: var(--forest);
    }
    .notice {
      background: #fbe8b9;
      border-left: 5px solid var(--gold);
      margin-bottom: 8px;
    }
    .notice a {
      margin-top: 4px;
    }
    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .section-header h2 {
      margin: 24px 0 12px;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .stat {
      background: #fffdf8;
      border-top: 4px solid var(--forest);
      border-radius: 8px;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      text-decoration: none;
      color: inherit;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
    }
    a.stat:hover {
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
    }
    .stat .number {
      font-size: 2rem;
      font-weight: 700;
      color: var(--forest);
      line-height: 1.1;
    }
    .stat .label {
      font-size: 0.85rem;
      color: #6b6b60;
    }
    .stat.alert {
      border-top-color: var(--clay);
    }
    .stat.alert .number {
      color: var(--clay);
    }
    .next ul {
      list-style: none;
      margin: 0;
      padding: 0;
    }
    .next li {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 10px 0;
      border-bottom: 1px solid #e8dfcf;
    }
    .next li:last-child {
      border-bottom: none;
    }
    .next a {
      display: flex;
      flex-direction: column;
      text-decoration: none;
      color: inherit;
    }
    .crop-name {
      font-weight: 600;
      color: var(--forest);
    }
    .crop-type {
      font-size: 0.85rem;
      color: #6b6b60;
    }
    .when {
      font-weight: 500;
      white-space: nowrap;
    }
    .empty {
      text-align: center;
      padding: 16px;
      color: #6b6b60;
    }
    .big-icon {
      font-size: 40px;
      width: 40px;
      height: 40px;
      color: var(--forest);
    }
    .message {
      text-align: center;
      padding: 24px 16px;
      color: #6b6b60;
    }
    .message.error {
      color: #8a3a22;
    }

    /* ---- weather widget ---- */
    .weather-card {
      border-top: 4px solid var(--forest);
    }
    .w-main {
      display: flex;
      align-items: center;
      gap: 20px;
      flex-wrap: wrap;
    }
    .w-icon {
      font-size: 56px;
      width: 56px;
      height: 56px;
    }
    .w-temp {
      font-size: 2.2rem;
      font-weight: 700;
      line-height: 1.1;
      color: var(--forest);
    }
    .w-desc {
      font-weight: 500;
    }
    .w-loc {
      display: flex;
      align-items: center;
      gap: 2px;
      font-size: 0.85rem;
      color: #6b6b60;
    }
    .w-loc mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
      color: var(--clay);
    }
    .w-extra {
      display: flex;
      flex-direction: column;
      gap: 2px;
      font-size: 0.9rem;
      margin-left: auto;
    }
    .cond.clear,
    .cond.partly_cloudy {
      color: var(--gold);
    }
    .cond.cloudy,
    .cond.fog {
      color: #8a8272;
    }
    .cond.drizzle,
    .cond.rain {
      color: var(--forest);
    }
    .cond.thunderstorm {
      color: var(--clay);
    }
    .cond.snow {
      color: #5b7f95;
    }
    .advisory {
      display: flex;
      gap: 12px;
      align-items: flex-start;
      padding: 12px 14px;
      border-radius: 8px;
      border-left: 5px solid;
      margin-top: 16px;
    }
    .advisory.warning {
      background: #f8e3dc;
      border-color: var(--clay);
    }
    .advisory.warning mat-icon {
      color: #a8442a;
    }
    .advisory.caution {
      background: #fbe8b9;
      border-color: var(--gold);
    }
    .advisory.caution mat-icon {
      color: #8a6200;
    }
    .advisory.info {
      background: #dfeadf;
      border-color: var(--forest);
    }
    .advisory.info mat-icon {
      color: var(--forest);
    }
    .adv-title {
      font-weight: 700;
      margin-bottom: 2px;
    }
    .adv-message {
      font-size: 0.92rem;
    }
    .more {
      display: inline-block;
      margin-top: 6px;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--forest);
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 16px;
    }
    .grid mat-icon {
      color: var(--clay);
    }
  `,
})
export class Dashboard {
  private auth = inject(AuthService);
  private cropService = inject(CropService);
  private weatherService = inject(WeatherService);

  crops = signal<Crop[]>([]);
  loading = signal(true);
  error = signal(false);

  weather = signal<WeatherReport | null>(null);
  weatherLoading = signal(true);
  weatherError = signal<WeatherError | null>(null);

  icon = conditionIcon;
  severityIcon = severityIcon;

  displayName = computed(() => {
    const user = this.auth.currentUser();
    return user?.full_name || user?.username || '';
  });

  profileIncomplete = computed(() => {
    const user = this.auth.currentUser();
    return !!user && (!user.district || !user.state || !user.farm_size_acres);
  });

  growing = computed(() => this.crops().filter((c) => c.status === 'growing'));

  overdue = computed(() => this.growing().filter((c) => c.growth.is_overdue));

  dueSoon = computed(() =>
    this.growing().filter((c) => {
      const d = c.growth.days_to_harvest;
      return d !== null && d >= 0 && d <= 14;
    }),
  );

  nextHarvests = computed(() =>
    this.growing()
      .filter((c) => c.growth.days_to_harvest !== null && c.growth.days_to_harvest >= 0)
      .sort((a, b) => a.growth.days_to_harvest! - b.growth.days_to_harvest!)
      .slice(0, 3),
  );

  constructor() {
    this.loadCrops();
    this.loadWeather();
  }

  loadCrops(): void {
    this.loading.set(true);
    this.error.set(false);
    this.cropService.list('growing').subscribe({
      next: (list) => {
        this.crops.set(list);
        this.loading.set(false);
      },
      error: () => {
        this.error.set(true);
        this.loading.set(false);
      },
    });
  }

  loadWeather(): void {
    this.weatherLoading.set(true);
    this.weatherError.set(null);
    this.weatherService.get().subscribe({
      next: (report) => {
        this.weather.set(report);
        this.weatherLoading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.weather.set(null);
        this.weatherLoading.set(false);
        const needsProfile = err.status === 400 || err.status === 404;
        const detail = typeof err.error?.detail === 'string' ? err.error.detail : null;
        this.weatherError.set({
          needsProfile,
          message: detail ?? 'The weather is unavailable right now.',
        });
      },
    });
  }

  dueLabel(days: number): string {
    if (days === 0) {
      return 'Today';
    }
    if (days === 1) {
      return 'Tomorrow';
    }
    return `In ${days} days`;
  }
}
