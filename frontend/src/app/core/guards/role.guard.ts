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
    const isHr = currentUser.role === 'hr' ||
                 currentUser.role === 'admin' ||
                 (currentUser.accessibleDashboards && currentUser.accessibleDashboards.includes('HR'));
    if (isHr) {
      if (currentUser.activeDashboard !== 'HR') {
        currentUser.activeDashboard = 'HR';
        authService.saveSession({ me: currentUser });
      }
      return true;
    }
    return router.createUrlTree([authService.getLandingRoute(currentUser.role)]);
  }

  // Protect Manager Dashboard
  if (url.includes('/manager-dashboard')) {
    const isManager = currentUser.role === 'manager' ||
                      currentUser.role === 'admin' ||
                      currentUser.isManager === true ||
                      (currentUser.accessibleDashboards && currentUser.accessibleDashboards.includes('MANAGER'));
    if (isManager) {
      if (currentUser.activeDashboard !== 'MANAGER') {
        currentUser.activeDashboard = 'MANAGER';
        authService.saveSession({ me: currentUser });
      }
      return true;
    }
    return router.createUrlTree([authService.getLandingRoute(currentUser.role)]);
  }

  // Protect Employee Dashboard
  if (url.includes('/emp-dashboard')) {
    const isEmployeeMode = currentUser.role === 'employee' ||
                           currentUser.role === 'admin' ||
                           currentUser.role === 'manager' ||
                           currentUser.role === 'hr' ||
                           currentUser.isManager === true ||
                           currentUser.activeDashboard === 'EMPLOYEE' ||
                           (currentUser.accessibleDashboards && currentUser.accessibleDashboards.includes('EMPLOYEE'));
    if (!isEmployeeMode) {
      return router.createUrlTree([authService.getLandingRoute(currentUser.role)]);
    }

    // Verify manager privileges for manager-specific routes
    const isManagerRoute = url.includes('/emp-dashboard/manager-dashboard') ||
                           url.includes('/emp-dashboard/team') ||
                           url.includes('/emp-dashboard/team-attendance') ||
                           url.includes('/emp-dashboard/leave-approvals');
    if (isManagerRoute) {
      const isManager = currentUser.role === 'manager' ||
                        currentUser.role === 'admin' ||
                        currentUser.isManager === true ||
                        (currentUser.accessibleDashboards && currentUser.accessibleDashboards.includes('MANAGER'));
      if (!isManager) {
        return router.createUrlTree(['/emp-dashboard']);
      }
    }

    // Verify HR privileges for hr-specific routes inside emp-dashboard
    if (url.includes('/emp-dashboard/hr-')) {
      const isHr = currentUser.role === 'hr' ||
                   currentUser.role === 'admin' ||
                   (currentUser.accessibleDashboards && currentUser.accessibleDashboards.includes('HR'));
      if (!isHr) {
        return router.createUrlTree(['/emp-dashboard']);
      }
    }

    return true;
  }

  const isAllowed = !allowedRoles.length ||
                    allowedRoles.includes(currentUser.role) ||
                    (currentUser.isManager && allowedRoles.includes('manager'));
  if (isAllowed) {
    return true;
  }

  return router.createUrlTree([authService.getLandingRoute(currentUser.role)]);
};
