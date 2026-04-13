import { Component, ChangeDetectionStrategy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Observable } from 'rxjs';
import { EmployeeProfile } from '../../../../core/models/profile.model';
import { MyProfileService } from '../../../../core/services/profile.service';

@Component({
  selector: 'app-my-profile',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './my-profile.html',
  styleUrl: './my-profile.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MyProfile implements OnInit {
  profile$!: Observable<EmployeeProfile>;

  constructor(private profileService: MyProfileService) {}

  ngOnInit(): void {
    this.profile$ = this.profileService.getProfile();
  }
}
