import { Component, ChangeDetectionStrategy, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BehaviorSubject, take } from 'rxjs';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { EmployeeProfile } from '../../../../core/models/profile.model';
import { MyProfileService } from '../../../../core/services/profile.service';
import { AuthService } from '../../../../core/services/auth.service';
import { AttendanceService } from '../../../../core/services/attendance.service';

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
  isPunchedIn = false;
  readonly bloodOptions = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];

  showAvatarModal = false;
  tempAvatarImage: string | null = null;
  
  readonly predefinedAvatars = [
    'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="50" fill="%233b82f6" /><path d="M32 42 L100 80 L100 100 L50 100 L20 100 Z" fill="%23000000" opacity="0.15" /><rect x="46" y="52" width="8" height="18" fill="%23fdba74" /><path d="M40 70 L50 82 L60 70 L55 100 L45 100 Z" fill="%23ffffff" /><path d="M48 80 L52 80 L54 100 L46 100 Z" fill="%23ef4444" /><path d="M20 100 L20 85 C20 74, 30 68, 40 68 L60 68 C70 68, 80 75, 80 85 L80 100 Z" fill="%231e293b" /><path d="M40 68 L50 82 L43 100 Z" fill="%230f172a" /><path d="M60 68 L50 82 L57 100 Z" fill="%230f172a" /><circle cx="50" cy="42" r="18" fill="%23ffedd5" /><path d="M32 42 C32 25, 68 25, 68 42 C68 33, 60 28, 50 28 C40 28, 32 33, 32 42 Z" fill="%231c1917" /><path d="M37 34 Q41 32 45 35" stroke="%231c1917" stroke-width="1.5" fill="none" /><path d="M63 34 Q59 32 55 35" stroke="%231c1917" stroke-width="1.5" fill="none" /><circle cx="42" cy="38" r="5" stroke="%231c1917" stroke-width="2" fill="none" /><circle cx="58" cy="38" r="5" stroke="%231c1917" stroke-width="2" fill="none" /><path d="M47 38 L53 38" stroke="%231c1917" stroke-width="2" /><path d="M46 50 Q50 53 54 50" stroke="%231c1917" stroke-width="1.5" fill="none" /></svg>',
    'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="50" fill="%23ec4899" /><path d="M32 42 L100 80 L100 100 L50 100 L20 100 Z" fill="%23000000" opacity="0.15" /><path d="M32 40 C22 50, 25 80, 35 85 C35 70, 32 50, 32 40 Z" fill="%23451a03" /><path d="M68 40 C78 50, 75 80, 65 85 C65 70, 68 50, 68 40 Z" fill="%23451a03" /><rect x="46" y="52" width="8" height="18" fill="%23fdba74" /><path d="M20 100 L20 85 C20 74, 30 68, 40 68 L60 68 C70 68, 80 75, 80 85 L80 100 Z" fill="%23374151" /><path d="M40 68 L50 82 L60 68 Z" fill="%23ffffff" /><circle cx="50" cy="42" r="18" fill="%23ffedd5" /><path d="M32 42 C32 25, 68 25, 68 42 C68 33, 60 28, 50 28 C40 28, 32 33, 32 42 Z" fill="%23451a03" /><path d="M37 34 Q41 32 45 35" stroke="%23451a03" stroke-width="1.5" fill="none" /><path d="M63 34 Q59 32 55 35" stroke="%23451a03" stroke-width="1.5" fill="none" /><circle cx="42" cy="38" r="2" fill="%23451a03" /><circle cx="58" cy="38" r="2" fill="%23451a03" /><circle cx="42" cy="38" r="5" stroke="%23ec4899" stroke-width="1.5" fill="none" /><circle cx="58" cy="38" r="5" stroke="%23ec4899" stroke-width="1.5" fill="none" /><path d="M47 38 L53 38" stroke="%23ec4899" stroke-width="1.5" /><path d="M46 50 Q50 53 54 50" stroke="%23b91c1c" stroke-width="1.5" fill="none" /></svg>',
    'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="50" fill="%2310b981" /><path d="M32 42 L100 80 L100 100 L50 100 L20 100 Z" fill="%23000000" opacity="0.15" /><rect x="46" y="52" width="8" height="18" fill="%23fdba74" /><path d="M20 100 L20 85 C20 74, 30 68, 40 68 L60 68 C70 68, 80 75, 80 85 L80 100 Z" fill="%230ea5e9" /><path d="M40 68 L50 80 L42 100 Z" fill="%230284c7" /><path d="M60 68 L50 80 L58 100 Z" fill="%230284c7" /><circle cx="50" cy="42" r="18" fill="%23fed7aa" /><path d="M32 42 C32 25, 68 25, 68 42 C68 35, 60 30, 50 30 C40 30, 32 35, 32 42 Z" fill="%231c1917" /><path d="M32 42 C32 56, 68 56, 68 42 C65 52, 58 56, 50 56 C42 56, 35 52, 32 42 Z" fill="%231c1917" /><path d="M42 47 C45 45, 55 45, 58 47 C58 49, 55 51, 50 51 C45 51, 42 49, 42 47 Z" fill="%231c1917" /><path d="M37 33 Q41 31 45 34" stroke="%231c1917" stroke-width="1.5" fill="none" /><path d="M63 33 Q59 31 55 34" stroke="%231c1917" stroke-width="1.5" fill="none" /><rect x="36" y="34" width="10" height="8" rx="2" stroke="%231c1917" stroke-width="2" fill="none" /><rect x="54" y="34" width="10" height="8" rx="2" stroke="%231c1917" stroke-width="2" fill="none" /><path d="M46 38 L54 38" stroke="%231c1917" stroke-width="2" /></svg>',
    'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="50" fill="%23f59e0b" /><path d="M32 42 L100 80 L100 100 L50 100 L20 100 Z" fill="%23000000" opacity="0.15" /><circle cx="50" cy="21" r="9" fill="%2378350f" /><rect x="46" y="52" width="8" height="18" fill="%23fdba74" /><path d="M20 100 L20 85 C20 74, 30 68, 40 68 L60 68 C70 68, 80 75, 80 85 L80 100 Z" fill="%231e3a8a" /><path d="M42 68 L50 82 L58 68 Z" fill="%23ffffff" /><circle cx="50" cy="42" r="18" fill="%23fff7ed" /><path d="M32 42 C32 25, 68 25, 68 42 C68 34, 60 28, 50 28 C40 28, 32 34, 32 42 Z" fill="%2378350f" /><path d="M37 34 Q41 32 45 35" stroke="%2378350f" stroke-width="1.5" fill="none" /><path d="M63 34 Q59 32 55 35" stroke="%2378350f" stroke-width="1.5" fill="none" /><circle cx="42" cy="38" r="2" fill="%2378350f" /><circle cx="58" cy="38" r="2" fill="%2378350f" /><circle cx="42" cy="38" r="5" stroke="%231e3a8a" stroke-width="1.5" fill="none" /><circle cx="58" cy="38" r="5" stroke="%231e3a8a" stroke-width="1.5" fill="none" /><path d="M47 38 L53 38" stroke="%231e3a8a" stroke-width="1.5" /><path d="M46 50 Q50 53 54 50" stroke="%23e11d48" stroke-width="1.5" fill="none" /></svg>',
    'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="50" fill="%23a855f7" /><path d="M32 42 L100 80 L100 100 L50 100 L20 100 Z" fill="%23000000" opacity="0.15" /><rect x="46" y="52" width="8" height="18" fill="%23fdba74" /><path d="M40 70 L50 82 L60 70 L55 100 L45 100 Z" fill="%23ffffff" /><path d="M48 80 L52 80 L54 100 L46 100 Z" fill="%2310b981" /><path d="M20 100 L20 85 C20 74, 30 68, 40 68 L60 68 C70 68, 80 75, 80 85 L80 100 Z" fill="%234b5563" /><path d="M40 68 L50 82 L43 100 Z" fill="%23374151" /><path d="M60 68 L50 82 L57 100 Z" fill="%23374151" /><circle cx="50" cy="42" r="18" fill="%23ffedd5" /><path d="M32 38 C32 24, 68 24, 68 38 C68 30, 58 26, 48 26 C38 26, 32 30, 32 38 Z" fill="%23451a03" /><path d="M32 38 L34 44 L37 44 L35 38 Z" fill="%23451a03" /><path d="M68 38 L66 44 L63 44 L65 38 Z" fill="%23451a03" /><path d="M37 34 Q41 32 45 35" stroke="%23451a03" stroke-width="1.5" fill="none" /><path d="M63 34 Q59 32 55 35" stroke="%23451a03" stroke-width="1.5" fill="none" /><circle cx="42" cy="39" r="2" fill="%23451a03" /><circle cx="58" cy="39" r="2" fill="%23451a03" /><circle cx="42" cy="39" r="5" stroke="%23374151" stroke-width="1.5" fill="none" /><circle cx="58" cy="39" r="5" stroke="%23374151" stroke-width="1.5" fill="none" /><path d="M47 39 L53 39" stroke="%23374151" stroke-width="1.5" /><path d="M46 50 Q50 53 54 50" stroke="%23451a03" stroke-width="1.5" fill="none" /></svg>',
    'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="50" fill="%2306b6d4" /><path d="M32 42 L100 80 L100 100 L50 100 L20 100 Z" fill="%23000000" opacity="0.15" /><path d="M30 40 L30 55 C30 58, 33 60, 36 60 C36 50, 32 45, 32 40 Z" fill="%231c1917" /><path d="M70 40 L70 55 C70 58, 67 60, 64 60 C64 50, 68 45, 68 40 Z" fill="%231c1917" /><rect x="46" y="52" width="8" height="18" fill="%23fdba74" /><path d="M20 100 L20 85 C20 74, 30 68, 40 68 L60 68 C70 68, 80 75, 80 85 L80 100 Z" fill="%23f97316" /><path d="M40 68 L50 82 L60 68 Z" fill="%23ffffff" /><circle cx="50" cy="42" r="18" fill="%23fed7aa" /><path d="M32 40 C32 24, 68 24, 68 40 C68 33, 62 31, 50 31 C38 31, 32 33, 32 40 Z" fill="%231c1917" /><path d="M32 35 C35 30, 45 28, 50 31 C55 28, 65 30, 68 35" stroke="%231c1917" stroke-width="2" fill="none" /><path d="M37 34 Q41 32 45 35" stroke="%231c1917" stroke-width="1.5" fill="none" /><path d="M63 34 Q59 32 55 35" stroke="%231c1917" stroke-width="1.5" fill="none" /><circle cx="42" cy="38" r="2" fill="%231c1917" /><circle cx="58" cy="38" r="2" fill="%231c1917" /><circle cx="42" cy="38" r="5" stroke="%231c1917" stroke-width="1.5" fill="none" /><circle cx="58" cy="38" r="5" stroke="%231c1917" stroke-width="1.5" fill="none" /><path d="M47 38 L53 38" stroke="%231c1917" stroke-width="1.5" /><path d="M46 50 Q50 53 54 50" stroke="%23ef4444" stroke-width="1.5" fill="none" /></svg>'
  ];

  constructor(
    private profileService: MyProfileService,
    private fb: FormBuilder,
    private authService: AuthService,
    private attendanceService: AttendanceService,
    private cdr: ChangeDetectorRef
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

    this.attendanceService.getTodayAttendanceState().pipe(take(1)).subscribe(state => {
      this.isPunchedIn = !!state?.isWorking;
      this.cdr.detectChanges();
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

  showEditModal = false;

  toggleEdit(): void {
    this.openEditModal();
  }

  openEditModal(): void {
    if (this.profile$.value) {
      this.patchForm(this.profile$.value);
    }
    this.showEditModal = true;
    this.cdr.detectChanges();
  }

  closeEditModal(): void {
    this.showEditModal = false;
    this.cdr.detectChanges();
  }

  cancelEdit(): void {
    this.closeEditModal();
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
        this.closeEditModal();
        setTimeout(() => this.saveMessage$.next(''), 3000);
      }
    });
  }

  openAvatarModal(): void {
    const current = this.profile$.value;
    this.tempAvatarImage = current?.profileImage || null;
    this.showAvatarModal = true;
    this.cdr.detectChanges();
  }

  closeAvatarModal(): void {
    this.showAvatarModal = false;
    this.cdr.detectChanges();
  }

  selectPredefinedAvatar(avatar: string): void {
    this.tempAvatarImage = avatar;
    this.cdr.detectChanges();
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      const file = input.files[0];
      if (file.size > 2 * 1024 * 1024) {
        alert('File size exceeds 2MB limit!');
        return;
      }
      
      const reader = new FileReader();
      reader.onload = () => {
        this.tempAvatarImage = reader.result as string;
        this.cdr.detectChanges();
      };
      reader.readAsDataURL(file);
    }
  }

  saveAvatar(profile: EmployeeProfile): void {
    const updatedProfile: EmployeeProfile = {
      ...profile,
      profileImage: this.tempAvatarImage || undefined
    };

    this.profileService.updateProfile(updatedProfile).subscribe(res => {
      if (res.success) {
        this.saveMessage$.next('Avatar customized successfully!');
        this.profile$.next(updatedProfile);
        
        if (this.tempAvatarImage) {
          this.authService.updateProfileImage(this.tempAvatarImage);
        }
        
        this.closeAvatarModal();
        setTimeout(() => this.saveMessage$.next(''), 3000);
      }
    });
  }
}
