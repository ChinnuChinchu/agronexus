import { Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-not-found',
  imports: [RouterLink, MatButtonModule, MatIconModule],
  template: `
    <div class="message">
      <mat-icon class="big-icon">search_off</mat-icon>
      <h1>Page not found</h1>
      <p>The page you are looking for does not exist.</p>
      <a mat-flat-button routerLink="/dashboard">Back to the dashboard</a>
    </div>
  `,
  styles: `
    .message {
      text-align: center;
      padding: 48px 16px;
      color: #6b6b60;
    }
    h1 {
      color: var(--forest);
      margin: 8px 0;
    }
    .big-icon {
      font-size: 56px;
      width: 56px;
      height: 56px;
      color: var(--forest);
    }
  `,
})
export class NotFound {}
