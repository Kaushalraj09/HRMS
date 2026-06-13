import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { Phase1StoreService } from './services/phase1-store.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const store = inject(Phase1StoreService);
  const router = inject(Router);
  const token = store.getToken();

  // Only attach the Authorization header if calling our local backend
  const isLocalApi = req.url.startsWith('http://localhost:8000') || req.url.startsWith('/');

  let processedReq = req;
  if (token && isLocalApi) {
    processedReq = req.clone({
      headers: req.headers.set('Authorization', `Bearer ${token}`)
    });
  }

  return next(processedReq).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401 && isLocalApi) {
        // Token has expired or is invalid. Clear the session and redirect to login.
        store.logout();
        router.navigate(['/auth/login']);
      }
      return throwError(() => error);
    })
  );
};
