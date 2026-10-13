import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  Crop,
  CropCreateRequest,
  CropStatus,
  CropType,
  CropUpdateRequest,
  HarvestRequest,
} from './models/crop.model';

@Injectable({ providedIn: 'root' })
export class CropService {
  private http = inject(HttpClient);
  private baseUrl = environment.apiUrl;

  private cropTypes$?: Observable<CropType[]>;

  /** The catalog rarely changes, so it is fetched once and reused. */
  getCropTypes(): Observable<CropType[]> {
    if (!this.cropTypes$) {
      this.cropTypes$ = this.http
        .get<CropType[]>(`${this.baseUrl}/crop-types`)
        .pipe(shareReplay(1));
    }
    return this.cropTypes$;
  }

  list(status?: CropStatus | null, limit = 100, offset = 0): Observable<Crop[]> {
    let params = new HttpParams().set('limit', limit).set('offset', offset);
    if (status) {
      params = params.set('status', status);
    }
    return this.http.get<Crop[]>(`${this.baseUrl}/crops`, { params });
  }

  get(id: number): Observable<Crop> {
    return this.http.get<Crop>(`${this.baseUrl}/crops/${id}`);
  }

  create(data: CropCreateRequest): Observable<Crop> {
    return this.http.post<Crop>(`${this.baseUrl}/crops`, data);
  }

  update(id: number, data: CropUpdateRequest): Observable<Crop> {
    return this.http.put<Crop>(`${this.baseUrl}/crops/${id}`, data);
  }

  harvest(id: number, data: HarvestRequest): Observable<Crop> {
    return this.http.post<Crop>(`${this.baseUrl}/crops/${id}/harvest`, data);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/crops/${id}`);
  }
}
