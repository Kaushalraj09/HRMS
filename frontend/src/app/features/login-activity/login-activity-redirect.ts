import { Component, OnInit } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { take } from 'rxjs';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login-activity-redirect',
  standalone: true,
  template: ''
})
export class LoginActivityRedirect implements OnInit {
  constructor(
    private readonly router: Router,
    private readonly route: ActivatedRoute,
    private readonly authService: AuthService
  ) {}

  ngOnInit(): void {
    this.authService.currentUser$.pipe(take(1)).subscribe(user => {
      if (user) {
        const role = user.role.toLowerCase();
        const id = this.route.snapshot.paramMap.get('id');
        
        if (role === 'admin') {
          const basePath = '/master-dashboard';
          if (id) {
            this.router.navigate([basePath, 'login-activity', id]);
          } else {
            this.router.navigate([basePath, 'login-activity']);
          }
        } else if (role === 'hr') {
          const basePath = '/hr-dashboard';
          if (id) {
            this.router.navigate([basePath, 'login-activity', id]);
          } else {
            this.router.navigate([basePath, 'login-activity']);
          }
        } else {
          this.router.navigate(['/emp-dashboard']);
        }
      } else {
        this.router.navigate(['/login']);
      }
    });
  }
}
