import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, switchMap, tap } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  RegisterRequest,
  TokenResponse,
  UpdateProfileRequest,
  User,
} from './models/user.model';

const TOKEN_KEY = 'farmease_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  private baseUrl = environment.apiUrl;

  private tokenSignal = signal<string | null>(localStorage.getItem(TOKEN_KEY));

  readonly currentUser = signal<User | null>(null);
  readonly isLoggedIn = computed(() => this.tokenSignal() !== null);

  get token(): string | null {
    return this.tokenSignal();
  }

  register(data: RegisterRequest): Observable<User> {
    return this.http.post<User>(`${this.baseUrl}/auth/register`, data);
  }

  login(username: string, password: string): Observable<User> {
    const body = new HttpParams().set('username', username).set('password', password);

    return this.http.post<TokenResponse>(`${this.baseUrl}/auth/login`, body).pipe(
      tap((res) => this.saveToken(res.access_token)),
      switchMap(() => this.loadProfile()),
    );
  }

  loadProfile(): Observable<User> {
    return this.http
      .get<User>(`${this.baseUrl}/users/me`)
      .pipe(tap((user) => this.currentUser.set(user)));
  }

  updateProfile(data: UpdateProfileRequest): Observable<User> {
    return this.http
      .put<User>(`${this.baseUrl}/users/me`, data)
      .pipe(tap((user) => this.currentUser.set(user)));
  }

    logout(): void {
    this.clearSession();
    this.router.navigate(['/login']);
  }

  clearSession(): void {
    localStorage.removeItem(TOKEN_KEY);
    this.tokenSignal.set(null);
    this.currentUser.set(null);
  }

  private saveToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
    this.tokenSignal.set(token);
  }
}
