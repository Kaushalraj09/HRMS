import { Component, Input, OnInit, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { EmpSidebarService } from './emp-sidebar.service';
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
        groupName: 'Employee Dashboard',
        items: [ 
              { label: 'Employee Dashboard',icon: 'fas fa-tachometer-alt', route: '/emp-dashboard' },
              { label: 'My Attendance', icon: 'fas fa-calendar-check', route: '/emp-dashboard/my-attendance' },
              { label: 'Regularization', icon: 'fas fa-business-time', route: '/emp-dashboard/regularization' },
              { label: 'My Profile', icon: 'far fa-user', route: '/emp-dashboard/my-profile' },
              { label: 'Change Password', icon: 'fas fa-key', route: '/emp-dashboard/change-password' },
              { label: 'Logout', icon: 'fas fa-sign-out-alt', isLogout: true }
        ]
      }
    ];
     isEmpSidebarOpen$! : import('rxjs').Observable<boolean>;
    
      constructor(private empSidebarService: EmpSidebarService, private router: Router, private readonly authService: AuthService) {
        this.isEmpSidebarOpen$ = this.empSidebarService.isEmpSidebarOpen$;
      }

      @HostListener('window:resize', ['$event'])
      onResize(event: any) {
        this.checkMobileCollapse();
      }

      private checkMobileCollapse() {
        if (typeof window !== 'undefined' && window.innerWidth < 768) {
          this.empSidebarService.setSidebarState(false);
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
              groupName: 'Employee View (View Only)',
              items: [
                { label: 'Admin Dashboard', icon: 'fas fa-tachometer-alt', route: '/master-dashboard' },
                { label: 'Employee Dashboard', icon: 'fas fa-tachometer-alt', route: '/emp-dashboard' }
              ]
            }
          ];
        }

        this.checkMobileCollapse();
        this.isEmpSidebarOpen$.subscribe(open => {
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
