import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of, throwError } from 'rxjs';
import { delay } from 'rxjs/operators';

import { LoginRequest, LoginResponse, SessionUser, UserRole } from '../models/auth.model';
import { Phase1StoreService } from './phase1-store.service';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly currentUserSubject: BehaviorSubject<SessionUser | null>;
  readonly currentUser$: Observable<SessionUser | null>;

  constructor(private readonly store: Phase1StoreService) {
    this.currentUserSubject = new BehaviorSubject<SessionUser | null>(this.store.getCurrentUser());
    this.currentUser$ = this.currentUserSubject.asObservable();
  }

  login(data: LoginRequest): Observable<LoginResponse> {
    const user = this.store.login(data);

    if (!user) {
      return throwError(() => new Error('Invalid email or password'));
    }

    this.currentUserSubject.next(user);

    return of<LoginResponse>({
      accessToken: `mock-access-token-${user.id}`,
      refreshToken: `mock-refresh-token-${user.id}`,
      tokenType: 'bearer',
      expiresIn: 3600,
      me: user
    }).pipe(delay(300));
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
