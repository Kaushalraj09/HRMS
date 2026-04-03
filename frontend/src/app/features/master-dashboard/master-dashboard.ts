import { Component } from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../shared/shared-module';

@Component({
  selector: 'app-master-dashboard',
  imports: [MatFormFieldModule, MatSelectModule, CommonModule, FormsModule, SharedModule],
  standalone: true,
  templateUrl: './master-dashboard.html',
  styleUrl: './master-dashboard.css',
})
export class MasterDashboard {
  selectedLang = 'en';

  toggleSidebar() {
    console.log('Sidebar toggled');
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

  fullDetails = [
    {
      icon: 'fas fa-cubes',
      label: 'Total Projects',
      value: '2'
    },
    {
      icon: 'fas fa-users',
      label: 'Total Clients',
      value: '3'
    },
    {
      icon: 'fas fa-user',
      label: 'Total Employees',
      value: '23'
    },
    {
      icon: 'fas fa-clock',
      label: 'Pending Work Mode Requests',
      value: '0'
    },
  ]

  clients = [
    {
      name: 'kaushal raj',
      role: 'CEO',
      email: 'kaushal@example.com',
      status: 'Active'
    },
    {
      name: 'Shubham Mandal',
      role: 'Manager',
      email: 'shubham@example.com',
      status: 'Active'
    }
  ]

  projects = [
    {
      name: 'Office Management',
      value: 1000000,
      progress: 60,
      tasks: '1 open tasks, 9 tasks completed'
    },
    {
      name: 'Website Redesign',
      value: 500000,
      progress: 40,
      tasks: '2 open tasks, 5 tasks completed'
    }
  ]
}