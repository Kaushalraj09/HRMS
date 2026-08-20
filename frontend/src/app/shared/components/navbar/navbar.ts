import { Component, HostListener, EventEmitter, Input, Output, OnInit, OnDestroy, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { Dropdown } from '../dropdown/dropdown';
import { AuthService } from '../../../core/services/auth.service';
import { NotificationService, Notification } from '../../../core/services/notification.service';
import { AttendanceService } from '../../../core/services/attendance.service';
import { TimeEngineService } from '../../../core/services/time-engine.service';
import { Subject, Subscription, debounceTime, distinctUntilChanged, map } from 'rxjs';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, Dropdown],
  templateUrl: './navbar.html',
  styleUrl: './navbar.css',
})
export class Navbar implements OnInit, OnDestroy, OnChanges {
  @Input() userName: string = 'System Admin';
  @Input() userRole: string = 'Software Engineer';
  @Input() showSearch: boolean = true;
  @Input() searchValue: string = '';

  @Output() hamburgerClick = new EventEmitter<void>();
  @Output() searchChange = new EventEmitter<string>();
  @Output() profileClick = new EventEmitter<void>();

  selectedLang = 'en';
  isOpen = false;
  isProfileDropdownOpen = false;
  isNotificationDropdownOpen = false;
  isLanguageDropdownOpen = false;
  profileImage: string | null = null;
  userInitials: string = 'U';
  isPunchedIn = false;

  // New notification fields
  currentFilterTab = 'all'; // 'all' | 'attendance' | 'leave' | 'unread'
  notificationSearchTerm = '';
  notificationPage = 1;
  hasMoreNotifications = true;
  loadingNotifications = false;

  notifications: any[] = [];
  unreadCount = 0;
  private connectedUserId: string | number | null = null;
  searchTerm = '';
  private readonly searchInput$ = new Subject<string>();

  private sub = new Subscription();

  constructor(
    private readonly authService: AuthService,
    private readonly notificationService: NotificationService,
    private readonly attendanceService: AttendanceService,
    private readonly timeEngine: TimeEngineService,
    private readonly router: Router
  ) {}

