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

  private get storage(): Storage | null {
    return typeof sessionStorage !== 'undefined' ? sessionStorage : null;
  }

  constructor(
    private readonly http: HttpClient
  ) {
    let initialUser: SessionUser | null = null;
    const storage = this.storage;
    if (storage) {
      const stored = storage.getItem(this.userKey);
      if (stored) {
        try { initialUser = JSON.parse(stored); } catch (e) {}
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
    const storage = this.storage;
    if (storage) {
      if (response.accessToken) {
        storage.setItem(this.tokenKey, response.accessToken);
      }
      if (response.me) {
        storage.setItem(this.userKey, JSON.stringify(response.me));
        storage.setItem(this.sessionKey, String(response.me.id));
      }
    }
  }

  logout(): void {
    const storage = this.storage;
    if (storage) {
      storage.removeItem(this.tokenKey);
      storage.removeItem(this.userKey);
      storage.removeItem(this.sessionKey);
    }
    this.currentUserSubject.next(null);
  }

  isLoggedIn(): boolean {
    return !!this.storage?.getItem(this.tokenKey);
  }

  getToken(): string | null {
    return this.storage?.getItem(this.tokenKey) ?? null;
  }

  getCurrentUser(): SessionUser | null {
    const storage = this.storage;
    if (storage) {
      const stored = storage.getItem(this.userKey);
      if (stored) {
        try {
          const user = JSON.parse(stored);
          if (user?.id !== this.currentUserSubject.value?.id) {
            this.currentUserSubject.next(user);
          }
          return user;
        } catch (e) {}
      }
    }
    return null;
  }

  getLandingRoute(role: UserRole): string {
    const roleLower = role?.toLowerCase();
    if (roleLower === 'admin') {
      return '/master-dashboard';
    } else if (roleLower === 'hr') {
      const user = this.getCurrentUser();
      if (user && user.activeDashboard === 'EMPLOYEE') {
        return '/emp-dashboard';
      }
      return '/hr-dashboard';
    } else {
      return '/emp-dashboard';
    }
  }

  getDisplayName(): string {
    return this.getCurrentUser()?.displayName || 'User';
  }

  updateProfileImage(imageUrl: string): void {
    const user = this.getCurrentUser();
    if (user) {
      user.profileImage = imageUrl;
      this.storage?.setItem(this.userKey, JSON.stringify(user));
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
