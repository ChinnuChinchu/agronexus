import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Observable, filter } from 'rxjs';

import { ageLabel, harvestCountdown } from '../../../core/crop-utils';
import { CropService } from '../../../core/crop.service';
import { Crop, CropStatus } from '../../../core/models/crop.model';
import { ConfirmData, ConfirmDialog } from '../../../shared/confirm-dialog/confirm-dialog';
import { StageTracker } from '../../../shared/stage-tracker/stage-tracker';
import { HarvestDialog } from '../harvest-dialog/harvest-dialog';

@Component({
  selector: 'app-crop-detail',
  imports: [
    DatePipe,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
    StageTracker,
  ],
  templateUrl: './crop-detail.html',
  styleUrl: './crop-detail.css',
})
export class CropDetail {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private cropService = inject(CropService);
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);

  crop = signal<Crop | null>(null);
  loading = signal(true);
  notFound = signal(false);
  error = signal(false);
  busy = signal(false);
  actionError = signal<string | null>(null);

  ageLabel = ageLabel;
  countdown = harvestCountdown;

  private id = Number(this.route.snapshot.paramMap.get('id'));

  constructor() {
    if (!Number.isInteger(this.id) || this.id <= 0) {
      this.router.navigateByUrl('/crops');
      return;
    }
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(false);
    this.notFound.set(false);

    this.cropService.get(this.id).subscribe({
      next: (crop) => {
        this.crop.set(crop);
        this.loading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.loading.set(false);
        if (err.status === 404) {
          this.notFound.set(true);
        } else {
          this.error.set(true);
        }
      },
    });
  }

  statusLabel(status: CropStatus): string {
    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  openHarvest(): void {
    const crop = this.crop();
    if (!crop) {
      return;
    }
    this.dialog
      .open(HarvestDialog, { data: { crop }, width: '440px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((updated?: Crop) => {
        if (updated) {
          this.crop.set(updated);
          this.snackBar.open('Crop marked as harvested', 'OK', { duration: 3000 });
        }
      });
  }

  markFailed(): void {
    this.confirm({
      title: 'Mark as failed?',
      message: 'Use this if the crop was lost. You can reopen it later if needed.',
      confirmLabel: 'Mark as failed',
    }).subscribe(() =>
      this.applyUpdate(this.cropService.update(this.id, { status: 'failed' }), 'Crop marked as failed'),
    );
  }

  reopen(): void {
    const crop = this.crop();
    const clears = crop?.status === 'harvested';
    this.confirm({
      title: 'Reopen this crop?',
      message: clears
        ? 'The crop goes back to growing, and its harvest date and yield will be cleared.'
        : 'The crop goes back to growing.',
      confirmLabel: 'Reopen',
    }).subscribe(() =>
      this.applyUpdate(this.cropService.update(this.id, { status: 'growing' }), 'Crop reopened'),
    );
  }

  deleteCrop(): void {
    this.confirm({
      title: 'Delete this crop?',
      message: 'This permanently removes the crop and its records. This cannot be undone.',
      confirmLabel: 'Delete',
      danger: true,
    }).subscribe(() => {
      this.busy.set(true);
      this.actionError.set(null);
      this.cropService.delete(this.id).subscribe({
        next: () => {
          this.snackBar.open('Crop deleted', 'OK', { duration: 3000 });
          this.router.navigateByUrl('/crops');
        },
        error: (err: HttpErrorResponse) => this.onActionError(err),
      });
    });
  }

  private confirm(data: ConfirmData): Observable<boolean> {
    return this.dialog
      .open(ConfirmDialog, { data, width: '420px', maxWidth: '95vw' })
      .afterClosed()
      .pipe(filter((ok): ok is boolean => ok === true));
  }

  private applyUpdate(request: Observable<Crop>, message: string): void {
    this.busy.set(true);
    this.actionError.set(null);
    request.subscribe({
      next: (crop) => {
        this.crop.set(crop);
        this.busy.set(false);
        this.snackBar.open(message, 'OK', { duration: 3000 });
      },
      error: (err: HttpErrorResponse) => this.onActionError(err),
    });
  }

  private onActionError(err: HttpErrorResponse): void {
    this.busy.set(false);
    this.actionError.set(
      typeof err.error?.detail === 'string'
        ? err.error.detail
        : 'Something went wrong. Please try again.',
    );
  }
}
