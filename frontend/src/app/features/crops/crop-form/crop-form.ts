import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';

import { CropService } from '../../../core/crop.service';
import { addDays } from '../../../core/date-utils';
import { Crop, CropCreateRequest, CropType } from '../../../core/models/crop.model';

function harvestAfterPlanting(control: AbstractControl): ValidationErrors | null {
  const harvest = control.value as string;
  const planting = control.parent?.get('planting_date')?.value as string | undefined;
  return harvest && planting && harvest < planting ? { beforePlanting: true } : null;
}

@Component({
  selector: 'app-crop-form',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
  ],
  templateUrl: './crop-form.html',
  styleUrl: './crop-form.css',
})
export class CropForm {
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private cropService = inject(CropService);
  private snackBar = inject(MatSnackBar);

  isEdit = this.route.snapshot.paramMap.has('id');
  private cropId = Number(this.route.snapshot.paramMap.get('id'));
  get cropIdValue(): number {
    return this.cropId;
  }
  loading = signal(true);
  loadError = signal(false);
  notFound = signal(false);
  saving = signal(false);
  errorMessage = signal<string | null>(null);

  types = signal<CropType[]>([]);
  selectedType = signal<CropType | null>(null);

  groups = computed(() => {
    const map = new Map<string, CropType[]>();
    for (const t of this.types()) {
      map.set(t.category, [...(map.get(t.category) ?? []), t]);
    }
    return [...map].map(([category, types]) => ({ category, types }));
  });

  form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.maxLength(100)]],
    crop_type_id: [null as number | null, [Validators.required]],
    variety: ['', [Validators.maxLength(100)]],
    area_acres: [null as number | null, [Validators.min(0.01)]],
    planting_date: ['', [Validators.required]],
    expected_harvest_date: ['', [harvestAfterPlanting]],
    notes: ['', [Validators.maxLength(2000)]],
  });

  constructor() {
    if (this.isEdit && (!Number.isInteger(this.cropId) || this.cropId <= 0)) {
      this.router.navigateByUrl('/crops');
      return;
    }

    this.form.controls.crop_type_id.valueChanges.subscribe((id) => {
      this.applyType(this.types().find((t) => t.id === id) ?? null);
      this.suggestHarvest();
    });

    this.form.controls.planting_date.valueChanges.subscribe(() => {
      this.form.controls.expected_harvest_date.updateValueAndValidity();
      this.suggestHarvest();
    });

    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.loadError.set(false);
    this.notFound.set(false);

    forkJoin([
      this.cropService.getCropTypes(),
      this.isEdit ? this.cropService.get(this.cropId) : of(null),
    ]).subscribe({
      next: ([types, crop]) => {
        this.types.set(types);
        if (crop) {
          this.fillForm(crop, types);
        }
        this.loading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.loading.set(false);
        if (err.status === 404) {
          this.notFound.set(true);
        } else {
          this.loadError.set(true);
        }
      },
    });
  }

  private fillForm(crop: Crop, types: CropType[]): void {
    this.form.patchValue(
      {
        name: crop.name,
        crop_type_id: crop.crop_type.id,
        variety: crop.variety ?? '',
        area_acres: crop.area_acres,
        planting_date: crop.planting_date,
        expected_harvest_date: crop.expected_harvest_date ?? '',
        notes: crop.notes ?? '',
      },
      { emitEvent: false },
    );
    this.applyType(types.find((t) => t.id === crop.crop_type.id) ?? null);

    // an existing harvest date is the farmer's value, so never auto-overwrite it
    if (crop.expected_harvest_date) {
      this.form.controls.expected_harvest_date.markAsDirty();
    }
  }

  private applyType(type: CropType | null): void {
    this.selectedType.set(type);
    const harvest = this.form.controls.expected_harvest_date;
    harvest.setValidators(
      type?.cycle === 'seasonal'
        ? [Validators.required, harvestAfterPlanting]
        : [harvestAfterPlanting],
    );
    if (type?.cycle === 'perennial') {
      harvest.setValue('', { emitEvent: false });
      harvest.markAsPristine();
    }
    harvest.updateValueAndValidity({ emitEvent: false });
  }

  private suggestHarvest(): void {
    const type = this.selectedType();
    const harvest = this.form.controls.expected_harvest_date;
    const planting = this.form.controls.planting_date.value;

    if (!type || type.cycle !== 'seasonal' || !type.duration_days || !planting) {
      return;
    }
    if (harvest.dirty) {
      return;
    }
    harvest.setValue(addDays(planting, type.duration_days));
  }

  bearingLabel(months: number): string {
    return months % 12 === 0 ? `${months / 12} years` : `${months} months`;
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const v = this.form.getRawValue();
    const seasonal = this.selectedType()?.cycle === 'seasonal';
    const payload: CropCreateRequest = {
      name: v.name.trim(),
      crop_type_id: v.crop_type_id as number,
      variety: v.variety.trim() || null,
      area_acres: v.area_acres,
      planting_date: v.planting_date,
      expected_harvest_date: seasonal ? v.expected_harvest_date || null : null,
      notes: v.notes.trim() || null,
    };

    this.saving.set(true);
    this.errorMessage.set(null);

    const request = this.isEdit
      ? this.cropService.update(this.cropId, payload)
      : this.cropService.create(payload);

    request.subscribe({
      next: (crop) => {
        this.snackBar.open(this.isEdit ? 'Crop updated' : 'Crop added', 'OK', {
          duration: 3000,
        });
        this.router.navigate(['/crops', crop.id]);
      },
      error: (err: HttpErrorResponse) => {
        this.saving.set(false);
        this.errorMessage.set(
          typeof err.error?.detail === 'string'
            ? err.error.detail
            : 'Please check the details you entered and try again.',
        );
      },
    });
  }
}
