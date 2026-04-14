import { Component } from '@angular/core';
import { RouterModule, Router } from '@angular/router';
import { CommonModule } from '@angular/common';

import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-dropdown',
  standalone: true,
  imports: [RouterModule, CommonModule],
  templateUrl: './dropdown.html',
  styleUrl: './dropdown.css',
})
export class Dropdown {
  isLogoutPopupOpen = false;

  constructor(private router: Router, private readonly authService: AuthService) {}

  get profileRoute(): string {
    const user = this.authService.getCurrentUser();

    if (user?.role === 'employee') {
      return '/emp-dashboard/my-profile';
    }
    if (user?.role === 'hr') {
      return '/hr-dashboard/employees';
    }
    return '/master-dashboard';
  }

  openLogoutConfirm(event: MouseEvent) {
    event.stopPropagation();
    this.isLogoutPopupOpen = true;
  }

  closeLogoutPopup(event: MouseEvent) {
    event.stopPropagation();
    this.isLogoutPopupOpen = false;
  }

  confirmLogout(event: MouseEvent) {
    event.stopPropagation();
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
