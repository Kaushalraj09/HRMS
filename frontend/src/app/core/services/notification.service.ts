import { Injectable, OnDestroy } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject, Subscription } from 'rxjs';
import { tap } from 'rxjs/operators';
import { buildApiUrl } from '../config/api.config';
import { AttendanceService } from './attendance.service';

export interface Notification {
  id: number;
  user_id: number;
  type: string;
  title: string;
  message: string;
  reference_id?: number;
  is_read: boolean;
  created_at: string;
  read_at?: string;
  updated_at?: string;
  category?: string;
  severity?: string;
  employee_id?: number;
  created_by?: number;
  receiver_role?: string;
  notification_metadata?: any;
  employee?: {
    id: number;
    first_name: string;
    last_name: string;
    full_name: string;
    avatar?: string;
  };
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

  fetchNotifications(
    limit: number = 50,
    page: number = 1,
    category?: string,
    isRead?: boolean,
    search?: string
  ): Observable<Notification[]> {
    let params = new HttpParams()
      .set('limit', limit.toString())
      .set('page', page.toString());
      
    if (category) {
      params = params.set('category', category);
    }
    if (isRead !== undefined) {
      params = params.set('is_read', isRead.toString());
    }
    if (search) {
      params = params.set('search', search);
    }

    return this.http.get<Notification[]>(this.apiUrl, { params }).pipe(
      tap(notifs => {
        if (page === 1) {
          this.notificationsSubject.next(notifs);
        } else {
          const current = this.notificationsSubject.value;
          const merged = [...current];
          for (const n of notifs) {
            if (!merged.some(item => item.id === n.id)) {
              merged.push(n);
            }
          }
          this.notificationsSubject.next(merged);
        }
      })
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

  clearAllNotifications(): Observable<any> {
    return this.http.delete(`${this.apiUrl}/clear-all`).pipe(
      tap(() => {
        this.notificationsSubject.next([]);
        this.unreadCountSubject.next(0);
      })
    );
  }

  deleteNotification(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}`).pipe(
      tap(() => {
        const current = this.notificationsSubject.value;
        const deletedNotif = current.find(n => n.id === id);
        const updatedList = current.filter(n => n.id !== id);
        this.notificationsSubject.next(updatedList);
        
        if (deletedNotif && !deletedNotif.is_read) {
          this.unreadCountSubject.next(Math.max(0, this.unreadCountSubject.value - 1));
        }
        this.fetchUnreadCount().subscribe();
      })
    );
  }

  ngOnDestroy() {
    if (this.wsSubscription) {
      this.wsSubscription.unsubscribe();
    }
  }
}

