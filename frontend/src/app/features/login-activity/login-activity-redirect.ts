import { Component, OnInit } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
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
    this.authService.currentUser$.subscribe(user => {
      if (user) {
        const role = user.role.toLowerCase();
        const id = this.route.snapshot.paramMap.get('id');
        let basePath = '';
        
        if (role === 'admin') {
          basePath = '/master-dashboard';
        } else if (role === 'hr') {
          basePath = user.activeDashboard === 'EMPLOYEE' ? '/emp-dashboard' : '/hr-dashboard';
        } else {
          basePath = '/emp-dashboard';
        }
        
        if (id) {
          this.router.navigate([basePath, 'login-activity', id]);
        } else {
          this.router.navigate([basePath, 'login-activity']);
        }
      } else {
        this.router.navigate(['/login']);
      }
    });
  }
}
