import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { buildApiUrl } from '../../../../core/config/api.config';
import { ChangePasswordPayload } from '../../../../core/models/auth.model';

@Injectable({
  providedIn: 'root'
})
export class ChangePasswordService {
  private readonly apiUrl = buildApiUrl('/auth');

  constructor(private readonly http: HttpClient) {}

  updatePassword(data: ChangePasswordPayload): Observable<{ success: boolean; message: string }> {
    // In a real application, you would pass the JWT token in the headers.
    // Assuming your Angular app has an interceptor that attaches the token,
    // this request will be authorized automatically.
    return this.http.post<{ success: boolean; message: string }>(`${this.apiUrl}/change-password`, data);
  }
}
