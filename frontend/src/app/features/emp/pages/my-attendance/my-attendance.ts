import { Component, OnInit } from '@angular/core';
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
  filterForm;

  constructor(private readonly fb: FormBuilder, private readonly attendanceService: AttendanceService) {
    this.filterForm = this.fb.group({
      fromDate: [''],
      toDate: [''],
      status: ['']
    });
  }

  ngOnInit(): void {
    this.attendanceService.getMyTimesheets().subscribe(rows => {
      this.allSheets = rows;
      this.timeSheets = rows;
    });
  }

  onSearch(): void {
    const { fromDate, toDate, status } = this.filterForm.getRawValue();

    this.timeSheets = this.allSheets.filter(row => {
      const matchesFrom = !fromDate || row.date >= fromDate;
      const matchesTo = !toDate || row.date <= toDate;
      const matchesStatus = !status || row.status.toLowerCase().includes(status.toLowerCase());
      return matchesFrom && matchesTo && matchesStatus;
    });
  }

  onReset(): void {
    this.filterForm.reset({
      fromDate: '',
      toDate: '',
      status: ''
    });
    this.timeSheets = this.allSheets;
  }
}
