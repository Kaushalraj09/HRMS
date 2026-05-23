import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router, RouterStateSnapshot } from '@angular/router';

import { UserRole } from '../models/auth.model';
import { AuthService } from '../services/auth.service';

export const roleGuard: CanActivateFn = (route: ActivatedRouteSnapshot, state: RouterStateSnapshot) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const allowedRoles = (route.data['roles'] as UserRole[]) || [];
  const currentUser = authService.getCurrentUser();

  if (!currentUser) {
    return router.createUrlTree(['/auth/login']);
  }

  const url = state.url;

  // Protect HR Dashboard
  if (url.includes('/hr-dashboard')) {
    if (currentUser.role === 'hr') {
      if (currentUser.activeDashboard === 'HR') {
        return true;
      }
      return router.createUrlTree(['/emp-dashboard']);
    }
  }

  // Protect Employee Dashboard
  if (url.includes('/emp-dashboard')) {
    const isEmployeeMode = currentUser.role === 'employee' || currentUser.activeDashboard === 'EMPLOYEE';
    if (isEmployeeMode) {
      return true;
    }
    return router.createUrlTree([authService.getLandingRoute(currentUser.role)]);
  }

  if (!allowedRoles.length || allowedRoles.includes(currentUser.role)) {
    return true;
  }

  return router.createUrlTree([authService.getLandingRoute(currentUser.role)]);
};
