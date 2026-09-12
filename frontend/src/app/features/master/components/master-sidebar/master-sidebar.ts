import { Component, Input, OnInit, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { MasterSidebarService } from './master-sidebar.service';
import { filter } from 'rxjs/operators';
import { AuthService } from '../../../../core/services/auth.service';

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
  selector: 'app-master-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './master-sidebar.html',
  styleUrls: ['./master-sidebar.css'],
  host: {
    '[class.collapsed]': 'collapsed'
  }
})
export class MasterSidebar implements OnInit {
  isLogoutPopupOpen = false;
  collapsed = false;
  @Input() menuConfig: MenuGroup[] = [
    {
      groupName: 'Main',
      items: [
        { label: 'Admin Dashboard', icon: 'fas fa-tachometer-alt', route: '/master-dashboard' },
        { label: 'Reports', icon: 'fas fa-file-contract', route: '/master-dashboard/reports' },
        { label: 'My Profile', icon: 'far fa-user', route: '/master-dashboard/my-profile' },
        { label: 'Login Activity', icon: 'fas fa-history', route: '/master-dashboard/login-activity' }
      ]
    },
    {
      groupName: 'Access Management',
      items: [
        { label: 'Employees', icon: 'far fa-user', route: '/master-dashboard/employees' },
        { label: 'HR Users', icon: 'fas fa-user-shield', route: '/master-dashboard/hr-users' },
        { label: 'Master Data Config', icon: 'fas fa-cogs', route: '/master-dashboard/master-data' }
      ]
    },
    {
      groupName: 'People',
      items: [
        { label: 'Documents', icon: 'fas fa-folder-open', route: '/master-dashboard/documents' },
        { label: 'Attendance', icon: 'far fa-clock', route: '/master-dashboard/attendance' },
        { label: 'Time Off Oversight', icon: 'fas fa-calendar-times', route: '/master-dashboard/time-off' },
        { label: 'Regularization Oversight', icon: 'fas fa-business-time', route: '/master-dashboard/regularization-requests' },
        {
          label: 'Training & Development',
          icon: 'fas fa-graduation-cap',
          children: [
            { label: 'All Trainings', route: '/master-dashboard/trainings' },
            { label: 'Training Reports', route: '/master-dashboard/training-reports' }
          ]
        }
      ]
    },
    {
      groupName: 'Payroll Management',
      items: [
        {
          label: 'Payroll',
          icon: 'fas fa-money-check-alt',
          route: '/master-dashboard/payroll/dashboard',
          children: [
            { label: 'Dashboard', icon: 'fas fa-chart-pie', route: '/master-dashboard/payroll/dashboard' },
            { label: 'Employee Salaries', icon: 'fas fa-users-cog', route: '/master-dashboard/payroll/salaries' },
            { label: 'Salary Structures', icon: 'fas fa-layer-group', route: '/master-dashboard/payroll/structures' },
            { label: 'Payroll Runs', icon: 'fas fa-cogs', route: '/master-dashboard/payroll/runs' },
            { label: 'Salary Revisions', icon: 'fas fa-chart-line', route: '/master-dashboard/payroll/revisions' },
            { label: 'Payslips', icon: 'fas fa-file-invoice-dollar', route: '/master-dashboard/payroll/payslips' },
            { label: 'Statutory Rules', icon: 'fas fa-balance-scale', route: '/master-dashboard/payroll/statutory' }
          ]
        }
      ]
    },
    {
      groupName: 'Cross Role Views',
      items: [
        { label: 'HR Dashboard', icon: 'fas fa-chart-line', route: '/hr-dashboard' },
        { label: 'Employee Dashboard', icon: 'fas fa-user-circle', route: '/emp-dashboard' }
      ]
    },
    {
      groupName: 'Pages',
      items: [
        { label: 'Logout', icon: 'fas fa-sign-out-alt', isLogout: true }
      ]
    }
  ];

  isSidebarOpen$! : import('rxjs').Observable<boolean>;

  constructor(private sidebarService: MasterSidebarService, private router: Router, private readonly authService: AuthService) {
    this.isSidebarOpen$ = this.sidebarService.isSidebarOpen$;
  }

  @HostListener('window:resize', ['$event'])
  onResize(event: any) {
    this.checkMobileCollapse();
  }

  private checkMobileCollapse() {
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      this.sidebarService.setSidebarState(false);
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


  ngOnInit(): void {
    this.checkMobileCollapse();
    this.checkActiveRoutes();
    this.isSidebarOpen$.subscribe(open => {
      this.collapsed = !open;
    });
    // Optionally auto-expand menu based on current route
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe(() => {
      this.checkActiveRoutes();
      this.checkMobileCollapse();
    });
  }

  toggleExpand(item: MenuItem): void {
    if (item.children) {
      item.expanded = !item.expanded;
      if (item.route) {
        this.router.navigate([item.route]);
      } else if (item.children.length > 0 && item.children[0].route) {
        this.router.navigate([item.children[0].route]);
      }
    }
  }

  checkActiveRoutes(): void {
    const currentUrl = this.router.url.split('?')[0];
    this.menuConfig.forEach(group => {
      group.items.forEach(item => {
        if (item.children) {
          const isActive = (item.route && (currentUrl === item.route || currentUrl.startsWith(item.route + '/') || (item.route.endsWith('/dashboard') && currentUrl === item.route.replace('/dashboard', '')))) ||
            item.children.some(child => child.route && (currentUrl === child.route || currentUrl.startsWith(child.route + '/')));
          if (isActive) {
            item.expanded = true;
          }
        }
      });
    });
  }

  isParentActive(item: MenuItem): boolean {
    if (!item.children) return false;
    const currentUrl = this.router.url.split('?')[0];
    return Boolean((item.route && (currentUrl === item.route || currentUrl.startsWith(item.route + '/') || (item.route.endsWith('/dashboard') && currentUrl === item.route.replace('/dashboard', '')))) ||
      item.children.some(child => child.route && (currentUrl === child.route || currentUrl.startsWith(child.route + '/'))));
  }
}
