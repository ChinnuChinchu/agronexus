import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';

import { ResourcePlan } from '../../core/models/resources.model';
import { ResourcesService } from '../../core/resources.service';

interface PageError {
  message: string;
  needsProfile: boolean;
}

const MAX_ACTIONS = 3;

@Component({
  selector: 'app-resources-snapshot',
  imports: [RouterLink, MatButtonModule, MatCardModule, MatIconModule, MatProgressBarModule],
  template: `
    <div class="section-header">
      <h2>Water &amp; fertilizer</h2>
      <a mat-button routerLink="/resources">Full plan</a>
    </div>

    @if (loading()) {
      <mat-progress-bar mode="indeterminate" />
    } @else if (error(); as e) {
      <mat-card>
        <mat-card-content class="empty" [class.error]="!e.needsProfile">
          <mat-icon class="big-icon">{{ e.needsProfile ? 'location_off' : 'cloud_off' }}</mat-icon>
          <p>
            {{
              e.needsProfile
                ? 'Add your village or district in your profile to get a water and fertilizer plan.'
                : e.message
            }}
          </p>
          @if (e.needsProfile) {
            <a mat-flat-button routerLink="/profile">Update profile</a>
          } @else {
            <button mat-stroked-button (click)="load()">Retry</button>
          }
        </mat-card-content>
      </mat-card>
    } @else if (plan(); as p) {
      @if (p.crops.length === 0) {
        <mat-card>
          <mat-card-content class="empty">
            <mat-icon class="big-icon">grass</mat-icon>
            <p>Add a growing crop to get a water and fertilizer plan.</p>
            <a mat-flat-button routerLink="/crops/new">Add crop</a>
          </mat-card-content>
        </mat-card>
      } @else {
        <mat-card class="res-card">
          <mat-card-content>
            <p class="summary">
              {{ p.summary.crops }} growing crop{{ p.summary.crops === 1 ? '' : 's' }} ·
              {{ p.summary.need_water_soon }} need water soon ·
              {{ p.summary.fertilizer_due }} fertilizer due
            </p>

            @if (topActions().length === 0) {
              <div class="calm">
                <mat-icon>check_circle</mat-icon>
                Nothing urgent for your crops right now.
              </div>
            } @else {
              <div class="actions">
                @for (a of topActions(); track a.crop_id + a.kind) {
                  <a [class]="'action ' + a.priority" routerLink="/resources">
                    <mat-icon>{{ a.kind === 'irrigation' ? 'water_drop' : 'eco' }}</mat-icon>
                    <span class="action-text">{{ a.text }}</span>
                    <span class="prio">{{ a.priority === 'high' ? 'Urgent' : 'Soon' }}</span>
                  </a>
                }
              </div>
              @if (extra() > 0) {
                <a class="more" routerLink="/resources">+{{ extra() }} more</a>
              }
            }
          </mat-card-content>
        </mat-card>
      }
    }
  `,
  styles: `
    h2 {
      color: var(--forest);
      margin: 24px 0 12px;
    }
    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .res-card {
      border-top: 4px solid var(--forest);
    }
    .summary {
      margin: 4px 0 12px;
      color: #6b6b60;
      font-size: 0.9rem;
    }
    .actions {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .action {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 14px;
      border-radius: 8px;
      border-left: 5px solid;
      text-decoration: none;
      color: inherit;
    }
    .action.high {
      background: #f8e3dc;
      border-color: var(--clay);
    }
    .action.high mat-icon {
      color: #a8442a;
    }
    .action.medium {
      background: #fbe8b9;
      border-color: var(--gold);
    }
    .action.medium mat-icon {
      color: #8a6200;
    }
    .action-text {
      flex: 1;
      font-weight: 500;
    }
    .prio {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #3b3b33;
    }
    .more {
      display: inline-block;
      margin-top: 10px;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--forest);
    }
    .calm {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 14px;
      border-radius: 8px;
      background: #dfeadf;
      border-left: 5px solid var(--forest);
    }
    .calm mat-icon {
      color: var(--forest);
    }
    .empty {
      text-align: center;
      padding: 16px;
      color: #6b6b60;
    }
    .empty.error {
      color: #8a3a22;
    }
    .big-icon {
      font-size: 40px;
      width: 40px;
      height: 40px;
      color: var(--forest);
    }
  `,
})
export class ResourcesSnapshot {
  private resourcesService = inject(ResourcesService);

  plan = signal<ResourcePlan | null>(null);
  loading = signal(true);
  error = signal<PageError | null>(null);

  topActions = computed(() => this.plan()?.actions.slice(0, MAX_ACTIONS) ?? []);
  extra = computed(() => Math.max((this.plan()?.actions.length ?? 0) - MAX_ACTIONS, 0));

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);

    this.resourcesService.plan().subscribe({
      next: (plan) => {
        this.plan.set(plan);
        this.loading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.plan.set(null);
        this.loading.set(false);
        const detail = typeof err.error?.detail === 'string' ? err.error.detail : null;
        this.error.set({
          needsProfile: err.status === 400 || err.status === 404,
          message: detail ?? 'The plan is unavailable right now.',
        });
      },
    });
  }
}
