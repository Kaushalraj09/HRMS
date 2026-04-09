<<<<<<< HEAD
import { Component, HostListener, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { Dropdown } from '../dropdown/dropdown';

@Component({
  selector: 'app-navbar',
  imports: [CommonModule, MatFormFieldModule, MatSelectModule, Dropdown],
=======
import { Component } from '@angular/core';
import {  EventEmitter, Input, Output } from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

@Component({
  selector: 'app-navbar',
  imports: [MatFormFieldModule, MatSelectModule],
>>>>>>> company/main
  templateUrl: './navbar.html',
  styleUrl: './navbar.css',
})
export class Navbar {
  @Input() userName: string = 'User';
  @Input() notificationCount: number = 0;
  @Input() showSearch: boolean = true;

  @Output() hamburgerClick = new EventEmitter<void>();
  @Output() searchChange = new EventEmitter<string>();
  @Output() profileClick = new EventEmitter<void>();
  @Output() notificationClick = new EventEmitter<void>();

  selectedLang = 'en';
  isOpen = false;
<<<<<<< HEAD
  isProfileDropdownOpen = false;

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    const target = event.target as HTMLElement;
    // Close dropdown if click is outside of profile completely
    if (!target.closest('.profile') && !target.closest('app-dropdown')) {
      this.isProfileDropdownOpen = false;
    }
  }
=======
>>>>>>> company/main

  onHamburgerClick() {
    this.hamburgerClick.emit();
    this.isOpen = !this.isOpen;
  }

  onSearch(value: string) {
    this.searchChange.emit(value);
  }

  onProfileClick() {
<<<<<<< HEAD
    this.isProfileDropdownOpen = !this.isProfileDropdownOpen;
=======
>>>>>>> company/main
    this.profileClick.emit();
  }

  onNotificationClick() {
    this.notificationClick.emit();
  }

}
