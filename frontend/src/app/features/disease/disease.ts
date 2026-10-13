import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  Component,
  DestroyRef,
  ElementRef,
  Injector,
  afterNextRender,
  computed,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { DomSanitizer, SafeUrl } from '@angular/platform-browser';
import { filter } from 'rxjs';

import { DiseaseService } from '../../core/disease.service';
import {
  PredictionResult,
  ScanLevel,
  ScanRead,
  SupportedCrop,
} from '../../core/models/disease.model';
import { ConfirmDialog } from '../../shared/confirm-dialog/confirm-dialog';
import { ALLOWED_TYPES, MAX_ORIGINAL_BYTES, prepareUpload } from './image-utils';

type Tone = 'good' | 'alert' | 'caution' | 'neutral';

const TONE_ICONS: Record<Tone, string> = {
  good: 'check_circle',
  alert: 'warning',
  caution: 'info',
  neutral: 'help_outline',
};

const LEVEL_LABELS: Record<ScanLevel, string> = {
  strong: 'Strong match',
  possible: 'Possible match',
  uncertain: 'Not sure',
};

@Component({
  selector: 'app-disease',
  imports: [
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatProgressBarModule,
    MatSelectModule,
  ],
  templateUrl: './disease.html',
  styleUrl: './disease.css',
})
export class Disease {
  private service = inject(DiseaseService);
  private sanitizer = inject(DomSanitizer);
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);
  private injector = inject(Injector);

  crops = signal<SupportedCrop[]>([]);
  cropsLoading = signal(true);
  cropsError = signal<string | null>(null);
  selectedCropId = signal<number | null>(null);

  file = signal<File | null>(null);
  preview = signal<SafeUrl | null>(null);
  fileError = signal<string | null>(null);
  private objectUrl: string | null = null;

  analysing = signal(false);
  analyseError = signal<string | null>(null);
  result = signal<PredictionResult | null>(null);

  history = signal<ScanRead[]>([]);
  historyLoading = signal(true);
  historyError = signal(false);

  resultCard = viewChild<ElementRef<HTMLElement>>('resultCard');

  supportedNames = computed(() => this.crops().map((c) => c.name).join(', '));
  canAnalyse = computed(
    () => this.file() !== null && this.selectedCropId() !== null && !this.analysing(),
  );

  constructor() {
    inject(DestroyRef).onDestroy(() => this.revokePreview());
    this.loadCrops();
    this.loadHistory();
  }

  // ---------- crops ----------
  loadCrops(): void {
    this.cropsLoading.set(true);
    this.cropsError.set(null);

    this.service.crops().subscribe({
      next: (list) => {
        this.crops.set(list);
        this.cropsLoading.set(false);
        if (list.length === 0) {
          this.cropsError.set('No crops are supported for disease checks yet.');
        } else if (this.selectedCropId() === null) {
          this.selectedCropId.set(list[0].crop_type_id);
        }
      },
      error: (err: HttpErrorResponse) => {
        this.cropsLoading.set(false);
        this.cropsError.set(
          err.status === 503
            ? 'Disease detection is not available right now. Please try again later.'
            : 'Could not load the disease check. Please try again.',
        );
      },
    });
  }

  onCropChange(id: number): void {
    this.selectedCropId.set(id);
    this.result.set(null);
    this.analyseError.set(null);
  }

  // ---------- photo ----------
  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const picked = input.files?.[0];
    input.value = ''; // so the same photo can be chosen again
    if (!picked) {
      return;
    }

    if (picked.type && !ALLOWED_TYPES.includes(picked.type)) {
      this.fileError.set('Please choose a JPEG, PNG or WebP photo.');
      return;
    }
    if (picked.size > MAX_ORIGINAL_BYTES) {
      this.fileError.set('This file is too large. Please choose a smaller photo.');
      return;
    }

    this.revokePreview();
    this.objectUrl = URL.createObjectURL(picked);
    this.preview.set(this.sanitizer.bypassSecurityTrustUrl(this.objectUrl));
    this.file.set(picked);
    this.fileError.set(null);
    this.analyseError.set(null);
    this.result.set(null);
  }

  clearPhoto(): void {
    this.revokePreview();
    this.preview.set(null);
    this.file.set(null);
    this.fileError.set(null);
    this.analyseError.set(null);
    this.result.set(null);
  }

  private revokePreview(): void {
    if (this.objectUrl) {
      URL.revokeObjectURL(this.objectUrl);
      this.objectUrl = null;
    }
  }

  // ---------- analysis ----------
  async analyse(): Promise<void> {
    const file = this.file();
    const cropId = this.selectedCropId();
    if (!file || cropId === null || this.analysing()) {
      return;
    }

    this.analysing.set(true);
    this.analyseError.set(null);
    this.result.set(null);

    const photo = await prepareUpload(file);
    this.service.predict(cropId, photo).subscribe({
      next: (result) => {
        this.result.set(result);
        this.analysing.set(false);
        this.loadHistory();
        afterNextRender(
          () => this.resultCard()?.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'start' }),
          { injector: this.injector },
        );
      },
      error: (err: HttpErrorResponse) => {
        this.analysing.set(false);
        this.analyseError.set(this.analyseMessage(err));
      },
    });
  }

  private analyseMessage(err: HttpErrorResponse): string {
    const detail = typeof err.error?.detail === 'string' ? err.error.detail : null;
    switch (err.status) {
      case 0:
        return 'Could not reach the server. Check your connection and try again.';
      case 413:
      case 422:
        return detail ?? 'This photo could not be used. Please try another one.';
      case 404:
        return detail ?? 'The crop was not found. Please choose it again.';
      case 503:
        return 'Disease detection is not available right now. Please try again later.';
      default:
        return 'Something went wrong while analysing the photo.';
    }
  }

  // ---------- history ----------
  loadHistory(): void {
    this.historyLoading.set(true);
    this.historyError.set(false);

    this.service.history().subscribe({
      next: (list) => {
        this.history.set(list);
        this.historyLoading.set(false);
      },
      error: () => {
        this.historyError.set(true);
        this.historyLoading.set(false);
      },
    });
  }

  deleteScan(scan: ScanRead): void {
    this.dialog
      .open(ConfirmDialog, {
        data: {
          title: 'Delete this check?',
          message: 'This removes it from your history. It cannot be undone.',
          confirmLabel: 'Delete',
          danger: true,
        },
        width: '400px',
        maxWidth: '95vw',
      })
      .afterClosed()
      .pipe(filter((ok): ok is boolean => ok === true))
      .subscribe(() => {
        this.service.deleteScan(scan.id).subscribe({
          next: () => {
            this.history.update((list) => list.filter((s) => s.id !== scan.id));
            this.snackBar.open('Check deleted', 'OK', { duration: 3000 });
          },
          error: () =>
            this.snackBar.open('Could not delete this check. Please try again.', 'OK', {
              duration: 4000,
            }),
        });
      });
  }

  // ---------- display helpers ----------
  tone(result: PredictionResult): Tone {
    if (result.status !== 'ok' || !result.top) {
      return 'neutral';
    }
    if (result.top.healthy) {
      return result.level === 'strong' ? 'good' : 'caution';
    }
    return result.level === 'strong' ? 'alert' : 'caution';
  }

  toneIcon(tone: Tone): string {
    return TONE_ICONS[tone];
  }

  scanTitle(scan: ScanRead): string {
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

  scanChip(scan: ScanRead): string {
    return scan.status === 'crop_mismatch' ? 'mismatch' : scan.level;
  }

  chipLabel(scan: ScanRead): string {
    return scan.status === 'crop_mismatch' ? 'Wrong crop?' : LEVEL_LABELS[scan.level];
  }
}
