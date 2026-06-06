import { Component, HostListener, EventEmitter, Input, Output, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { Dropdown } from '../dropdown/dropdown';
import { AuthService } from '../../../core/services/auth.service';
import { NotificationService, Notification } from '../../../core/services/notification.service';
import { AttendanceService } from '../../../core/services/attendance.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, Dropdown],
  templateUrl: './navbar.html',
  styleUrl: './navbar.css',
})
export class Navbar implements OnInit, OnDestroy {
  @Input() userName: string = 'User';
  @Input() showSearch: boolean = true;

  @Output() hamburgerClick = new EventEmitter<void>();
  @Output() searchChange = new EventEmitter<string>();
  @Output() profileClick = new EventEmitter<void>();
  @Output() notificationClick = new EventEmitter<void>();

  selectedLang = 'en';
  isOpen = false;
  isProfileDropdownOpen = false;
  isNotificationDropdownOpen = false;
  isLanguageDropdownOpen = false;
  profileImage: string | null = null;
  userInitials: string = 'U';

  notifications: Notification[] = [];
  unreadCount = 0;
  private connectedUserId: string | number | null = null;

  private sub = new Subscription();

  constructor(
    private readonly authService: AuthService,
    private readonly notificationService: NotificationService,
    private readonly attendanceService: AttendanceService,
    private readonly router: Router
  ) {}

  ngOnInit(): void {
    this.sub.add(
      this.authService.currentUser$.subscribe(user => {
        if (user) {
          this.userName = user.displayName;
          this.profileImage = user.profileImage || null;
          
          const names = user.displayName.split(' ');
          const first = names[0]?.[0] || '';
          const last = names[1]?.[0] || '';
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
        this.notifications = notifs;
      })
    );

    this.sub.add(
      this.notificationService.unreadCount$.subscribe(count => {
        this.unreadCount = count;
      })
    );
  }

  loadNotifications(): void {
    this.notificationService.fetchNotifications().subscribe();
    this.notificationService.fetchUnreadCount().subscribe();
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (!target.closest('.profile') && !target.closest('app-dropdown')) {
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

  onSearch(value: string) {
    this.searchChange.emit(value);
  }

  onProfileClick() {
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
    this.notificationClick.emit();
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
    if (notif.type === 'LOGIN_ACTIVITY' && notif.reference_id) {
      this.router.navigate(['/notifications/login-activity', notif.reference_id]);
    }
  }

  getIconClass(type: string): string {
    switch (type) {
      case 'LOGIN_ACTIVITY':
        return 'fas fa-shield-alt';
      case 'ATTENDANCE':
        return 'fas fa-clock';
      case 'LEAVE':
        return 'fas fa-calendar-alt';
      default:
        return 'fas fa-bell';
    }
  }
}
