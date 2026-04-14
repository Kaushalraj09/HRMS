import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';

import { AdminDashboardData, HrDashboardData } from '../models/dashboard.model';
import { Phase1StoreService } from './phase1-store.service';

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  constructor(private readonly store: Phase1StoreService) {}

  getAdminDashboard(): Observable<AdminDashboardData> {
    return of(this.store.getAdminDashboardData()).pipe(delay(250));
  }

  getHrDashboard(): Observable<HrDashboardData> {
    return of(this.store.getHrDashboardData()).pipe(delay(250));
  }
}
