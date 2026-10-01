import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, tap } from 'rxjs';

import { LoginRequest, LoginResponse, SessionUser, UserRole, ForgotPasswordPayload, ResetPasswordPayload, StandardResponse } from '../models/auth.model';
import { buildApiUrl } from '../config/api.config';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly currentUserSubject: BehaviorSubject<SessionUser | null>;
  readonly currentUser$: Observable<SessionUser | null>;

  private readonly apiUrl = buildApiUrl('/auth');
  
  private readonly tokenKey = 'aivan_hrms_phase1_token_v1';
  private readonly userKey = 'aivan_hrms_phase1_user_v1';
  private readonly sessionKey = 'aivan_hrms_phase1_session_v1';

  constructor(
    private readonly http: HttpClient
  ) {
    let initialUser: SessionUser | null = null;
    // Prefer tab-isolated sessionStorage so each browser tab maintains its own independent session
    if (typeof sessionStorage !== 'undefined') {
      const stored = sessionStorage.getItem(this.userKey);
      if (stored) {
        try {
          initialUser = JSON.parse(stored);
        } catch (e) {}
      }
    }
    // Fallback to localStorage only if sessionStorage is empty (user profile cache only, not JWT token)
    if (!initialUser && typeof localStorage !== 'undefined') {
      const stored = localStorage.getItem(this.userKey);
      if (stored) {
        try {
          initialUser = JSON.parse(stored);
          if (initialUser && typeof sessionStorage !== 'undefined') {
            sessionStorage.setItem(this.userKey, stored);
          }
        } catch (e) {}
      }
    }

    this.currentUserSubject = new BehaviorSubject<SessionUser | null>(initialUser);
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
        this.saveSession(response);
        this.currentUserSubject.next(response.me || null);
      })
    );
  }

  saveSession(response: LoginResponse): void {
    // Store in tab-scoped sessionStorage so multiple tabs can be logged into different users
    // and prevent XSS persistent token exfiltration from localStorage
    if (typeof sessionStorage !== 'undefined') {
      try {
        if (response.me) {
          sessionStorage.setItem(this.userKey, JSON.stringify(response.me));
          sessionStorage.setItem(this.sessionKey, String(response.me.id));
        }
        if (response.accessToken) {
          sessionStorage.setItem(this.tokenKey, response.accessToken);
        }
      } catch (e) {}
    }

    // Keep only user profile metadata in localStorage for offline/tab-restoration; DO NOT store JWT
    if (typeof localStorage !== 'undefined') {
      try {
        if (response.me) {
          localStorage.setItem(this.userKey, JSON.stringify(response.me));
          localStorage.setItem(this.sessionKey, String(response.me.id));
        }
        // Clean up any legacy token that may exist
        localStorage.removeItem(this.tokenKey);
      } catch (e) {}
    }
  }

  getToken(): string | null {
    if (typeof sessionStorage !== 'undefined') {
      return sessionStorage.getItem(this.tokenKey);
    }
    return null;
  }

  logout(): void {
    this.http.post<StandardResponse>(`${this.apiUrl}/logout`, {}).subscribe({ error: () => undefined });
    // Clear only this tab's session
    if (typeof sessionStorage !== 'undefined') {
      try {
        sessionStorage.removeItem(this.userKey);
        sessionStorage.removeItem(this.sessionKey);
        sessionStorage.removeItem(this.tokenKey);
      } catch (e) {}
    }
    if (typeof localStorage !== 'undefined') {
      try {
        localStorage.removeItem(this.userKey);
        localStorage.removeItem(this.sessionKey);
        localStorage.removeItem(this.tokenKey);
      } catch (e) {}
    }
    this.currentUserSubject.next(null);
  }

  isLoggedIn(): boolean {
    return !!this.getCurrentUser();
  }

  getCurrentUser(): SessionUser | null {
    // Check sessionStorage first for tab isolation
    if (typeof sessionStorage !== 'undefined') {
      try {
        const stored = sessionStorage.getItem(this.userKey);
        if (stored) {
          const user = JSON.parse(stored);
          if (user) {
            if (user?.id !== this.currentUserSubject.value?.id) {
              this.currentUserSubject.next(user);
            }
            return user;
          }
        }
      } catch (e) {}
    }

    // Fallback to localStorage
    if (typeof localStorage !== 'undefined') {
      try {
        const stored = localStorage.getItem(this.userKey);
        if (stored) {
          const user = JSON.parse(stored);
          if (user) {
            if (user?.id !== this.currentUserSubject.value?.id) {
              this.currentUserSubject.next(user);
            }
            return user;
          }
        }
      } catch (e) {}
    }
    return null;
  }

  getLandingRoute(role: UserRole): string {
    const roleLower = role?.toLowerCase();
    if (roleLower === 'admin') {
      return '/master-dashboard';
    }
    // All employees, HR, and Managers land on their personal Employee Dashboard first
    return '/emp-dashboard';
  }

  getDisplayName(): string {
    return this.getCurrentUser()?.displayName || 'User';
  }

  updateProfileImage(imageUrl: string): void {
    const user = this.getCurrentUser();
    if (user) {
      user.profileImage = imageUrl;
      if (typeof sessionStorage !== 'undefined') {
        sessionStorage.setItem(this.userKey, JSON.stringify(user));
      }
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(this.userKey, JSON.stringify(user));
      }
      this.currentUserSubject.next(user);
    }
  }

  forgotPassword(email: string): Observable<StandardResponse> {
    return this.http.post<StandardResponse>(`${this.apiUrl}/forgot-password`, { email } as ForgotPasswordPayload);
  }

  resetPassword(data: ResetPasswordPayload): Observable<StandardResponse> {
    return this.http.post<StandardResponse>(`${this.apiUrl}/reset-password`, data);
  }
}
