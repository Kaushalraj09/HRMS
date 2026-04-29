import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Phase1StoreService } from './services/phase1-store.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const store = inject(Phase1StoreService);
  const token = store.getToken();

  if (token) {
    const clonedReq = req.clone({
      headers: req.headers.set('Authorization', `Bearer ${token}`)
    });
    return next(clonedReq);
  }

  return next(req);
};
