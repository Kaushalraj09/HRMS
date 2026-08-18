import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { AttendanceService } from '../../../../core/services/attendance.service';
import { EmployeeTimesheetRow } from '../../../../core/models/attendance.model';
import { exportTableToPdf } from '../../../../core/utils/pdf-export.util';

@Component({
  selector: 'app-my-attendance',
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './my-attendance.html',
  styleUrl: './my-attendance.css',
})
export class MyAttendance implements OnInit {
  timeSheets: EmployeeTimesheetRow[] = [];
  timeSheetPage = 1;
  readonly timeSheetPageSize = 10;
  filterForm;
  activeRange: 'this-month' | 'last-month' | 'last-7-days' | 'all' | 'custom' = 'all';

  constructor(
    private readonly fb: FormBuilder,
    private readonly attendanceService: AttendanceService,
    private readonly cdr: ChangeDetectorRef
  ) {
    this.filterForm = this.fb.group({
      fromDate: [''],
      toDate: [''],
      status: ['']
    });
  }

  ngOnInit(): void {
    this.loadTimesheets();
  }

  get pagedTimeSheets(): EmployeeTimesheetRow[] {
    const start = (this.timeSheetPage - 1) * this.timeSheetPageSize;
    return this.timeSheets.slice(start, start + this.timeSheetPageSize);
  }

  get timeSheetTotalPages(): number {
    return Math.max(1, Math.ceil(this.timeSheets.length / this.timeSheetPageSize));
  }

  get timeSheetPages(): number[] {
    return Array.from({ length: this.timeSheetTotalPages }, (_, index) => index + 1);
  }

  get timeSheetStartEntry(): number {
    return this.timeSheets.length > 0 ? ((this.timeSheetPage - 1) * this.timeSheetPageSize) + 1 : 0;
  }

  get timeSheetEndEntry(): number {
    return Math.min(this.timeSheetPage * this.timeSheetPageSize, this.timeSheets.length);
  }

  // Summary KPIs
  get presentDaysCount(): number {
    return this.timeSheets.filter(r => r.status === 'Present' || r.status === 'Working' || r.status === 'Half Day').length;
  }

  get absentDaysCount(): number {
    return this.timeSheets.filter(r => r.status === 'Absent').length;
  }

  get leaveDaysCount(): number {
    return this.timeSheets.filter(r => r.status === 'Time Off').length;
  }

  get presentRatePercentage(): number {
    if (this.timeSheets.length === 0) return 0;
    return Math.round((this.presentDaysCount / this.timeSheets.length) * 100);
  }

  get totalWorkHoursDisplay(): string {
    let totalMinutes = 0;
    for (const sheet of this.timeSheets) {
      const match = (sheet.total || sheet.grandTotal || '').match(/(\d+)\s*h\s*(\d+)?/i);
      if (match) {
        const hrs = parseInt(match[1], 10) || 0;
        const mins = parseInt(match[2], 10) || 0;
        totalMinutes += hrs * 60 + mins;
      }
    }
    const hours = Math.floor(totalMinutes / 60);
    const mins = totalMinutes % 60;
    return `${hours}h ${mins}m`;
  }

  get overtimeHoursDisplay(): string {
    let totalMinutes = 0;
    for (const sheet of this.timeSheets) {
      const match = (sheet.overtime || '').match(/(\d+)\s*h\s*(\d+)?/i);
      if (match) {
        const hrs = parseInt(match[1], 10) || 0;
        const mins = parseInt(match[2], 10) || 0;
        totalMinutes += hrs * 60 + mins;
      }
    }
    const hours = Math.floor(totalMinutes / 60);
    const mins = totalMinutes % 60;
    return `${hours}h ${mins}m`;
  }

  isLate(lateText?: string): boolean {
    if (!lateText || lateText === '-' || lateText === '0h 0m' || lateText === '0m' || lateText === '0h') {
      return false;
    }
    return true;
  }

  setTimeSheetPage(page: number): void {
    if (page < 1 || page > this.timeSheetTotalPages) {
      return;
    }
    this.timeSheetPage = page;
  }

