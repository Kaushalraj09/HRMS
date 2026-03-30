import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { CalendarModule } from 'angular-calendar';

@Component({
  selector: 'app-emp-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatFormFieldModule,
    MatSelectModule,
    FormsModule,
    CalendarModule
  ],
  templateUrl: './empdashboard.component.html',
  styleUrls: ['./empdashboard.component.css'],
})
export class EmpDashboardComponent {
  selectedLang = 'en';
  currentDate: Date = new Date();
  status: string = 'work';

  ngOnInit() {
    setInterval(() => {
      this.currentDate = new Date();
    }, 1000);

    this.filterEvents(this.selectedDate);
  }

  isPunchedIn: boolean = false;

  togglePunch() {
    this.isPunchedIn = !this.isPunchedIn;
  }


  approvedHours = 2.0;
  remainingHours = 8;
  startTimer() {

  }


  timeSheets: any[] = [];

  attendanceSummary = [
    {
      label: 'Total Days',
      value: 0,
      icon: 'fas fa-calendar total blue-icon'
    },
    {
      label: 'Worked Days',
      value: 0,
      icon: 'fas fa-calendar-check worked blue-icon'
    },
    {
      label: 'Present',
      value: 0,
      icon: 'fas fa-check-circle blue-icon'
    },
    {
      label: 'Absent with Approval',
      value: 0,
      icon: 'fas fa-user-check blue-icon'
    },
    {
      label: 'Absent without Approval',
      value: 0,
      icon: 'fas fa-user-times unapproved blue-icon'
    }
  ];



  viewDate: Date = new Date();
  selectedDate: Date = new Date();
  weekNumber: number = 2;

  events = [
    {
      date: new Date(2026, 2, 30),
      time: '10:08 PM',
      title: 'Punch In',
      location: 'Office'
    },
    {
      date: new Date(2026, 2, 30),
      time: '10:12 PM',
      title: 'Punch Out',
      location: 'Office'
    }
  ];


  selectedEvents: any[] = [];

  onDayClick(day: any) {
    this.selectedDate = day.date;
    this.weekNumber = this.getWeekOfMonth(day.date);
    this.filterEvents(day.date);
  }

  getWeekOfMonth(date: Date): number {
    const startOfMonth = new Date(date.getFullYear(), date.getMonth(), 1);
    const dayOfMonth = date.getDate();
    const dayOfWeek = startOfMonth.getDay();
    return Math.ceil((dayOfMonth + dayOfWeek) / 7);
  }

  filterEvents(date: Date) {
    this.selectedEvents = this.events.filter(e =>
      e.date.toDateString() === date.toDateString()
    );
  }
}


