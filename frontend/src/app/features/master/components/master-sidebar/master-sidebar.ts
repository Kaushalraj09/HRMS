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
        { label: 'My Profile', icon: 'far fa-user', route: '/master-dashboard/my-profile' },
        { label: 'Login Activity', icon: 'fas fa-history', route: '/master-dashboard/login-activity' }
      ]
    },
    {
      groupName: 'Access Management',
      items: [
        { label: 'HR Users', icon: 'fas fa-user-shield', route: '/master-dashboard/hr-users' },
      ]
    },
    {
      groupName: 'People',
      items: [
        { label: 'Employees', icon: 'far fa-user', route: '/master-dashboard/employees' },
        { label: 'Attendance', icon: 'far fa-clock', route: '/master-dashboard/attendance' }
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
    
    // Initial check
    setTimeout(() => this.checkActiveRoutes(), 100);
  }

  toggleExpand(item: MenuItem): void {
    if (item.children) {
      item.expanded = !item.expanded;
    }
  }

  checkActiveRoutes(): void {
    const currentUrl = this.router.url;
    this.menuConfig.forEach(group => {
      group.items.forEach(item => {
        if (item.children) {
          const isActive = item.children.some(child => child.route && currentUrl.includes(child.route));
          if (isActive) {
             item.expanded = true;
          }
        }
      });
    });
  }

  isParentActive(item: MenuItem): boolean {
    if (!item.children) return false;
    const currentUrl = this.router.url;
    return item.children.some(child => child.route && currentUrl.includes(child.route));
  }
}
