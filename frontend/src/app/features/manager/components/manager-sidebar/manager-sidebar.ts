import { Component, Input, OnInit, HostListener, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { Observable } from 'rxjs';
import { ManagerSidebarService } from './manager-sidebar.service';
import { AuthService } from '../../../../core/services/auth.service';

export interface MenuItem {
  label: string;
  icon?: string;
  route?: string;
  children?: MenuItem[];
  expanded?: boolean;
  isLogout?: boolean;
  badge?: string;
}

export interface MenuGroup {
  groupName: string;
  items: MenuItem[];
}

@Component({
  selector: 'app-manager-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './manager-sidebar.html',
  styleUrls: ['./manager-sidebar.css'],
  host: {
    '[class.collapsed]': 'collapsed'
  }
})
export class ManagerSidebar implements OnInit {
  isLogoutPopupOpen = false;
  collapsed = false;

  @Input() menuConfig: MenuGroup[] = [
    {
      groupName: 'Manager Dashboard',
      items: [
        { label: 'Manager Dashboard', icon: 'fas fa-chart-line', route: '/manager-dashboard' },
        { label: 'My Team', icon: 'fas fa-users', route: '/manager-dashboard/team' },
        { label: 'Team Attendance', icon: 'fas fa-clock', route: '/manager-dashboard/attendance' },
        { label: 'Leave Approvals', icon: 'fas fa-calendar-check', route: '/manager-dashboard/time-off' },
        { label: 'Employee View', icon: 'fas fa-exchange-alt', route: '/emp-dashboard' },
        { label: 'My Profile', icon: 'far fa-user', route: '/manager-dashboard/my-profile' },
        { label: 'Logout', icon: 'fas fa-sign-out-alt', isLogout: true }
      ]
    }
  ];

  isSidebarOpen$: Observable<boolean>;

  constructor(
    private readonly router: Router,
    private readonly managerSidebarService: ManagerSidebarService,
    private readonly authService: AuthService,
    private readonly cdr: ChangeDetectorRef
  ) {
    this.isSidebarOpen$ = this.managerSidebarService.isSidebarOpen$;
  }

  @HostListener('window:resize')
  onResize(): void {
    this.checkMobileCollapse();
  }

  private checkMobileCollapse(): void {
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      this.managerSidebarService.setSidebarState(false);
    }
  }

  ngOnInit(): void {
    this.checkMobileCollapse();
    this.isSidebarOpen$.subscribe(open => {
      this.collapsed = !open;
      this.cdr.markForCheck();
    });
  }

  handleItemClick(item: MenuItem): void {
    if (item.isLogout) {
      this.isLogoutPopupOpen = true;
      this.cdr.markForCheck();
      return;
    }
    if (item.children) {
      item.expanded = !item.expanded;
      this.cdr.markForCheck();
      return;
    }
    if (item.route) {
      if (item.route === '/emp-dashboard') {
        const user = this.authService.getCurrentUser();
        if (user) {
          user.activeDashboard = 'EMPLOYEE';
          this.authService.saveSession({ me: user });
        }
      }
      this.router.navigate([item.route]);
    }
  }

  isParentActive(item: MenuItem): boolean {
    if (!item.children) return false;
    return item.children.some(child => child.route ? this.router.isActive(child.route, { paths: 'exact', queryParams: 'exact', fragment: 'ignored', matrixParams: 'ignored' }) : false);
  }

  closeLogoutPopup(): void {
    this.isLogoutPopupOpen = false;
    this.cdr.markForCheck();
  }

  confirmLogout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
