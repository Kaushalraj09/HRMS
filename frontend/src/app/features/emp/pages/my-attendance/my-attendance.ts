import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { AttendanceService } from '../../../../core/services/attendance.service';
import { EmployeeTimesheetRow } from '../../../../core/models/attendance.model';

@Component({
  selector: 'app-my-attendance',
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './my-attendance.html',
  styleUrl: './my-attendance.css',
})
export class MyAttendance implements OnInit {
  allSheets: EmployeeTimesheetRow[] = [];
  timeSheets: EmployeeTimesheetRow[] = [];
  timeSheetPage = 1;
  readonly timeSheetPageSize = 10;
  filterForm;

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
    this.attendanceService.getMyTimesheets().subscribe((rows: EmployeeTimesheetRow[]) => {
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
      this.allSheets = this.sortLatestFirst(visibleRows);
      this.timeSheets = this.allSheets;
      this.timeSheetPage = 1;
      this.cdr.detectChanges();
    });
  }

  get pagedTimeSheets(): EmployeeTimesheetRow[] {
    const start = (this.timeSheetPage - 1) * this.timeSheetPageSize;
    return this.timeSheets.slice(start, start + this.timeSheetPageSize);
  }

  get timeSheetTotalPages(): number {
    return Math.ceil(this.timeSheets.length / this.timeSheetPageSize);
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

  setTimeSheetPage(page: number): void {
    if (page < 1 || page > this.timeSheetTotalPages) {
      return;
    }

    this.timeSheetPage = page;
  }

  onSearch(): void {
    const { fromDate, toDate, status } = this.filterForm.getRawValue();

    this.timeSheets = this.allSheets.filter(row => {
      const matchesFrom = !fromDate || row.date >= fromDate;
      const matchesTo = !toDate || row.date <= toDate;
      const matchesStatus = !status || row.status.toLowerCase().includes(status.toLowerCase());
      return matchesFrom && matchesTo && matchesStatus;
    });
    this.timeSheetPage = 1;
  }

  onReset(): void {
    this.filterForm.reset({
      fromDate: '',
      toDate: '',
      status: ''
    });
    this.timeSheets = this.allSheets;
    this.timeSheetPage = 1;
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
