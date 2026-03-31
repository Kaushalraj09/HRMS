import { CommonModule } from '@angular/common';
import { Component, Injectable } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { CalendarModule, CalendarDateFormatter, CalendarNativeDateFormatter, DateFormatterParams } from 'angular-calendar';

@Injectable()
export class CustomDateFormatter extends CalendarNativeDateFormatter {
  public override monthViewColumnHeader({ date, locale }: DateFormatterParams): string {
    return new Intl.DateTimeFormat(locale, { weekday: 'narrow' }).format(date);
  }
}

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
  providers: [
    {
      provide: CalendarDateFormatter,
      useClass: CustomDateFormatter,
    },
  ],
})
export class EmpDashboardComponent {
  selectedLang = 'en';
  currentDate: Date = new Date();
  status: string = 'work';

  ngOnInit() {
    setInterval(() => {
      this.currentDate = new Date();
    }, 1000);

    this.weekNumber = this.getWeekOfMonth(this.selectedDate);
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
    },
    {
      date: new Date(2026, 2, 31),
      time: '06:12 PM',
      title: 'Punch Out',
      location: 'Office'
    }
  ];


  selectedEvents: any[] = [];

  onDayClick(day: { date: Date }) {
    this.selectedDate = day.date;
    this.weekNumber = this.getWeekOfMonth(day.date);
    this.filterEvents(day.date);
  }

  getWeekOfMonth(date: Date): number {
    const firstDayOfMonth = new Date(date.getFullYear(), date.getMonth(), 1);
    const dayOfWeek = firstDayOfMonth.getDay();
    return Math.ceil((date.getDate() + dayOfWeek) / 7);
  }

  filterEvents(date: Date) {
    this.selectedEvents = this.events.filter(e =>
      e.date.toDateString() === date.toDateString()
    );
  }

  latestNews_content = [
    {
      heading: 'Welcome to Aivan ERP System',
      contents: 'We are excited to announce the launch of our new ERP system designed to streamline your business operations and improve productivity.',
      newsType: 'General',
      date: new Date(2026, 3, 10)
    },
    {
      heading: 'Welcome to New Branch opening',
      contents: 'We are excited to announce the launch of our new branch in downtown!',
      newsType: 'Promotional',
      date: new Date(2026, 3, 10)
    },

  ];


}

