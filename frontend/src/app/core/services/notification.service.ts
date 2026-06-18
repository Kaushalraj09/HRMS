import { Injectable, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, Subscription } from 'rxjs';
import { tap } from 'rxjs/operators';
import { buildApiUrl } from '../config/api.config';
import { AttendanceService } from './attendance.service';

export interface Notification {
  id: number;
  user_id: number;
  type: 'LOGIN_ACTIVITY' | 'ATTENDANCE' | 'LEAVE' | 'SYSTEM' | 'TIMEOFF_APPLY' | 'TIMEOFF_REQUEST' | 'TIMEOFF_UPDATE' | 'ATTENDANCE_AUTO_CHECKOUT' | 'TIMEOFF_EXPIRED' | 'TIMEOFF_REMINDER';
  title: string;
  message: string;
  reference_id?: number;
  is_read: boolean;
  created_at: string;
  read_at?: string;
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService implements OnDestroy {
  private readonly apiUrl = buildApiUrl('/notifications');
  
  private notificationsSubject = new BehaviorSubject<Notification[]>([]);
  public notifications$ = this.notificationsSubject.asObservable();
  
  private unreadCountSubject = new BehaviorSubject<number>(0);
  public unreadCount$ = this.unreadCountSubject.asObservable();
  
  private wsSubscription: Subscription | null = null;

  constructor(
    private readonly http: HttpClient,
    private readonly attendanceService: AttendanceService
  ) {
    this.wsSubscription = this.attendanceService.wsMessage$.subscribe(msg => {
      if (msg && msg.type === 'NEW_NOTIFICATION') {
        const notif: Notification = msg.notification;
        const currentList = this.notificationsSubject.value;
        if (!currentList.some(n => n.id === notif.id)) {
          this.notificationsSubject.next([notif, ...currentList]);
          this.unreadCountSubject.next(this.unreadCountSubject.value + 1);
        }
      }
    });
  }

  fetchNotifications(): Observable<Notification[]> {
    return this.http.get<Notification[]>(this.apiUrl).pipe(
      tap(notifs => this.notificationsSubject.next(notifs))
    );
  }

  fetchUnreadCount(): Observable<{ unread_count: number }> {
    return this.http.get<{ unread_count: number }>(`${this.apiUrl}/unread-count`).pipe(
      tap(res => this.unreadCountSubject.next(res.unread_count))
    );
  }

  markAsRead(id: number): Observable<Notification> {
    return this.http.put<Notification>(`${this.apiUrl}/${id}/mark-read`, {}).pipe(
      tap(updated => {
        const updatedList = this.notificationsSubject.value.map(n => 
          n.id === id ? { ...n, is_read: true } : n
        );
        this.notificationsSubject.next(updatedList);
        
        const currentCount = this.unreadCountSubject.value;
        this.unreadCountSubject.next(Math.max(0, currentCount - 1));
        
        // Fetch fresh unread count from backend in the background to ensure consistency
        this.fetchUnreadCount().subscribe();
      })
    );
  }

  markAllAsRead(): Observable<{ unread_count: number }> {
    return this.http.put<{ unread_count: number }>(`${this.apiUrl}/mark-all-read`, {}).pipe(
      tap(res => {
        const updatedList = this.notificationsSubject.value.map(n => ({
          ...n,
          is_read: true
        }));
        this.notificationsSubject.next(updatedList);
        this.unreadCountSubject.next(res.unread_count);
      })
    );
  }

  ngOnDestroy() {
    if (this.wsSubscription) {
      this.wsSubscription.unsubscribe();
    }
  }
}
