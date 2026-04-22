import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, tap } from 'rxjs';

import { LoginRequest, LoginResponse, SessionUser, UserRole } from '../models/auth.model';
import { Phase1StoreService } from './phase1-store.service';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly currentUserSubject: BehaviorSubject<SessionUser | null>;
  readonly currentUser$: Observable<SessionUser | null>;

  private readonly apiUrl = 'http://localhost:8000/api/v1/auth';

  constructor(
    private readonly http: HttpClient,
    private readonly store: Phase1StoreService
  ) {
    this.currentUserSubject = new BehaviorSubject<SessionUser | null>(this.store.getCurrentUser());
    this.currentUser$ = this.currentUserSubject.asObservable();
  }

  login(data: LoginRequest): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/login`, data).pipe(
      tap(response => {
        // Normalize role to lowercase for frontend consistency
        if (response.me && response.me.role) {
          response.me.role = response.me.role.toLowerCase() as UserRole;
        }
        this.store.saveBackendSession(response);
        this.currentUserSubject.next(response.me);
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
}
