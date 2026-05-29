import { Component, HostListener, EventEmitter, Input, Output, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { Dropdown } from '../dropdown/dropdown';
import { AuthService } from '../../../core/services/auth.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, MatFormFieldModule, MatSelectModule, Dropdown],
  templateUrl: './navbar.html',
  styleUrl: './navbar.css',
})
export class Navbar implements OnInit, OnDestroy {
  @Input() userName: string = 'User';
  @Input() notificationCount: number = 0;
  @Input() showSearch: boolean = true;

  @Output() hamburgerClick = new EventEmitter<void>();
  @Output() searchChange = new EventEmitter<string>();
  @Output() profileClick = new EventEmitter<void>();
  @Output() notificationClick = new EventEmitter<void>();

  selectedLang = 'en';
  isOpen = false;
  isProfileDropdownOpen = false;
  profileImage: string | null = null;
  userInitials: string = 'U';

  private sub = new Subscription();

  constructor(private readonly authService: AuthService) {}

  ngOnInit(): void {
    this.sub.add(
      this.authService.currentUser$.subscribe(user => {
        if (user) {
          this.userName = user.displayName;
          this.profileImage = user.profileImage || null;
          
          const names = user.displayName.split(' ');
          const first = names[0]?.[0] || '';
          const last = names[1]?.[0] || '';
          this.userInitials = (first + last).toUpperCase() || 'U';
        }
      })
    );
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (!target.closest('.profile') && !target.closest('app-dropdown')) {
      this.isProfileDropdownOpen = false;
    }
  }

  onHamburgerClick() {
    this.hamburgerClick.emit();
    this.isOpen = !this.isOpen;
  }

  onSearch(value: string) {
    this.searchChange.emit(value);
  }

  onProfileClick() {
    this.isProfileDropdownOpen = !this.isProfileDropdownOpen;
    this.profileClick.emit();
  }

  onNotificationClick() {
    this.notificationClick.emit();
  }
}