  setQuickRange(range: 'this-month' | 'last-month' | 'last-7-days' | 'all'): void {
    this.activeRange = range;
    const now = new Date();
    let from = '';
    let to = '';

    if (range === 'this-month') {
      const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
      from = this.formatDate(startOfMonth);
      to = this.formatDate(now);
    } else if (range === 'last-month') {
      const startOfLastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      const endOfLastMonth = new Date(now.getFullYear(), now.getMonth(), 0);
      from = this.formatDate(startOfLastMonth);
      to = this.formatDate(endOfLastMonth);
    } else if (range === 'last-7-days') {
      const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      from = this.formatDate(sevenDaysAgo);
      to = this.formatDate(now);
    } else if (range === 'all') {
      from = '';
      to = '';
    }

    this.filterForm.patchValue({
      fromDate: from,
      toDate: to
    });
    this.onSearch();
  }

  private formatDate(d: Date): string {
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  }

  onSearch(): void {
    const { fromDate, toDate, status } = this.filterForm.getRawValue();
    this.loadTimesheets(fromDate || '', toDate || '', status || '');
  }

  onReset(): void {
    this.activeRange = 'all';
    this.filterForm.reset({
      fromDate: '',
      toDate: '',
      status: ''
    });
    this.loadTimesheets();
  }

  exportToPdf(): void {
    if (this.timeSheets.length === 0) return;
    const headers = ['Date', 'Day', 'Entry', 'Exit', 'Late', 'Total', 'Overtime', 'Break', 'Grand Total', 'Status'];
    const rows = this.timeSheets.map(r => [
      r.date || '-',
      r.day || '-',
      r.entry || '-',
      r.exit || '-',
      r.late || '-',
      r.total || '-',
      r.overtime || '-',
      r.break || '-',
      r.grandTotal || '-',
      r.status || '-'
    ]);

    const totalDays = this.timeSheets.length;
    const presentDays = this.timeSheets.filter(r => r.status === 'Present' || r.status === 'Working').length;
    const absentDays = this.timeSheets.filter(r => r.status === 'Absent').length;

    exportTableToPdf({
      title: 'Employee Personal Attendance Timesheet',
      subtitle: 'Daily attendance logs, check-in/out times, and total work hours',
      filename: `my_attendance_${new Date().toISOString().slice(0, 10)}.pdf`,
      headers,
      rows,
      metadata: [
        { label: 'Total Logs', value: totalDays },
        { label: 'Present / Working', value: presentDays },
        { label: 'Absent', value: absentDays }
      ]
    });
  }

  exportToCsv(): void {
    this.exportToPdf();
  }

  private loadTimesheets(fromDate: string = '', toDate: string = '', status: string = ''): void {
    this.attendanceService.getMyTimesheets(fromDate, toDate, status).subscribe((rows: EmployeeTimesheetRow[]) => {
      const todayIso = new Date().toISOString().slice(0, 10);
      const visibleRows = rows.filter(row =>
        row.date <= todayIso
        && (
          row.entry !== '-'
          || row.exit !== '-'
          || !!row.scheduledStart
          || !!row.scheduledEnd
          || !!row.taskDescription
        )
      );
      this.timeSheets = this.sortLatestFirst(visibleRows);
      this.timeSheetPage = 1;
      this.cdr.detectChanges();
    });
  }

  private sortLatestFirst(rows: EmployeeTimesheetRow[]): EmployeeTimesheetRow[] {
    return [...rows].sort((left, right) => {
      const dateDiff = new Date(right.date).getTime() - new Date(left.date).getTime();
      if (dateDiff !== 0) {
        return dateDiff;
      }

      return this.timeSortValue(right.entry) - this.timeSortValue(left.entry);
    });
  }

  private timeSortValue(time: string): number {
    const match = time.match(/^(\d{1,2}):(\d{2})/);
    if (!match) {
      return -1;
    }

    return Number(match[1]) * 60 + Number(match[2]);
  }
}
