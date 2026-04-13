import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';
import { AttendanceRecord, PaginatedAttendance } from '../models/attendance.model';

@Injectable({ providedIn: 'root' })
export class AttendanceService {
  private mockRecords: AttendanceRecord[] = [
    { id: '1', code: 'EMP-001', name: 'Kaushal Raj', department: 'Engineering', date: '2023-11-20', checkIn: '09:00 AM', checkOut: '06:00 PM', hours: '9h', status: 'Present' },
    { id: '2', code: 'EMP-002', name: 'John Doe', department: 'HR', date: '2023-11-20', checkIn: '09:15 AM', checkOut: '', hours: '-', status: 'Checked In' },
    { id: '3', code: 'EMP-003', name: 'Jane Smith', department: 'Finance', date: '2023-11-20', checkIn: '', checkOut: '', hours: '-', status: 'Not Marked' },
    { id: '4', code: 'EMP-004', name: 'Emily Davis', department: 'Marketing', date: '2023-11-20', checkIn: '08:45 AM', checkOut: '05:30 PM', hours: '8h 45m', status: 'Checked Out' },
    { id: '5', code: 'EMP-005', name: 'Michael Brown', department: 'Engineering', date: '2023-11-20', checkIn: '09:05 AM', checkOut: '06:10 PM', hours: '9h 5m', status: 'Present' },
    { id: '6', code: 'EMP-006', name: 'William Jones', department: 'Sales', date: '2023-11-20', checkIn: '09:30 AM', checkOut: '', hours: '-', status: 'Checked In' },
    { id: '7', code: 'EMP-007', name: 'Olivia Miller', department: 'Engineering', date: '2023-11-20', checkIn: '', checkOut: '', hours: '-', status: 'Not Marked' },
    { id: '8', code: 'EMP-008', name: 'James Wilson', department: 'Support', date: '2023-11-20', checkIn: '08:00 AM', checkOut: '04:00 PM', hours: '8h', status: 'Checked Out' },
    { id: '9', code: 'EMP-009', name: 'Benjamin Taylor', department: 'Marketing', date: '2023-11-20', checkIn: '09:00 AM', checkOut: '', hours: '-', status: 'Checked In' },
    { id: '10', code: 'EMP-010', name: 'Sophia Anderson', department: 'Engineering', date: '2023-11-20', checkIn: '09:10 AM', checkOut: '06:00 PM', hours: '8h 50m', status: 'Present' },
    { id: '11', code: 'EMP-011', name: 'Jacob Thomas', department: 'HR', date: '2023-11-20', checkIn: '', checkOut: '', hours: '-', status: 'Not Marked' },
    { id: '12', code: 'EMP-012', name: 'Isabella Jackson', department: 'Finance', date: '2023-11-20', checkIn: '08:30 AM', checkOut: '05:30 PM', hours: '9h', status: 'Present' },
  ];

  getAttendanceLogs(
    page: number, 
    limit: number, 
    fromDate: string, 
    toDate: string, 
    search: string, 
    department: string, 
    status: string
  ): Observable<PaginatedAttendance> {
    let filtered = [...this.mockRecords];

    if (search) {
      const s = search.toLowerCase();
      filtered = filtered.filter(e => e.name.toLowerCase().includes(s) || e.code.toLowerCase().includes(s));
    }
    if (department) {
      filtered = filtered.filter(e => e.department === department);
    }
    if (status) {
      filtered = filtered.filter(e => e.status === status);
    }
    
    // Calculate precise metric sums dynamically based on filters provided exactly mapping requested behaviour
    const startIndex = (page - 1) * limit;
    const paginatedItems = filtered.slice(startIndex, startIndex + limit);

    const metrics = {
      present: filtered.filter(r => r.status === 'Present').length,
      checkedIn: filtered.filter(r => r.status === 'Checked In').length,
      notMarked: filtered.filter(r => r.status === 'Not Marked').length,
      checkedOut: filtered.filter(r => r.status === 'Checked Out').length
    };

    return of({
      data: paginatedItems,
      total: filtered.length,
      metrics
    }).pipe(delay(600));
  }
}
