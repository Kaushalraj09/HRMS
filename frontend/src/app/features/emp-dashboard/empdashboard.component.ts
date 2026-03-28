import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

@Component({
  selector: 'app-emp-dashboard',
  standalone: true,
  imports: [CommonModule, MatFormFieldModule, MatSelectModule, FormsModule],
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
  }

  isPunchedIn: boolean = false;

  togglePunch() {
    this.isPunchedIn = !this.isPunchedIn;
  }


  approvedHours = 5.0;
  remainingHours = 15;

  hours: number = 0;
  minutes: number = 0;

  totalSeconds: number = 0;
  interval: any;
  isTimerStarted = false;

  startTimer() {
    this.isTimerStarted = true;

    this.totalSeconds = (this.hours * 3600) + (this.minutes * 60);

    if (this.totalSeconds <= 0) return;

    this.interval = setInterval(() => {
      if (this.totalSeconds > 0) {
        this.totalSeconds--;
      } else {
        clearInterval(this.interval);
      }
    }, 1000);
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
    icon: 'fas fa-user-check present blue-icon'
  },
  {
    label: 'Absent with Approval',
    value: 0,
    icon: 'fas fa-user-times approved blue-icon'
  },
  {
    label: 'Absent without Approval',
    value: 0,
    icon: 'fas fa-user-times unapproved blue-icon'
  }
];
}


