import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { ResourcePlan } from './models/resources.model';

@Injectable({ providedIn: 'root' })
export class ResourcesService {
  private http = inject(HttpClient);

  plan(): Observable<ResourcePlan> {
    return this.http.get<ResourcePlan>(`${environment.apiUrl}/resources/plan`);
  }
}
