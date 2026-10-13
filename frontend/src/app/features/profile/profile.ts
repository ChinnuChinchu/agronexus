import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';

import { AuthService } from '../../core/auth.service';
import { UpdateProfileRequest } from '../../core/models/user.model';

@Component({
  selector: 'app-profile',
  imports: [
    ReactiveFormsModule,
    DatePipe,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
  ],
  templateUrl: './profile.html',
  styleUrl: './profile.css',
})
export class Profile {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private snackBar = inject(MatSnackBar);

  user = this.auth.currentUser;
  editing = signal(false);
  saving = signal(false);
  errorMessage = signal<string | null>(null);

  initial = computed(() => {
    const u = this.user();
    return ((u?.full_name || u?.username || '?').charAt(0)).toUpperCase();
  });

  form = this.fb.nonNullable.group({
    full_name: ['', [Validators.maxLength(100)]],
    email: ['', [Validators.email]],
    phone: ['', [Validators.pattern(/^[0-9+\-\s]{7,20}$/)]],
    village: ['', [Validators.maxLength(100)]],
    district: ['', [Validators.maxLength(100)]],
    state: ['', [Validators.maxLength(100)]],
    farm_size_acres: [null as number | null, [Validators.min(0.01)]],
  });

  startEdit(): void {
    const user = this.user();
    if (!user) {
      return;
    }
    this.form.reset({
      full_name: user.full_name ?? '',
      email: user.email ?? '',
      phone: user.phone ?? '',
      village: user.village ?? '',
      district: user.district ?? '',
      state: user.state ?? '',
      farm_size_acres: user.farm_size_acres,
    });
    this.errorMessage.set(null);
    this.editing.set(true);
  }

  cancelEdit(): void {
    this.errorMessage.set(null);
    this.editing.set(false);
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.saving.set(true);
    this.errorMessage.set(null);

    const v = this.form.getRawValue();
    const payload: UpdateProfileRequest = {
      full_name: v.full_name.trim() || null,
      email: v.email.trim() || null,
      phone: v.phone.trim() || null,
      village: v.village.trim() || null,
      district: v.district.trim() || null,
      state: v.state.trim() || null,
      farm_size_acres: v.farm_size_acres,
    };

    this.auth.updateProfile(payload).subscribe({
      next: () => {
        this.saving.set(false);
        this.editing.set(false);
        this.snackBar.open('Profile updated', 'OK', { duration: 3000 });
      },
      error: (err: HttpErrorResponse) => {
        this.saving.set(false);
        if (err.status === 409 && typeof err.error?.detail === 'string') {
          this.errorMessage.set(err.error.detail);
        } else if (err.status === 422) {
          this.errorMessage.set('Please check the details you entered.');
        } else {
          this.errorMessage.set('Could not save your profile. Please try again.');
        }
      },
    });
  }
}
