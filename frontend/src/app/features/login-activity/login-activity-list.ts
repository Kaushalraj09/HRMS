import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { LoginActivityService, LoginActivity } from '../../core/services/login-activity.service';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login-activity-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './login-activity-list.html',
  styleUrl: './login-activity-list.css'
})
export class LoginActivityList implements OnInit {
  activities: LoginActivity[] = [];
  filterType = 'Today';
  startDate = '';
  endDate = '';
  isAdminOrHR = false;
  isLoading = false;

  constructor(
    private readonly loginActivityService: LoginActivityService,
    private readonly authService: AuthService,
    private readonly router: Router,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.authService.currentUser$.subscribe(user => {
      if (user) {
        const role = user.role.toLowerCase();
        this.isAdminOrHR = (role === 'admin' || role === 'hr');
        this.loadHistory();
        this.cdr.detectChanges();
      }
    });
  }

  loadHistory(): void {
    this.isLoading = true;
    this.cdr.detectChanges();
    const filter = this.filterType;
    const start = this.filterType === 'Custom' ? this.startDate : undefined;
    const end = this.filterType === 'Custom' ? this.endDate : undefined;

    this.loginActivityService.getHistory(filter, start, end).subscribe({
      next: (data) => {
        this.activities = data;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error fetching login activity:', err);
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  setFilter(type: string): void {
    this.filterType = type;
    if (type !== 'Custom') {
      this.loadHistory();
    }
  }

  onCustomDateChange(): void {
    if (this.startDate && this.endDate) {
      this.loadHistory();
    }
  }

  viewDetails(id: number): void {
    this.router.navigate(['/notifications/login-activity', id]);
  }
}
