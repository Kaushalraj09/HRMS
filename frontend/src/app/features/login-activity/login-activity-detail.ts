import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { take } from 'rxjs';
import { LoginActivityService, LoginActivity } from '../../core/services/login-activity.service';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login-activity-detail',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './login-activity-detail.html',
  styleUrl: './login-activity-detail.css'
})
export class LoginActivityDetail implements OnInit {
  activityId!: number;
  activity: LoginActivity | null = null;
  isAdminOrHR = false;
  isLoading = true;

  constructor(
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly loginActivityService: LoginActivityService,
    private readonly authService: AuthService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const idStr = params.get('id');
      if (idStr) {
        this.activityId = +idStr;
        this.checkRoleAndLoad();
        this.cdr.detectChanges();
      } else {
        this.goBack();
      }
    });
  }

  checkRoleAndLoad(): void {
    this.authService.currentUser$.pipe(take(1)).subscribe(user => {
      if (user) {
        const role = user.role.toLowerCase();
        this.isAdminOrHR = (role === 'admin' || role === 'hr');
        this.loadDetail();
        this.cdr.detectChanges();
      }
    });
  }

  loadDetail(): void {
    this.isLoading = true;
    this.cdr.detectChanges();
    this.loginActivityService.getDetail(this.activityId).subscribe({
      next: (data) => {
        this.activity = data;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error loading login activity detail:', err);
        this.isLoading = false;
        this.cdr.detectChanges();
        this.goBack();
      }
    });
  }

  goBack(): void {
    this.router.navigate(['../'], { relativeTo: this.route });
  }
}
