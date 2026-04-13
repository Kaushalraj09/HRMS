import { Injectable } from '@angular/core';
import { Observable, of, throwError } from 'rxjs';
import { delay } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class ChangePasswordService {

  updatePassword(data: any): Observable<any> {
    // Simulate secure API Call delay naturally
    
    // Simulate server side current password verification error
    if (data.currentPassword === 'wrong') {
       return throwError(() => new Error('Current password is incorrect'));
    }
    
    return of({ success: true, message: 'Password updated successfully' }).pipe(delay(1000));
  }
}
