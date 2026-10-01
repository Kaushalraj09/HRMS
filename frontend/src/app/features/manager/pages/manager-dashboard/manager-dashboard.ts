import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { Observable } from 'rxjs';
import { Navbar } from '../../../../shared/components/navbar/navbar';
import { ManagerSidebar } from '../../components/manager-sidebar/manager-sidebar';
import { ManagerSidebarService } from '../../components/manager-sidebar/manager-sidebar.service';
import { AuthService } from '../../../../core/services/auth.service';

@Component({
  selector: 'app-manager-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, Navbar, ManagerSidebar],
  templateUrl: './manager-dashboard.html',
  styleUrls: ['./manager-dashboard.css']
})
export class ManagerDashboard implements OnInit {
  isSidebarOpen$: Observable<boolean>;
  userName = 'Manager';
  userRole = 'Manager';
  userAvatarUrl?: string;

  constructor(
    private readonly router: Router,
    private readonly managerSidebarService: ManagerSidebarService,
    private readonly authService: AuthService,
    private readonly cdr: ChangeDetectorRef
  ) {
    this.isSidebarOpen$ = this.managerSidebarService.isSidebarOpen$;
  }

  ngOnInit(): void {
    const user = this.authService.getCurrentUser();
    if (user) {
      this.userName = user.displayName || user.email || 'Manager';
      this.userRole = user.designation || (user.role ? (user.role.charAt(0).toUpperCase() + user.role.slice(1)) : 'Manager');
      this.userAvatarUrl = user.profileImage || undefined;
    }
    this.authService.currentUser$.subscribe((u) => {
      if (u) {
        this.userName = u.displayName || u.email || 'Manager';
        this.userRole = u.designation || (u.role ? (u.role.charAt(0).toUpperCase() + u.role.slice(1)) : 'Manager');
        this.userAvatarUrl = u.profileImage || undefined;
        this.cdr.markForCheck();
      }
    });
  }

  toggleSidebar(): void {
    this.managerSidebarService.toggleSidebar();
  }

  onProfileClick(): void {
    this.router.navigate(['/manager-dashboard/my-profile']);
  }
}
