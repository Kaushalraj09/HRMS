import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { SidebarService } from './sidebar.service';
import { filter } from 'rxjs/operators';

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
        { 
          label: 'Dashboard', 
          icon: 'fas fa-tachometer-alt',
          expanded: true,
          children: [
            { label: 'Admin Dashboard', route: '/master-dashboard' },
            { label: 'Hr Dashboard', route: '/hr-dashboard' },
            { label: 'Employee Dashboard', route: '/emp-dashboard' }
          ]
        }
      ]
    },
    {
      groupName: 'Authentication',
      items: [
        { label: 'User Controller', icon: 'fas fa-user-secret', route: '/users' },
        { label: 'Work Mode Requests', icon: 'far fa-check-circle', route: '/work-modes' }
      ]
    },
    {
      groupName: 'Employees',
      items: [
        { label: 'Employees', icon: 'far fa-user', route: '/employees' }
      ]
    },
  
    {
      groupName: 'HR',
      items: [
        { label: 'Sales', icon: 'far fa-copy', route: '/sales' },
        { label: 'Payroll', icon: 'fas fa-money-bill-wave', route: '/payroll' },
        { label: 'Reports', icon: 'fas fa-chart-pie', route: '/reports' }
      ]
    },
    {
      groupName: 'Performance',
      items: [
        { label: 'Performance', icon: 'fas fa-graduation-cap', route: '/performance' },
        { label: 'Training', icon: 'fas fa-edit', route: '/training' }
      ]
    },
    {
      groupName: 'Administration',
      items: [
        { label: 'Assets', icon: 'fas fa-cubes', route: '/assets' },
        { label: 'Jobs', icon: 'fas fa-briefcase', route: '/jobs' }
      ]
    },

    {
      groupName: 'Pages',
      items: [
        { label: 'Profile', icon: 'far fa-user', route: '/profile' },
        { label: 'Logout', icon: 'fas fa-sign-out-alt', isLogout: true }
      ]
    }
  ];

  isSidebarOpen$! : import('rxjs').Observable<boolean>;

  constructor(private sidebarService: SidebarService, private router: Router) {
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
    localStorage.clear();
    sessionStorage.clear();
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
