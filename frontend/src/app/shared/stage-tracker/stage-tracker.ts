import { Component, input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

type StepState = 'done' | 'current' | 'upcoming';

@Component({
  selector: 'app-stage-tracker',
  imports: [MatIconModule],
  template: `
    <ol class="tracker">
      @for (name of stages(); track $index) {
        <li
          class="step"
          [attr.data-state]="stateOf($index)"
          [attr.aria-current]="stateOf($index) === 'current' ? 'step' : null"
        >
          <div class="bar"></div>
          <div class="label">
            @switch (stateOf($index)) {
              @case ('done') {
                <mat-icon>check_circle</mat-icon>
              }
              @case ('current') {
                <mat-icon>radio_button_checked</mat-icon>
              }
              @default {
                <mat-icon>radio_button_unchecked</mat-icon>
              }
            }
            <span>{{ name }}</span>
          </div>
        </li>
      }
    </ol>
  `,
  styles: `
    .tracker {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .step {
      flex: 1 1 110px;
      min-width: 0;
    }
    .bar {
      height: 8px;
      border-radius: 4px;
      background: #d9cdb8;
    }
    .label {
      display: flex;
      align-items: center;
      gap: 4px;
      margin-top: 6px;
      font-size: 0.85rem;
      color: #6b6b60;
    }
    .label mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      flex-shrink: 0;
      color: #9a8f78;
    }
    .step[data-state='done'] .bar {
      background: var(--forest);
    }
    .step[data-state='done'] .label mat-icon {
      color: var(--forest);
    }
    .step[data-state='current'] .bar {
      background: var(--gold);
    }
    .step[data-state='current'] .label {
      color: var(--forest);
      font-weight: 700;
    }
    .step[data-state='current'] .label mat-icon {
      color: var(--gold);
    }
  `,
})
export class StageTracker {
  stages = input.required<string[]>();
  currentIndex = input<number | null>(null);
  allDone = input(false);

  stateOf(index: number): StepState {
    if (this.allDone()) {
      return 'done';
    }
    const current = this.currentIndex();
    if (current === null) {
      return 'upcoming';
    }
    if (index < current) {
      return 'done';
    }
    return index === current ? 'current' : 'upcoming';
  }
}
