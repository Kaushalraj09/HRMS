import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { SidebarService } from './sidebar.service';
import { filter } from 'rxjs/operators';
import { AuthService } from '../../../core/services/auth.service';

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
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './sidebar.html',
  styleUrls: ['./sidebar.css']
})
export class Sidebar implements OnInit {
  isLogoutPopupOpen = false;
  @Input() menuConfig: MenuGroup[] = [
    {
      groupName: 'Main',
      items: [
        { label: 'Admin Dashboard', icon: 'fas fa-tachometer-alt', route: '/master-dashboard' }
      ]
    },
    {
      groupName: 'Access Management',
      items: [
        { label: 'HR Users', icon: 'fas fa-user-shield', route: '/master-dashboard/hr-users' },
        { label: 'Create HR', icon: 'fas fa-user-plus', route: '/master-dashboard/hr-users/add' }
      ]
    },
    {
      groupName: 'People',
      items: [
        { label: 'Employees', icon: 'far fa-user', route: '/master-dashboard/employees' }
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

  constructor(private sidebarService: SidebarService, private router: Router, private readonly authService: AuthService) {
    this.isSidebarOpen$ = this.sidebarService.isSidebarOpen$;
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
    // Optionally auto-expand menu based on current route
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe(() => {
      this.checkActiveRoutes();
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
