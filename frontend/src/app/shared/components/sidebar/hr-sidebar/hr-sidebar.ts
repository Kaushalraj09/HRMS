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
     @Input() menuConfig: MenuGroup[] = [
      { 
        groupName: 'Hr Dashboard',
        items: [ 
              { label: 'Hr Dashboard',icon: 'fas fa-tachometer-alt', route: '/emp-dashboard' },
              { label: 'My Attendance', icon: 'fas fa-calendar-check', route: '/attendance' },
              { label: 'My Profile', icon: 'far fa-user', route: '/profile' },
              { label: 'Change Password', icon: 'fas fa-key', route: '/change-password' },
              { label: 'Logout', icon: 'fas fa-sign-out-alt', route: '/login' }
        ]
      }
    ];
     isHrSidebarOpen$! : import('rxjs').Observable<boolean>;
    
      constructor( private router: Router, private hrSidebarService: HrSidebarService) {
        this.isHrSidebarOpen$ = this.hrSidebarService.isHrSidebarOpen$;
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
