import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';

import { CreateHrPayload, HrUser } from '../models/hr.model';
import { PaginatedResult } from '../models/employee.model';
import { Phase1StoreService } from './phase1-store.service';

@Injectable({
  providedIn: 'root'
})
export class HrService {
  constructor(private readonly store: Phase1StoreService) {}

  getHrUsers(page: number, limit: number, search: string, status: string): Observable<PaginatedResult<HrUser>> {
    return of(this.store.listHrs({ page, limit, search, status })).pipe(delay(300));
  }

  createHr(payload: CreateHrPayload): Observable<{ success: boolean; message: string; hr: HrUser }> {
    return of(this.store.createHr(payload)).pipe(delay(400));
  }
}
