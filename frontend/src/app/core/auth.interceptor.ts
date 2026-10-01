import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { isAppApiUrl } from './config/api.config';
import { AuthService } from './services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  // Send the HttpOnly session cookie only to this application's API.
  const isLocalApi = isAppApiUrl(req.url);

  let processedReq = req;
  if (isLocalApi) {
    const token = auth.getToken();
    const setHeaders: Record<string, string> = {
      'X-Requested-With': 'XMLHttpRequest'
    };
    if (token) {
      setHeaders['Authorization'] = `Bearer ${token}`;
    }
    processedReq = req.clone({
      withCredentials: true,
      setHeaders
    });
  }

  return next(processedReq).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401 && isLocalApi && !req.url.endsWith('/auth/logout')) {
        // Token has expired or is invalid. Clear the session and redirect to login.
        auth.logout();
        router.navigate(['/auth/login']);
      }
      return throwError(() => error);
    })
  );
};
