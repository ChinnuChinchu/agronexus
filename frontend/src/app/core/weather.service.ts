import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { WeatherReport } from './models/weather.model';

@Injectable({ providedIn: 'root' })
export class WeatherService {
  private http = inject(HttpClient);

  get(): Observable<WeatherReport> {
    return this.http.get<WeatherReport>(`${environment.apiUrl}/weather`);
  }
}
