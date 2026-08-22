import { Component, Input, OnInit, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { HrSidebarService } from './hr-sidebar.service';
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
  selector: 'app-hr-sidebar',
  imports: [CommonModule, RouterModule],
  templateUrl: './hr-sidebar.html',
  styleUrl: './hr-sidebar.css',
  host: {
    '[class.collapsed]': 'collapsed'
  }
})
export class HrSidebar implements OnInit {
     isLogoutPopupOpen = false;
     collapsed = false;
     @Input() menuConfig: MenuGroup[] = [
      { 
        groupName: 'Hr Dashboard',
        items: [ 
          { label: 'HR Dashboard', icon: 'fas fa-chart-line', route: '/hr-dashboard' },
          { label: 'Employees', icon: 'fas fa-users', route: '/hr-dashboard/employees' },
          { label: 'Documents', icon: 'fas fa-folder-open', route: '/hr-dashboard/documents' },
          { label: 'Attendance', icon: 'fas fa-clock', route: '/hr-dashboard/attendance' },
          { label: 'Time Off', icon: 'fas fa-calendar-times', route: '/hr-dashboard/time-off' },
          { label: 'Regularizations', icon: 'fas fa-business-time', route: '/hr-dashboard/regularization-requests' },
          {
            label: 'Training & Development',
            icon: 'fas fa-graduation-cap',
            children: [
              { label: 'All Trainings', route: '/hr-dashboard/trainings' },
              { label: 'Training Reports', route: '/hr-dashboard/training-reports' }
            ]
          },
          { label: 'Reports', icon: 'fas fa-file-contract', route: '/hr-dashboard/reports' },
          { label: 'My Profile', icon: 'far fa-user', route: '/hr-dashboard/my-profile' },
          { label: 'Login Activity', icon: 'fas fa-history', route: '/hr-dashboard/login-activity' },
          { label: 'Logout', icon: 'fas fa-sign-out-alt', isLogout: true }
        ]
      }
    ];
     isHrSidebarOpen$! : import('rxjs').Observable<boolean>;
    
      constructor( private router: Router, private hrSidebarService: HrSidebarService, private readonly authService: AuthService) {
        this.isHrSidebarOpen$ = this.hrSidebarService.isHrSidebarOpen$;
      }

      @HostListener('window:resize', ['$event'])
      onResize(event: any) {
        this.checkMobileCollapse();
      }

      private checkMobileCollapse() {
        if (typeof window !== 'undefined' && window.innerWidth < 768) {
          this.hrSidebarService.setSidebarState(false);
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
        const user = this.authService.getCurrentUser();
        if (user?.role === 'admin') {
          this.menuConfig = [
            {
              groupName: 'HR View (View Only)',
              items: [
                { label: 'Admin Dashboard', icon: 'fas fa-tachometer-alt', route: '/master-dashboard' },
                { label: 'HR Dashboard', icon: 'fas fa-chart-line', route: '/hr-dashboard' }
              ]
            }
          ];
        }

        this.checkMobileCollapse();
        this.isHrSidebarOpen$.subscribe(open => {
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
