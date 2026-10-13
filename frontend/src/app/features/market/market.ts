import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { forkJoin } from 'rxjs';

import { MarketService } from '../../core/market.service';
import { AvailableCrop, PriceBoard, PriceTrend } from '../../core/models/market.model';
import {
  agoLabel,
  changeClass,
  changeIcon,
  changeText,
  fullDate,
  inr,
  perKg,
  signalIcon,
  signalTitle,
} from './market-utils';
import { PriceChart } from './price-chart/price-chart';

@Component({
  selector: 'app-market',
  imports: [
    DatePipe,
    MatButtonModule,
    MatButtonToggleModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatProgressBarModule,
    MatSelectModule,
    PriceChart,
  ],
  templateUrl: './market.html',
  styleUrl: './market.css',
})
export class Market {
  private marketService = inject(MarketService);

  crops = signal<AvailableCrop[]>([]);
  cropsLoading = signal(true);
  cropsError = signal(false);

  selectedCropId = signal<number | null>(null);
  variety = signal(''); // '' means all varieties
  days = signal(90);

  board = signal<PriceBoard | null>(null);
  trend = signal<PriceTrend | null>(null);
  loading = signal(false);
  error = signal(false);

  readonly dayOptions = [30, 90, 365];
  private requestId = 0;

  selectedCrop = computed(
    () => this.crops().find((c) => c.crop_type_id === this.selectedCropId()) ?? null,
  );

  inr = inr;
  perKg = perKg;
  fullDate = fullDate;
  agoLabel = agoLabel;
  signalTitle = signalTitle;
  signalIcon = signalIcon;
  changeText = changeText;
  changeIcon = changeIcon;
  changeClass = changeClass;

  constructor() {
    this.loadCrops();
  }

  loadCrops(): void {
    this.cropsLoading.set(true);
    this.cropsError.set(false);

    this.marketService.crops().subscribe({
      next: (list) => {
        this.crops.set(list);
        this.cropsLoading.set(false);
        if (list.length > 0 && this.selectedCropId() === null) {
          this.selectedCropId.set(list[0].crop_type_id);
          this.loadPrices();
        }
      },
      error: () => {
        this.cropsError.set(true);
        this.cropsLoading.set(false);
      },
    });
  }

  loadPrices(): void {
    const cropId = this.selectedCropId();
    if (cropId === null) {
      return;
    }

    const request = ++this.requestId;
    this.loading.set(true);
    this.error.set(false);

    const variety = this.variety() || null;
    forkJoin({
      board: this.marketService.prices(cropId, variety),
      trend: this.marketService.trend(cropId, this.days(), variety),
    }).subscribe({
      next: ({ board, trend }) => {
        if (request !== this.requestId) {
          return;
        }
        this.board.set(board);
        this.trend.set(trend);
        this.loading.set(false);
      },
      error: () => {
        if (request !== this.requestId) {
          return;
        }
        this.error.set(true);
        this.loading.set(false);
      },
    });
  }

  onCropChange(id: number): void {
    this.selectedCropId.set(id);
    this.variety.set('');
    this.board.set(null);
    this.trend.set(null);
    this.loadPrices();
  }

  onVarietyChange(value: string): void {
    this.variety.set(value);
    this.loadPrices();
  }

  onDaysChange(value: number): void {
    this.days.set(value);
    this.loadPrices();
  }

  dayLabel(days: number): string {
    return days === 365 ? '1 year' : `${days} days`;
  }
}
