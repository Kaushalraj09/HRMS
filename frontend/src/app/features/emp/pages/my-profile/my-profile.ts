import { Component, ChangeDetectionStrategy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BehaviorSubject, take } from 'rxjs';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { EmployeeProfile } from '../../../../core/models/profile.model';
import { MyProfileService } from '../../../../core/services/profile.service';

@Component({
  selector: 'app-my-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './my-profile.html',
  styleUrl: './my-profile.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MyProfile implements OnInit {
  profile$ = new BehaviorSubject<EmployeeProfile | null>(null);
  isEditing$ = new BehaviorSubject<boolean>(false);
  saveMessage$ = new BehaviorSubject<string>('');
  profileForm!: FormGroup;

  constructor(
    private profileService: MyProfileService,
    private fb: FormBuilder
  ) {
    this.initForm();
  }

  ngOnInit(): void {
    this.loadProfile();
  }

  private initForm(): void {
    this.profileForm = this.fb.group({
      firstName: ['', Validators.required],
      lastName: ['', Validators.required],
      gender: [''],
      dateOfBirth: [''],
      maritalStatus: [''],
      bloodGroup: [''],
      personalEmail: ['', Validators.email],
      mobileNumber: ['', Validators.required],
      alternateMobile: [''],
      location: ['']
    });
  }

  private loadProfile(): void {
    this.profileService.getProfile().pipe(take(1)).subscribe(profile => {
      this.profile$.next(profile);
      this.patchForm(profile);
    });
  }

  private patchForm(profile: EmployeeProfile): void {
    this.profileForm.patchValue({
      firstName: profile.personalDetails.firstName,
      lastName: profile.personalDetails.lastName,
      gender: profile.personalDetails.gender,
      dateOfBirth: profile.personalDetails.dateOfBirth,
      maritalStatus: profile.personalDetails.maritalStatus,
      bloodGroup: profile.personalDetails.bloodGroup,
      personalEmail: profile.contactDetails.personalEmail,
      mobileNumber: profile.contactDetails.mobileNumber,
      alternateMobile: profile.contactDetails.alternateMobile,
      location: profile.contactDetails.location
    });
  }

  toggleEdit(): void {
    this.isEditing$.next(true);
  }

  cancelEdit(): void {
    this.isEditing$.next(false);
    if (this.profile$.value) {
      this.patchForm(this.profile$.value);
    }
  }

  saveChanges(): void {
    const current = this.profile$.value;
    if (!current || this.profileForm.invalid) {
      this.profileForm.markAllAsTouched();
      return;
    }

    const raw = this.profileForm.getRawValue();
    const updatedProfile: EmployeeProfile = {
      ...current,
      firstName: raw.firstName,
      lastName: raw.lastName,
      personalDetails: {
        ...current.personalDetails,
        firstName: raw.firstName,
        lastName: raw.lastName,
        gender: raw.gender,
        dateOfBirth: raw.dateOfBirth,
        maritalStatus: raw.maritalStatus,
        bloodGroup: raw.bloodGroup
      },
      contactDetails: {
        ...current.contactDetails,
        personalEmail: raw.personalEmail,
        mobileNumber: raw.mobileNumber,
        alternateMobile: raw.alternateMobile,
        location: raw.location
      }
    };

    this.profileService.updateProfile(updatedProfile).subscribe(res => {
      if (res.success) {
        this.saveMessage$.next(res.message);
        this.profile$.next(updatedProfile);
        this.isEditing$.next(false);
        setTimeout(() => this.saveMessage$.next(''), 3000);
      }
    });
  }
}
