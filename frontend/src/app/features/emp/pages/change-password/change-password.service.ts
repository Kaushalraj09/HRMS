import { Injectable } from '@angular/core';
import { Observable, of, throwError } from 'rxjs';
import { delay } from 'rxjs/operators';

import { ChangePasswordPayload } from '../../../../core/models/auth.model';
import { Phase1StoreService } from '../../../../core/services/phase1-store.service';

@Injectable({
  providedIn: 'root'
})
export class ChangePasswordService {
  constructor(private readonly store: Phase1StoreService) {}

  updatePassword(data: ChangePasswordPayload): Observable<{ success: boolean; message: string }> {
    try {
      return of(this.store.updateCurrentPassword(data)).pipe(delay(300));
    } catch (error) {
      return throwError(() => error);
    }
  }
}
