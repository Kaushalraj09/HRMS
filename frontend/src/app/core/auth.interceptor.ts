import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Phase1StoreService } from './services/phase1-store.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const store = inject(Phase1StoreService);
  const token = store.getToken();

  // Only attach the Authorization header if calling our local backend
  const isLocalApi = req.url.startsWith('http://localhost:8000') || req.url.startsWith('/');

  if (token && isLocalApi) {
    const clonedReq = req.clone({
      headers: req.headers.set('Authorization', `Bearer ${token}`)
    });
    return next(clonedReq);
  }

  return next(req);
};
