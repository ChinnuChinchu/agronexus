import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
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
import { Router, RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';

import { AuthService } from '../../../core/auth.service';
import { RegisterRequest } from '../../../core/models/user.model';

function matchesPassword(control: AbstractControl): ValidationErrors | null {
  const password = control.parent?.get('password')?.value;
  return control.value === password ? null : { mismatch: true };
}

@Component({
  selector: 'app-register',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
  ],
  templateUrl: './register.html',
  styleUrl: '../auth.css',
})
export class Register {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);

  hidePassword = signal(true);
  loading = signal(false);
  errorMessage = signal<string | null>(null);

  form = this.fb.nonNullable.group({
    username: [
      '',
      [
        Validators.required,
        Validators.minLength(3),
        Validators.maxLength(50),
        Validators.pattern(/^[A-Za-z0-9_.]+$/),
      ],
    ],
    full_name: ['', [Validators.maxLength(100)]],
    email: ['', [Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8), Validators.maxLength(72)]],
    confirmPassword: ['', [Validators.required, matchesPassword]],
  });

  constructor() {
    this.form.controls.password.valueChanges.subscribe(() =>
      this.form.controls.confirmPassword.updateValueAndValidity(),
    );
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.loading.set(true);
    this.errorMessage.set(null);

    const v = this.form.getRawValue();
    const payload: RegisterRequest = {
      username: v.username.trim(),
      password: v.password,
      email: v.email.trim() || null,
      full_name: v.full_name.trim() || null,
    };

    this.auth
      .register(payload)
      .pipe(switchMap(() => this.auth.login(payload.username, payload.password)))
      .subscribe({
        next: () => this.router.navigateByUrl('/dashboard'),
        error: (err: HttpErrorResponse) => {
          this.loading.set(false);
          if (err.status === 409 && typeof err.error?.detail === 'string') {
            this.errorMessage.set(err.error.detail);
          } else if (err.status === 422) {
            this.errorMessage.set('Please check the details you entered.');
          } else {
            this.errorMessage.set('Unable to reach the server. Please try again.');
          }
        },
      });
  }
}
