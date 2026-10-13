import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { PredictionResult, ScanRead, SupportedCrop } from './models/disease.model';

@Injectable({ providedIn: 'root' })
export class DiseaseService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/disease`;

  crops(): Observable<SupportedCrop[]> {
    return this.http.get<SupportedCrop[]>(`${this.baseUrl}/crops`);
  }

  predict(cropTypeId: number, photo: Blob): Observable<PredictionResult> {
    const form = new FormData();
    form.append('crop_type_id', String(cropTypeId));
    form.append('image', photo, 'leaf.jpg');
    return this.http.post<PredictionResult>(`${this.baseUrl}/predict`, form);
  }

  history(limit = 20): Observable<ScanRead[]> {
    const params = new HttpParams().set('limit', limit);
    return this.http.get<ScanRead[]>(`${this.baseUrl}/history`, { params });
  }

  deleteScan(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/history/${id}`);
  }
}
