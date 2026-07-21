import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { isAppApiUrl } from './config/api.config';
import { AuthService } from './services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const token = auth.getToken();

  // Only attach the Authorization header if calling our local backend
  const isLocalApi = isAppApiUrl(req.url);

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
        auth.logout();
        router.navigate(['/auth/login']);
      }
      return throwError(() => error);
    })
  );
};
