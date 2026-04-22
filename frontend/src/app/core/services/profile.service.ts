import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';
import { EmployeeProfile } from '../models/profile.model';

import { Phase1StoreService } from './phase1-store.service';

@Injectable({
  providedIn: 'root'
})
export class MyProfileService {
  constructor(private readonly store: Phase1StoreService) {}

  getProfile(): Observable<EmployeeProfile> {
    const profile = this.store.getEmployeeProfile() || {
      id: 'na',
      employeeId: 'NA',
      firstName: 'Portal',
      lastName: 'User',
      initials: 'PU',
      role: 'User',
      department: 'General',
      shift: 'General Shift',
      status: 'Active' as const,
      personalDetails: {
        firstName: 'Portal',
        lastName: 'User',
        gender: 'Not Available',
        dateOfBirth: '2000-01-01'
      },
      contactDetails: {
        officialEmail: 'not.available@aivan.com',
        mobileNumber: '0000000000',
        location: 'Not Assigned'
      }
    };
    return of(profile).pipe(delay(300));
  }

  updateProfile(profile: EmployeeProfile): Observable<{ success: boolean; message: string }> {
    return of(this.store.updateEmployeeProfile(profile)).pipe(delay(400));
  }
}
