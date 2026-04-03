import { Component } from '@angular/core';
import {  EventEmitter, Input, Output } from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

@Component({
  selector: 'app-navbar',
  imports: [MatFormFieldModule, MatSelectModule],
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

  onHamburgerClick() {
    this.hamburgerClick.emit();
  }

  onSearch(value: string) {
    this.searchChange.emit(value);
  }

  onProfileClick() {
    this.profileClick.emit();
  }

  onNotificationClick() {
    this.notificationClick.emit();
  }

}