  ngOnInit(): void {
    this.searchTerm = this.searchValue || '';

    this.sub.add(
      this.searchInput$.pipe(
        map(value => value.trim()),
        debounceTime(150),
        distinctUntilChanged()
      ).subscribe(value => {
        this.searchChange.emit(value);
      })
    );

    this.sub.add(
      this.timeEngine.state$.subscribe(state => {
        this.isPunchedIn = !!state?.isWorking;
      })
    );

    this.sub.add(
      this.authService.currentUser$.subscribe(user => {
        if (user) {
          this.userName = user.displayName;
          this.profileImage = user.profileImage || null;
          
          const names = (user.displayName || '').trim().split(/\s+/).filter(Boolean);
          const first = names[0]?.[0] || '';
          const last = names.length > 1 ? names[names.length - 1]?.[0] || '' : '';
          this.userInitials = (first + last).toUpperCase() || 'U';

          // Connect WebSocket if not connected for this user
          if (this.connectedUserId !== user.id) {
            this.connectedUserId = user.id;
            this.attendanceService.connectWebSocket(user.id);
          }

          // Initial load of notifications
          this.loadNotifications();
        } else {
          this.connectedUserId = null;
          this.attendanceService.disconnectWebSocket();
        }
      })
    );

    // Subscribe to notification service updates (BehaviorSubjects)
    this.sub.add(
      this.notificationService.notifications$.subscribe(notifs => {
        setTimeout(() => {
          this.notifications = notifs;
        });
      })
    );

    this.sub.add(
      this.notificationService.unreadCount$.subscribe(count => {
        setTimeout(() => {
          this.unreadCount = count;
        });
      })
    );
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['searchValue'] && changes['searchValue'].currentValue !== this.searchTerm) {
      this.searchTerm = changes['searchValue'].currentValue || '';
    }
  }

  loadNotifications(): void {
    this.loadNotificationsWithFilters();
    this.notificationService.fetchUnreadCount().subscribe();
  }

  loadNotificationsWithFilters(append: boolean = false) {
    this.loadingNotifications = true;
    let category: string | undefined = undefined;
    let isRead: boolean | undefined = undefined;
    
    if (this.currentFilterTab === 'attendance') {
      category = 'ATTENDANCE';
    } else if (this.currentFilterTab === 'leave') {
      category = 'LEAVE';
    } else if (this.currentFilterTab === 'unread') {
      isRead = false;
    }
    
    const pageToLoad = append ? this.notificationPage + 1 : 1;
    const limit = 15;
    
    this.notificationService.fetchNotifications(
      limit,
      pageToLoad,
      category,
      isRead,
      this.notificationSearchTerm || undefined
    ).subscribe({
      next: (notifs) => {
        this.loadingNotifications = false;
        if (notifs.length < limit) {
          this.hasMoreNotifications = false;
        } else {
          this.hasMoreNotifications = true;
        }
        if (append) {
          this.notificationPage = pageToLoad;
        } else {
          this.notificationPage = 1;
        }
      },
      error: (err) => {
        this.loadingNotifications = false;
        console.error('Error loading notifications', err);
      }
    });
  }

  setNotificationTab(tab: string) {
    this.currentFilterTab = tab;
    this.notificationPage = 1;
    this.hasMoreNotifications = true;
    this.loadNotificationsWithFilters();
  }

  onNotificationSearch(event: Event) {
    const val = (event.target as HTMLInputElement).value;
    this.notificationSearchTerm = val;
    this.notificationPage = 1;
    this.hasMoreNotifications = true;
    this.loadNotificationsWithFilters();
  }

  clearNotificationSearch() {
    this.notificationSearchTerm = '';
    this.notificationPage = 1;
    this.hasMoreNotifications = true;
    this.loadNotificationsWithFilters();
  }

  getGroupedNotifications() {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    yesterday.setHours(0, 0, 0, 0);
    
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    sevenDaysAgo.setHours(0, 0, 0, 0);

    const groups: { [key: string]: { label: string; items: any[] } } = {
      today: { label: 'Today', items: [] },
      yesterday: { label: 'Yesterday', items: [] },
      week: { label: 'Last 7 Days', items: [] },
      older: { label: 'Older', items: [] }
    };

    for (const notif of this.notifications) {
      const createdDate = new Date(notif.created_at);
      createdDate.setHours(0, 0, 0, 0);
      
      if (createdDate.getTime() === today.getTime()) {
        groups['today'].items.push(notif);
      } else if (createdDate.getTime() === yesterday.getTime()) {
        groups['yesterday'].items.push(notif);
      } else if (createdDate.getTime() >= sevenDaysAgo.getTime()) {
        groups['week'].items.push(notif);
      } else {
        groups['older'].items.push(notif);
      }
    }

    return Object.keys(groups)
      .map(key => ({ key, label: groups[key].label, items: groups[key].items }))
      .filter(g => g.items.length > 0);
  }

  clearAllNotifications(event: MouseEvent) {
    event.stopPropagation();
    if (confirm('Are you sure you want to clear all notifications?')) {
      this.notificationService.clearAllNotifications().subscribe();
    }
  }

  deleteNotification(event: MouseEvent, notifId: number) {
    event.stopPropagation();
    this.notificationService.deleteNotification(notifId).subscribe();
  }

  markSingleAsRead(event: MouseEvent, notifId: number) {
    event.stopPropagation();
    this.notificationService.markAsRead(notifId).subscribe();
  }

  getSeverityClass(severity: string | undefined): string {
    if (!severity) return 'severity-info';
    return `severity-${severity.toLowerCase()}`;
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (!target.closest('.profile-user-pill') && !target.closest('app-dropdown')) {
      this.isProfileDropdownOpen = false;
    }
    if (!target.closest('.notification-container')) {
      this.isNotificationDropdownOpen = false;
    }
    if (!target.closest('.language-selector')) {
      this.isLanguageDropdownOpen = false;
    }
  }

  onHamburgerClick() {
    this.hamburgerClick.emit();
    this.isOpen = !this.isOpen;
  }

  onSearchInput(event: Event) {
    const value = (event.target as HTMLInputElement).value;
    this.searchTerm = value;
    this.searchInput$.next(value);
  }

  clearSearch(event?: Event) {
    event?.stopPropagation();
    this.searchTerm = '';
    this.searchInput$.next('');
  }

  onProfileClick(event?: MouseEvent) {
    event?.stopPropagation();
    this.isProfileDropdownOpen = !this.isProfileDropdownOpen;
    this.isNotificationDropdownOpen = false;
    this.isLanguageDropdownOpen = false;
    this.profileClick.emit();
  }

  toggleLanguageDropdown(event: MouseEvent) {
    event.stopPropagation();
    this.isLanguageDropdownOpen = !this.isLanguageDropdownOpen;
    this.isProfileDropdownOpen = false;
    this.isNotificationDropdownOpen = false;
  }

  selectLanguage(lang: string, event: MouseEvent) {
    event.stopPropagation();
    this.selectedLang = lang;
    this.isLanguageDropdownOpen = false;
  }

  toggleNotificationDropdown(event: MouseEvent) {
    event.stopPropagation();
    this.isNotificationDropdownOpen = !this.isNotificationDropdownOpen;
    if (this.isNotificationDropdownOpen) {
      // Reload on open
      this.loadNotifications();
    }
  }

  markAllAsRead(event: MouseEvent) {
    event.stopPropagation();
    this.notificationService.markAllAsRead().subscribe();
  }

  onNotificationItemClick(notif: Notification) {
    this.isNotificationDropdownOpen = false;
    
    // Mark as read
    if (!notif.is_read) {
      this.notificationService.markAsRead(notif.id).subscribe();
    }

    // Redirect based on type
    const targetRoute = this.getNotificationTargetRoute(notif);
    if (targetRoute) {
      this.router.navigate(targetRoute);
    }
  }

  private getActiveDashboardBaseRoute(): string | null {
    const currentUrl = this.router.url;
    if (currentUrl.startsWith('/master-dashboard')) {
      return '/master-dashboard';
    }
    if (currentUrl.startsWith('/hr-dashboard')) {
      return '/hr-dashboard';
    }
    if (currentUrl.startsWith('/emp-dashboard')) {
      return '/emp-dashboard';
    }

    const user = this.authService.getCurrentUser();
    if (!user) {
      return null;
    }

    if (user.role === 'admin') {
      return '/master-dashboard';
    }
    if (user.role === 'hr') {
      return '/hr-dashboard';
    }
    return '/emp-dashboard';
  }

  private getNotificationTargetRoute(notif: any): string[] | null {
    const baseRoute = this.getActiveDashboardBaseRoute();
    if (!baseRoute) {
      return null;
    }

    const type = (notif.type || '').toUpperCase();
    const category = (notif.category || '').toUpperCase();

    if (type === 'ATTENDANCE' || category === 'LOGIN' || category === 'PUNCH_IN' || category === 'PUNCH_OUT') {
      return baseRoute === '/emp-dashboard'
        ? ['/emp-dashboard', 'my-attendance']
        : [baseRoute, 'attendance'];
    }

    if (type === 'LEAVE' || category.startsWith('LEAVE_')) {
      return baseRoute === '/emp-dashboard'
        ? ['/emp-dashboard']
        : [baseRoute, 'attendance'];
    }

    if (type === 'TIMEOFF_APPLY' || type === 'TIMEOFF_REQUEST' || type === 'TIMEOFF_UPDATE') {
      return baseRoute === '/emp-dashboard'
        ? ['/emp-dashboard']
        : [baseRoute, 'attendance'];
    }

    if (type === 'ATTENDANCE_AUTO_CHECKOUT') {
      return baseRoute === '/emp-dashboard'
        ? ['/emp-dashboard', 'my-attendance']
        : [baseRoute];
    }

    if (type === 'TIMEOFF_EXPIRED' || type === 'TIMEOFF_REMINDER') {
      return [baseRoute];
    }

    return null;
  }

  getIconClass(type: string, category?: string): string {
    const t = (type || '').toUpperCase();
    const c = (category || '').toUpperCase();

    if (c === 'LOGIN' || t === 'LOGIN_ACTIVITY') {
      return 'fas fa-sign-in-alt';
    }
    if (c === 'PUNCH_IN') {
      return 'fas fa-clock';
    }
    if (c === 'PUNCH_OUT') {
      return 'fas fa-sign-out-alt';
    }
    if (c === 'LEAVE_REQUEST' || t === 'TIMEOFF_REQUEST' || t === 'TIMEOFF_APPLY') {
      return 'fas fa-calendar-plus';
    }
    if (c === 'LEAVE_APPROVED') {
      return 'fas fa-check-circle';
    }
    if (c === 'LEAVE_REJECTED') {
      return 'fas fa-times-circle';
    }
    if (c === 'LEAVE_CANCELLED') {
      return 'fas fa-ban';
    }
    if (t === 'SYSTEM') {
      return 'fas fa-cog';
    }
    if (t === 'ATTENDANCE_AUTO_CHECKOUT') {
      return 'fas fa-sign-out-alt';
    }
    if (t === 'SHIFT_END_REMINDER') {
      return 'fas fa-hourglass-end';
    }
    if (t === 'OVERTIME_REMINDER') {
      return 'fas fa-exclamation-circle';
    }
    if (t === 'TIMEOFF_EXPIRED') {
      return 'fas fa-calendar-times';
    }
    return 'fas fa-bell';
  }

  formatCategory(category?: string, type?: string): string {
    const raw = (category || type || 'SYSTEM').toUpperCase();
    const map: Record<string, string> = {
      'LOGIN': 'Login',
      'LOGIN_ACTIVITY': 'Login Activity',
      'PUNCH_IN': 'Punch In',
      'PUNCH_OUT': 'Punch Out',
      'ATTENDANCE': 'Attendance',
      'ATTENDANCE_AUTO_CHECKOUT': 'Auto Checkout',
      'LEAVE': 'Leave',
      'LEAVE_REQUEST': 'Leave Request',
      'LEAVE_APPROVED': 'Leave Approved',
      'LEAVE_REJECTED': 'Leave Rejected',
      'LEAVE_CANCELLED': 'Leave Cancelled',
      'TIMEOFF_APPLY': 'Time Off',
      'TIMEOFF_REQUEST': 'Time Off',
      'TIMEOFF_UPDATE': 'Time Off Update',
      'TIMEOFF_EXPIRED': 'Time Off Expired',
      'TIMEOFF_REMINDER': 'Time Off Reminder',
      'SHIFT_END_REMINDER': 'Shift End',
      'OVERTIME_REMINDER': 'Overtime Alert',
      'SYSTEM': 'System'
    };

    if (map[raw]) {
      return map[raw];
    }
    return raw.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
  }

  getCategoryTheme(category?: string, type?: string): string {
    const raw = (category || type || 'SYSTEM').toUpperCase();
    if (raw.includes('LOGIN')) return 'theme-blue';
    if (raw.includes('PUNCH') || raw.includes('ATTENDANCE') || raw.includes('APPROVED')) return 'theme-green';
    if (raw.includes('LEAVE') || raw.includes('TIMEOFF')) return 'theme-purple';
    if (raw.includes('REMINDER') || raw.includes('ALERT')) return 'theme-amber';
    if (raw.includes('REJECTED') || raw.includes('CANCELLED') || raw.includes('ERROR')) return 'theme-red';
    return 'theme-slate';
  }

  getCategoryBadgeClass(category?: string): string {
    const raw = (category || '').toUpperCase();
    if (raw.includes('LOGIN')) return 'badge-blue';
    if (raw.includes('PUNCH') || raw.includes('ATTENDANCE') || raw.includes('APPROVED')) return 'badge-green';
    if (raw.includes('LEAVE') || raw.includes('TIMEOFF')) return 'badge-purple';
    if (raw.includes('REMINDER') || raw.includes('ALERT')) return 'badge-amber';
    if (raw.includes('REJECT') || raw.includes('CANCEL') || raw.includes('ERROR')) return 'badge-red';
    return 'badge-gray';
  }

  formatNotifTime(dateStr?: string): string {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24 && d.getDate() === now.getDate()) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ', ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
}
