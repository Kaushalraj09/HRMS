import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';
import { EmployeeProfile } from '../models/profile.model';

@Injectable({
  providedIn: 'root'
})
export class MyProfileService {

  constructor() { }

  getProfile(): Observable<EmployeeProfile> {
    const mockProfile: EmployeeProfile = {
      id: '1',
      employeeId: 'EMP001',
      firstName: 'Kaushal',
      lastName: 'Raj',
      initials: 'KR',
      role: 'Full Stack Developer',
      department: 'Engineering',
      shift: 'General Shift',
      status: 'Active',
      personalDetails: {
        firstName: 'Kaushal',
        lastName: 'Raj',
        gender: 'Male',
        dateOfBirth: '1995-03-22'
      },
      contactDetails: {
        officialEmail: 'kaushal.raj@company.com',
        mobileNumber: '+91 9876543210',
        location: 'Tech Park, Block B, Bangalore'
      }
    };

    // Simulate network delay for loading skeleton
    return of(mockProfile).pipe(delay(800));
  }
}
