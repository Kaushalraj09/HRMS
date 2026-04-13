import { Component, Input, OnInit} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { HrSidebarService } from './hr-sidebar.service';


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
})
export class HrSidebar {
     isLogoutPopupOpen = false;
     @Input() menuConfig: MenuGroup[] = [
      { 
        groupName: 'Hr Dashboard',
        items: [ 
              { label: 'HR Dashboard', icon: 'fas fa-chart-line', route: '/hr-dashboard' },
              { label: 'Employees', icon: 'fas fa-users', route: '/hr-dashboard/employees' },
              { label: 'Attendance', icon: 'fas fa-clock', route: '/hr-dashboard/attendance' },
              { label: 'Logout', icon: 'fas fa-sign-out-alt', isLogout: true }
        ]
      }
    ];
     isHrSidebarOpen$! : import('rxjs').Observable<boolean>;
    
      constructor( private router: Router, private hrSidebarService: HrSidebarService) {
        this.isHrSidebarOpen$ = this.hrSidebarService.isHrSidebarOpen$;
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
