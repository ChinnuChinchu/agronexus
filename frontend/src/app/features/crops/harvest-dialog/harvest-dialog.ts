import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { CropService } from '../../../core/crop.service';
import { todayIso } from '../../../core/date-utils';
import { Crop, HarvestRequest } from '../../../core/models/crop.model';

@Component({
  selector: 'app-harvest-dialog',
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
  ],
  template: `
    <h2 mat-dialog-title>Mark as harvested</h2>
    <form [formGroup]="form" (ngSubmit)="submit()">
      <mat-dialog-content>
        <p class="crop-name">{{ data.crop.name }}</p>

        @if (errorMessage()) {
          <div class="form-error">{{ errorMessage() }}</div>
        }

        <mat-form-field appearance="outline">
          <mat-label>Harvest date</mat-label>
          <input
            matInput
            type="date"
            formControlName="date"
            [min]="data.crop.planting_date"
            [max]="today"
          />
          @if (form.controls.date.hasError('required')) {
            <mat-error>Harvest date is required</mat-error>
          }
        </mat-form-field>

        <div class="row">
          <mat-form-field appearance="outline">
            <mat-label>Yield (optional)</mat-label>
            <input matInput type="number" step="any" formControlName="quantity" />
            @if (form.controls.quantity.hasError('min')) {
              <mat-error>Must be greater than 0</mat-error>
            }
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Unit</mat-label>
            <mat-select formControlName="unit">
              @for (u of units; track u) {
                <mat-option [value]="u">{{ u }}</mat-option>
              }
            </mat-select>
          </mat-form-field>
        </div>
      </mat-dialog-content>

      <mat-dialog-actions>
        <button mat-button type="button" mat-dialog-close [disabled]="saving()">Cancel</button>
        <button mat-flat-button type="submit" [disabled]="saving()">
          {{ saving() ? 'Saving...' : 'Mark as harvested' }}
        </button>
      </mat-dialog-actions>
    </form>
  `,
  styles: `
    .crop-name {
      margin: 0 0 12px;
      font-weight: 600;
      color: var(--forest);
    }
    mat-form-field {
      width: 100%;
    }
    .row {
      display: grid;
      grid-template-columns: 2fr 1fr;
      column-gap: 12px;
    }
    mat-dialog-actions {
      justify-content: flex-end;
    }
    .form-error {
      background: #f8e3dc;
      color: #8a3a22;
      border-left: 4px solid var(--clay);
      padding: 10px 12px;
      border-radius: 6px;
      margin-bottom: 12px;
      font-size: 0.9rem;
    }
  `,
})
export class HarvestDialog {
  private fb = inject(FormBuilder);
  private cropService = inject(CropService);
  private dialogRef = inject(MatDialogRef<HarvestDialog, Crop>);
  data = inject<{ crop: Crop }>(MAT_DIALOG_DATA);

  today = todayIso();
  units = ['kg', 'quintal', 'tonne', 'bunches', 'nuts', 'pieces', 'litres'];

  saving = signal(false);
  errorMessage = signal<string | null>(null);

  form = this.fb.nonNullable.group({
    date: [this.today, [Validators.required]],
    quantity: [null as number | null, [Validators.min(0.01)]],
    unit: ['kg'],
  });

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const v = this.form.getRawValue();
    const payload: HarvestRequest = {
      actual_harvest_date: v.date,
      yield_quantity: v.quantity,
      yield_unit: v.quantity ? v.unit : null,
    };

    this.saving.set(true);
    this.errorMessage.set(null);

    this.cropService.harvest(this.data.crop.id, payload).subscribe({
      next: (updated) => this.dialogRef.close(updated),
      error: (err: HttpErrorResponse) => {
        this.saving.set(false);
        this.errorMessage.set(
          typeof err.error?.detail === 'string'
            ? err.error.detail
            : 'Could not save. Please check the details and try again.',
        );
      },
    });
  }
}
