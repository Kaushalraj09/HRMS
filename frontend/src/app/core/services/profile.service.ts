import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { buildApiUrl } from '../config/api.config';
import { EmployeeProfile } from '../models/profile.model';

@Injectable({
  providedIn: 'root'
})
export class MyProfileService {
  private readonly apiUrl = buildApiUrl('/profile');

  constructor(private readonly http: HttpClient) {}

  getProfile(): Observable<EmployeeProfile> {
    return this.http.get<EmployeeProfile>(`${this.apiUrl}/`);
  }

  updateProfile(profile: EmployeeProfile): Observable<{ success: boolean; message: string }> {
    return this.http.put<{ success: boolean; message: string }>(`${this.apiUrl}/update`, {
      personalDetails: profile.personalDetails,
      contactDetails: profile.contactDetails,
      profileImage: profile.profileImage
    });
  }
}
