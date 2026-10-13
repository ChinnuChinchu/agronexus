import { Routes } from '@angular/router';

import { authGuard, guestGuard } from './core/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    title: 'Sign in · AgroNexus',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/auth/login/login').then((m) => m.Login),
  },
  {
    path: 'register',
    title: 'Create account · AgroNexus',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/auth/register/register').then((m) => m.Register),
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./features/layout/layout').then((m) => m.Layout),
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        title: 'Dashboard · AgroNexus',
        loadComponent: () => import('./features/dashboard/dashboard').then((m) => m.Dashboard),
      },
      {
        path: 'crops',
        title: 'My crops · AgroNexus',
        loadComponent: () =>
          import('./features/crops/crop-list/crop-list').then((m) => m.CropList),
      },
      {
        path: 'crops/new',
        title: 'Add crop · AgroNexus',
        loadComponent: () =>
          import('./features/crops/crop-form/crop-form').then((m) => m.CropForm),
      },
      {
        path: 'crops/:id/edit',
        title: 'Edit crop · AgroNexus',
        loadComponent: () =>
          import('./features/crops/crop-form/crop-form').then((m) => m.CropForm),
      },
      {
        path: 'crops/:id',
        title: 'Crop · AgroNexus',
        loadComponent: () =>
          import('./features/crops/crop-detail/crop-detail').then((m) => m.CropDetail),
      },
      {
        path: 'weather',
        title: 'Weather · AgroNexus',
        loadComponent: () => import('./features/weather/weather').then((m) => m.Weather),
      },
      {
        path: 'market',
        title: 'Market prices · AgroNexus',
        loadComponent: () => import('./features/market/market').then((m) => m.Market),
      },
      {
        path: 'resources',
        title: 'Water & fertilizer · AgroNexus',
        loadComponent: () =>
          import('./features/resources/resources').then((m) => m.Resources),
      },
      {
        path: 'disease',
        title: 'Disease check · AgroNexus',
        loadComponent: () => import('./features/disease/disease').then((m) => m.Disease),
      },
      {
        path: 'profile',
        title: 'Profile · AgroNexus',
        loadComponent: () => import('./features/profile/profile').then((m) => m.Profile),
      },
      {
        path: '**',
        title: 'Page not found · AgroNexus',
        loadComponent: () =>
          import('./features/not-found/not-found').then((m) => m.NotFound),
      },
    ],
  },
];
