import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, tap } from 'rxjs';

import { LoginRequest, LoginResponse, SessionUser, UserRole } from '../models/auth.model';
import { buildApiUrl } from '../config/api.config';
import { Phase1StoreService } from './phase1-store.service';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly currentUserSubject: BehaviorSubject<SessionUser | null>;
  readonly currentUser$: Observable<SessionUser | null>;

  private readonly apiUrl = buildApiUrl('/auth');

  constructor(
    private readonly http: HttpClient,
    private readonly store: Phase1StoreService
  ) {
    this.currentUserSubject = new BehaviorSubject<SessionUser | null>(this.store.getCurrentUser());
    this.currentUser$ = this.currentUserSubject.asObservable();
  }

  login(data: LoginRequest & { activeDashboard?: string }): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/login`, data).pipe(
      tap(response => {
        if (response.requiresDashboardSelection) {
          return;
        }
        // Normalize role to lowercase for frontend consistency
        if (response.me && response.me.role) {
          response.me.role = response.me.role.toLowerCase() as UserRole;
        }
        this.store.saveBackendSession(response);
        this.currentUserSubject.next(response.me || null);
      })
    );
  }

  logout(): void {
    this.store.logout();
    this.currentUserSubject.next(null);
  }

  isLoggedIn(): boolean {
    return this.store.isLoggedIn();
  }

  getCurrentUser(): SessionUser | null {
    const latestUser = this.store.getCurrentUser();
    if (latestUser?.id !== this.currentUserSubject.value?.id) {
      this.currentUserSubject.next(latestUser);
    }
    return latestUser;
  }

  getLandingRoute(role: UserRole): string {
    return this.store.getLandingRoute(role);
  }

  getDisplayName(): string {
    return this.getCurrentUser()?.displayName || 'User';
  }

  updateProfileImage(imageUrl: string): void {
    const user = this.getCurrentUser();
    if (user) {
      user.profileImage = imageUrl;
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('aivan_hrms_phase1_user_v1', JSON.stringify(user));
      }
      this.currentUserSubject.next(user);
    }
  }

  forgotPassword(email: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/forgot-password`, { email });
  }

  resetPassword(data: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/reset-password`, data);
  }
}
