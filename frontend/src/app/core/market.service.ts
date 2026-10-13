import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { AvailableCrop, PriceBoard, PriceTrend } from './models/market.model';

@Injectable({ providedIn: 'root' })
export class MarketService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/market`;

  crops(): Observable<AvailableCrop[]> {
    return this.http.get<AvailableCrop[]>(`${this.baseUrl}/crops`);
  }

  prices(cropTypeId: number, variety?: string | null): Observable<PriceBoard> {
    let params = new HttpParams().set('crop_type_id', cropTypeId);
    if (variety) {
      params = params.set('variety', variety);
    }
    return this.http.get<PriceBoard>(`${this.baseUrl}/prices`, { params });
  }

  trend(cropTypeId: number, days: number, variety?: string | null): Observable<PriceTrend> {
    let params = new HttpParams().set('crop_type_id', cropTypeId).set('days', days);
    if (variety) {
      params = params.set('variety', variety);
    }
    return this.http.get<PriceTrend>(`${this.baseUrl}/trend`, { params });
  }
}
