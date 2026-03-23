import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartType } from 'chart.js';
import ChartDataLabels from 'chartjs-plugin-datalabels';

@Component({
  selector: 'app-hr-dashboard',
  standalone: true,
  imports: [CommonModule, MatFormFieldModule, MatSelectModule, BaseChartDirective],
  templateUrl: './hrDashboard.component.html',
  styleUrls: ['./hrDashboard.component.css'],
})
export class HrDashboardComponent {
  selectedLang = 'en';
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


// charts

  workFromHome = 4;
  workFromOffice = 1;

  total = this.workFromHome + this.workFromOffice;

  pieChartType: 'doughnut' = 'doughnut';

  pieChartData: ChartConfiguration<'doughnut'>['data'] = {
    labels: ['Work from Home', 'Work from Office'],
    datasets: [
      {
        data: [this.workFromHome, this.workFromOffice],
        backgroundColor: ['#4e73df', '#1cc88a'],
        borderWidth: 2
      }
    ]
  };
   pieChartOptions: ChartConfiguration<'doughnut'>['options'] = {
    cutout: '70%',

    layout: {
    padding: {
      top: 40,
      bottom: 30,
      left: 40,
      right: 40
    }
  },

    plugins: {
      legend: {
        display: false
      },
      datalabels: {
        color: '#000',
        font: {
          weight: 'bold',
          size: 12
        },
       formatter: (value: number, context: any) => {
          const total = context.chart._metasets[0].total;
          const percentage = ((value / total) * 100).toFixed(0);
          const label = context.chart.data.labels[context.dataIndex];
          return `${percentage}%\n${label}`;
        },
        anchor: 'end',    
        align: 'start',
        offset: 30,
        clamp: false,
        clip: false
      }
    }
  };



  male = 4;
  female = 12;

  gendertotal = this.male + this.female;

  pieChartType2: 'doughnut' = 'doughnut';

  pieChartData2: ChartConfiguration<'doughnut'>['data'] = {
    labels: ['Female', 'Male'],
    datasets: [
      {
        data: [this.male, this.female],
        backgroundColor: ['#da1387', '#8ccdfc'],
        borderWidth: 2
      }
    ]
  };
   pieChartOptions2: ChartConfiguration<'doughnut'>['options'] = {
    cutout: '70%',

    layout: {
    padding: {
      top: 40,
      bottom: 30,
      left: 40,
      right: 40
    }
  },

    plugins: {
      legend: {
        display: false
      },
      datalabels: {
        color: '#000',
        font: {
          weight: 'bold',
          size: 12
        },
       formatter: (value: number, context: any) => {
          const total = context.chart._metasets[0].total;
          const percentage = ((value / total) * 100).toFixed(0);
          const label = context.chart.data.labels[context.dataIndex];
          return `${percentage}%\n${label}`;
        },
        anchor: 'end',    
        align: 'start',
        offset: 12,
        clamp: false,
        clip: false
      }
    }
  };

  pieChartPlugins = [ChartDataLabels];  
}
