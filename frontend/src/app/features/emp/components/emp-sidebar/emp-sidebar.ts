import { Component, Input, OnInit, HostListener, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { EmpSidebarService } from './emp-sidebar.service';
import { AuthService } from '../../../../core/services/auth.service';
import { SessionUser } from '../../../../core/models/auth.model';

export interface MenuItem {
  label: string;
  icon?: string;
  route?: string;
  children?: MenuItem[];
  expanded?: boolean;
  isLogout?: boolean;
}

export interface MenuGroup {
  groupName: string;
  items: MenuItem[];
}

@Component({
  selector: 'app-emp-sidebar',
  imports: [CommonModule, RouterModule],
  templateUrl: './emp-sidebar.html',
  styleUrl: './emp-sidebar.css',
  host: {
    '[class.collapsed]': 'collapsed'
  }
})
export class EmpSidebar implements OnInit {
  isLogoutPopupOpen = false;
  collapsed = false;

  @Input() menuConfig: MenuGroup[] = [
    { 
      groupName: 'Dashboard',
      items: [ 
        { label: 'Dashboard', icon: 'fas fa-tachometer-alt', route: '/emp-dashboard' },
        { label: 'My Attendance', icon: 'fas fa-calendar-check', route: '/emp-dashboard/my-attendance' },
        { label: 'My Documents', icon: 'fas fa-folder-open', route: '/emp-dashboard/my-documents' },
        { label: 'Time Off', icon: 'fas fa-clock', route: '/emp-dashboard/time-off' },
        { label: 'Regularization', icon: 'fas fa-business-time', route: '/emp-dashboard/regularization' },
        { label: 'My Payroll', icon: 'fas fa-file-invoice-dollar', route: '/emp-dashboard/my-payroll' },
        { label: 'My Trainings', icon: 'fas fa-graduation-cap', route: '/emp-dashboard/my-trainings' },
        { label: 'My Profile', icon: 'far fa-user', route: '/emp-dashboard/my-profile' },
        { label: 'Change Password', icon: 'fas fa-key', route: '/emp-dashboard/change-password' },
        { label: 'Logout', icon: 'fas fa-sign-out-alt', isLogout: true }
      ]
    }
  ];

  isEmpSidebarOpen$!: import('rxjs').Observable<boolean>;

  constructor(
    private empSidebarService: EmpSidebarService, 
    private router: Router, 
    private readonly authService: AuthService,
    private readonly cdr: ChangeDetectorRef
  ) {
    this.isEmpSidebarOpen$ = this.empSidebarService.isEmpSidebarOpen$;
  }

  @HostListener('window:resize', ['$event'])
  onResize(event: any) {
    this.checkMobileCollapse();
  }

  checkMobileCollapse(): void {
    if (typeof window !== 'undefined' && window.innerWidth <= 768) {
      this.empSidebarService.setSidebarState(false);
    }
  }

  handleItemClick(item: MenuItem, event?: Event): void {
    if (item.isLogout) {
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }
      this.isLogoutPopupOpen = true;
      return;
    }
    if (item.children) {
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }
      item.expanded = !item.expanded;
      this.cdr.markForCheck();
      return;
    }
  }

  handleLogout(item: MenuItem) {
    if (item.isLogout) {
      this.isLogoutPopupOpen = true;
    }
  }

  closeLogoutPopup() {
    this.isLogoutPopupOpen = false;
  }

  confirmLogout() {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  isUserManager(user: SessionUser | null): boolean {
    if (!user) return false;
    const role = (user.role || '').toLowerCase();
    if (role === 'manager' || role === 'admin') return true;
    if (user.isManager) return true;
    if (user.accessibleDashboards && user.accessibleDashboards.includes('MANAGER')) return true;
    return false;
  }

  isUserHr(user: SessionUser | null): boolean {
    if (!user) return false;
    const role = (user.role || '').toLowerCase();
    if (role === 'hr' || role === 'admin') return true;
    if (user.accessibleDashboards && user.accessibleDashboards.includes('HR')) return true;
    return false;
  }

  buildMenu(user: SessionUser | null): void {
    const isManager = this.isUserManager(user);
    const isHr = this.isUserHr(user);

    const items: MenuItem[] = [];

    // Optional admin link
    if (user?.role === 'admin') {
      items.push({ label: 'Admin Dashboard', icon: 'fas fa-shield-alt', route: '/master-dashboard' });
    }

    // 1. Dashboard (Primary first item: Employee self-service dashboard)
    items.push({ label: 'Dashboard', icon: 'fas fa-tachometer-alt', route: '/emp-dashboard' });

    // 2. HR Dashboard with sub-parts (ONLY for employees assigned as HR)
    if (isHr) {
      items.push({
        label: 'HR Dashboard',
        icon: 'fas fa-user-shield',
        expanded: false,
        children: [
          { label: 'Overview', icon: 'fas fa-chart-pie', route: '/emp-dashboard/hr-overview' },
          { label: 'Employees', icon: 'fas fa-users', route: '/emp-dashboard/hr-employees' },
          { label: 'Managers', icon: 'fas fa-user-tie', route: '/emp-dashboard/hr-managers' },
          { label: 'Documents', icon: 'fas fa-folder-open', route: '/emp-dashboard/hr-documents' },
          { label: 'Attendance', icon: 'fas fa-clock', route: '/emp-dashboard/hr-attendance' },
          { label: 'Time Off', icon: 'fas fa-calendar-times', route: '/emp-dashboard/hr-time-off' },
          { label: 'Regularizations', icon: 'fas fa-business-time', route: '/emp-dashboard/hr-regularization' },
          {
            label: 'Trainings',
            icon: 'fas fa-graduation-cap',
            expanded: false,
            children: [
              { label: 'All Trainings', icon: 'fas fa-book-reader', route: '/emp-dashboard/hr-trainings' },
              { label: 'Training Reports', icon: 'fas fa-chart-bar', route: '/emp-dashboard/training-reports' }
            ]
          },
          { label: 'Reports', icon: 'fas fa-file-contract', route: '/emp-dashboard/hr-reports' },
          {
            label: 'Payroll',
            icon: 'fas fa-money-check-alt',
            expanded: false,
            children: [
              { label: 'Dashboard', icon: 'fas fa-chart-pie', route: '/emp-dashboard/hr-payroll/dashboard' },
              { label: 'Employee Salaries', icon: 'fas fa-users-cog', route: '/emp-dashboard/hr-payroll/salaries' },
              { label: 'Salary Structures', icon: 'fas fa-layer-group', route: '/emp-dashboard/hr-payroll/structures' },
              { label: 'Payroll Runs', icon: 'fas fa-cogs', route: '/emp-dashboard/hr-payroll/runs' },
              { label: 'Salary Revisions', icon: 'fas fa-chart-line', route: '/emp-dashboard/hr-payroll/revisions' },
              { label: 'Payslips', icon: 'fas fa-file-invoice-dollar', route: '/emp-dashboard/hr-payroll/payslips' },
              { label: 'Statutory Rules', icon: 'fas fa-balance-scale', route: '/emp-dashboard/hr-payroll/statutory' }
            ]
          }
        ]
      });
    }

    // 3. Manager Dashboard with sub-parts (ONLY for employees assigned as manager)
    if (isManager) {
      items.push({
        label: 'Manager Dashboard',
        icon: 'fas fa-chart-line',
        expanded: false,
        children: [
          { label: 'Overview', icon: 'fas fa-chart-pie', route: '/emp-dashboard/manager-dashboard' },
          { label: 'My Team', icon: 'fas fa-users', route: '/emp-dashboard/team' },
          { label: 'Team Attendance', icon: 'fas fa-clock', route: '/emp-dashboard/team-attendance' },
          { label: 'Leave Approvals', icon: 'fas fa-calendar-check', route: '/emp-dashboard/leave-approvals' }
        ]
      });
    }

    // 3. Employee self-service items
    items.push(
      { label: 'My Attendance', icon: 'fas fa-calendar-check', route: '/emp-dashboard/my-attendance' },
      { label: 'My Documents', icon: 'fas fa-folder-open', route: '/emp-dashboard/my-documents' },
      { label: 'Time Off', icon: 'fas fa-clock', route: '/emp-dashboard/time-off' },
      { label: 'Regularization', icon: 'fas fa-business-time', route: '/emp-dashboard/regularization' },
      { label: 'My Payroll', icon: 'fas fa-file-invoice-dollar', route: '/emp-dashboard/my-payroll' },
      { label: 'My Trainings', icon: 'fas fa-graduation-cap', route: '/emp-dashboard/my-trainings' },
      { label: 'My Profile', icon: 'far fa-user', route: '/emp-dashboard/my-profile' },
      { label: 'Change Password', icon: 'fas fa-key', route: '/emp-dashboard/change-password' },
      { label: 'Logout', icon: 'fas fa-sign-out-alt', isLogout: true }
    );

    this.menuConfig = [
      {
        groupName: 'Dashboard',
        items: items
      }
    ];

    this.checkActiveRoutes();
    this.cdr.markForCheck();
  }

  ngOnInit(): void {
    const user = this.authService.getCurrentUser();
    this.buildMenu(user);

    // Keep menu synchronized with active session user changes
    this.authService.currentUser$.subscribe(u => {
      this.buildMenu(u);
    });

    this.checkMobileCollapse();
    this.isEmpSidebarOpen$.subscribe(open => {
      this.collapsed = !open;
      this.cdr.markForCheck();
    });

    // Auto-expand menu based on current route
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe(() => {
      this.checkActiveRoutes();
      this.checkMobileCollapse();
    });
    
    // Initial active route check
    setTimeout(() => this.checkActiveRoutes(), 100);
  }

  toggleExpand(item: MenuItem): void {
    if (item.children) {
      item.expanded = !item.expanded;
      this.cdr.markForCheck();
    }
  }

  handleParentClick(item: MenuItem, event?: Event): void {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    if (item.children) {
      item.expanded = !item.expanded;
      this.cdr.markForCheck();
    }
  }

  toggleChildExpand(child: MenuItem, event?: Event): void {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    if (child.children) {
      child.expanded = !child.expanded;
      this.cdr.markForCheck();
    }
  }

  checkActiveRoutes(): void {
    const currentUrl = this.router.url;
    this.menuConfig.forEach(group => {
      group.items.forEach(item => {
        if (item.children) {
          let hasActiveDirectChild = false;
          item.children.forEach(child => {
            if (child.children) {
              const isSubChildActive = child.children.some(sub =>
                sub.route && (currentUrl === sub.route || currentUrl.startsWith(sub.route + '/'))
              );
              if (isSubChildActive) {
                child.expanded = true;
                hasActiveDirectChild = true;
              }
            } else if (child.route && (currentUrl === child.route || currentUrl.startsWith(child.route + '/'))) {
              hasActiveDirectChild = true;
            }
          });
          if (hasActiveDirectChild) {
            item.expanded = true;
          }
        }
      });
    });
    this.cdr.markForCheck();
  }

  isParentActive(item: MenuItem): boolean {
    if (!item.children) return false;
    const currentUrl = this.router.url;
    return item.children.some(child => {
      if (child.children) {
        return child.children.some(sub => sub.route ? (currentUrl === sub.route || currentUrl.startsWith(sub.route + '/')) : false);
      }
      return child.route ? (currentUrl === child.route || currentUrl.startsWith(child.route + '/')) : false;
    });
  }
}
