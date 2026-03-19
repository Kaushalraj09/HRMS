import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-hr-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './hrDashboard.component.html',
  styleUrls: ['./hrDashboard.component.css'],
})
export class HrDashboardComponent {
  projects = [
    { id: 1, name: 'AivanHR' },
    { id: 2, name: 'AivanERP' },
  ];

  clients = [
    { id: 1, name: 'Client A' },
    { id: 2, name: 'Client B' },
    { id: 3, name: 'Client C' },
  ];

  kpis = [
    { label: 'TOTAL PROJECTS', value: 2, icon: 'folder', accent: 'gold' as const },
    { label: 'TOTAL CLIENTS', value: 3, icon: 'building', accent: 'blue' as const },
    { label: 'TOTAL EMPLOYEES', value: 23, icon: 'users', accent: 'green' as const },
    { label: 'PRESENT EMPLOYEES', value: 23, icon: 'userCheck', accent: 'green' as const },
    { label: 'ABSENT (APPROVED)', value: 0, icon: 'userMinus', accent: 'orange' as const },
    { label: 'UNSCHEDULED ABSENTS', value: 0, icon: 'userX', accent: 'red' as const },
  ];

  workLocation = {
    title: 'Work Location Breakdown',
    total: 5,
    segments: [
      { label: 'Work from Office', value: 20, color: '#22c55e' },
      { label: 'Work from Home', value: 80, color: '#2563eb' },
    ],
  };

  gender = {
    title: 'Gender Breakdown',
    total: 19,
    segments: [
      { label: 'Female', value: 16, color: '#fb7185' },
      { label: 'Male', value: 84, color: '#38bdf8' },
    ],
  };

  events = [
    { name: 'ravi n', note: 'Birthday: Oct 15', role: 'L2 Engineer' },
    { name: 'sachin', note: 'Birthday: Oct 15', role: 'Full Stack' },
    { name: 'Sachin M', note: 'Birthday: Oct 15', role: 'Dev' },
  ];
}
