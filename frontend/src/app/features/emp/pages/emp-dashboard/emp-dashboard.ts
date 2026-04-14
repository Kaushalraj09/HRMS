import { CommonModule } from '@angular/common';
import { Component, Injectable, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { CalendarModule, CalendarDateFormatter, CalendarNativeDateFormatter, DateFormatterParams } from 'angular-calendar';
import { CalendarEvent } from 'calendar-utils';
import { SharedModule } from '../../../../shared/shared-module';
import { EmpSidebarService } from '../../components/emp-sidebar/emp-sidebar.service';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { EmpSidebar } from '../../components/emp-sidebar/emp-sidebar';
import { AttendanceService } from '../../../../core/services/attendance.service';
import { AuthService } from '../../../../core/services/auth.service';
import { EmployeeAttendanceSummaryItem, EmployeeTimesheetRow, WorkMode } from '../../../../core/models/attendance.model';

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
    CalendarModule,
    SharedModule,
    RouterModule,
    EmpSidebar
  ],
  templateUrl: './emp-dashboard.html',
  styleUrls: ['./emp-dashboard.css'],
  providers: [
    {
      provide: CalendarDateFormatter,
      useClass: CustomDateFormatter,
    },
  ],
})
export class EmpDashboard {
  selectedLang = 'en';
  userName = 'Employee';
  currentDate: Date = new Date();
  status: WorkMode = 'Office';
  isEmpSidebarOpen$!: import('rxjs').Observable<boolean>;
  isDashboardHome: boolean = true;
    
  constructor(
    private empsidebarService: EmpSidebarService,
    private router: Router,
    private readonly attendanceService: AttendanceService,
    private readonly authService: AuthService
  ) {
        this.isEmpSidebarOpen$ = this.empsidebarService.isEmpSidebarOpen$;
        this.isDashboardHome = this.router.url === '/emp-dashboard';
        this.userName = this.authService.getDisplayName();
        this.router.events.subscribe((event) => {
          if (event instanceof NavigationEnd) {
            this.isDashboardHome = event.urlAfterRedirects === '/emp-dashboard';
          }
        });
      }

  toggleSidebar() {
    this.empsidebarService.toggleSidebar();
  }
  onSearch(event: any) {
    console.log('Search:', event);
  }
  openProfile() {
    console.log('Opening profile');
  }
  openNotifications() {
    console.log('Opening notifications');
  }

  ngOnInit() {
    setInterval(() => {
      this.currentDate = new Date();
    }, 1000);

    this.weekNumber = this.getWeekOfMonth(this.selectedDate);
    this.loadDashboardData();
  }

  isPunchedIn: boolean = false;

  togglePunch() {
    this.attendanceService.toggleMyPunch(this.status).subscribe(todayState => {
      this.isPunchedIn = todayState.isPunchedIn;
      this.approvedHours = todayState.approvedHours;
      this.remainingHours = todayState.remainingHours;
      this.status = todayState.workMode;
      this.loadDashboardData();
    });
  }


  approvedHours = 2.0;
  remainingHours = 8;
  startTimer() {

  }


  timeSheets: EmployeeTimesheetRow[] = [];

  attendanceSummary: EmployeeAttendanceSummaryItem[] = [];



  viewDate: Date = new Date();
  selectedDate: Date = new Date();
  weekNumber: number = 2;

  timelineEvents = [
    {
      date: new Date().toISOString().slice(0, 10),
      time: '09:30',
      title: 'Punch In',
      location: 'Office'
    }
  ];

  calendarEvents: CalendarEvent[] = [];
  selectedEvents: Array<{ date: string; time: string; title: string; location: string }> = [];

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
    const isoDate = date.toISOString().slice(0, 10);
    this.selectedEvents = this.timelineEvents.filter(e =>
      e.date === isoDate
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

  private loadDashboardData(): void {
    this.attendanceService.getTodayAttendanceState().subscribe(todayState => {
      this.isPunchedIn = todayState.isPunchedIn;
      this.approvedHours = todayState.approvedHours;
      this.remainingHours = todayState.remainingHours;
      this.status = todayState.workMode;
    });

    this.attendanceService.getMyTimesheets().subscribe(rows => {
      this.timeSheets = rows;
      this.timelineEvents = rows
        .filter(row => row.entry !== '-')
        .flatMap(row => {
          const events = [{ date: row.date, time: row.entry, title: 'Punch In', location: 'Office' }];
          if (row.exit !== '-') {
            events.push({ date: row.date, time: row.exit, title: 'Punch Out', location: 'Office' });
          }
          return events;
        });
      this.calendarEvents = this.timelineEvents.map(event => ({
        start: new Date(`${event.date}T00:00:00`),
        title: event.title
      }));
      this.filterEvents(this.selectedDate);
    });

    this.attendanceService.getMyAttendanceSummary().subscribe(summary => {
      this.attendanceSummary = summary;
    });
  }


}
