import { Component } from '@angular/core';
import { RouterModule, Router } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-dropdown',
  standalone: true,
  imports: [RouterModule, CommonModule],
  templateUrl: './dropdown.html',
  styleUrl: './dropdown.css',
})
export class Dropdown {
  isLogoutPopupOpen = false;

  constructor(private router: Router) {}

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
    // clear auth data
    localStorage.clear();
    sessionStorage.clear();

    // redirect to login
    this.router.navigate(['/login']);
  }
}
