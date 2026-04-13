import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration } from 'chart.js';
import ChartDataLabels from 'chartjs-plugin-datalabels';
import { SharedModule } from '../../../../shared/shared-module';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { HrSidebarService } from '../../components/hr-sidebar/hr-sidebar.service';
import { FormsModule } from '@angular/forms';
import { HrSidebar } from '../../components/hr-sidebar/hr-sidebar';
import { CustomSelectComponent } from '../../../../shared/components/custom-select/custom-select';


@Component({
  selector: 'app-hr-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, MatFormFieldModule, MatSelectModule, BaseChartDirective, SharedModule, RouterModule, HrSidebar, CustomSelectComponent],
  templateUrl: './hr-dashboard.html',
  styleUrls: ['./hr-dashboard.css'],
})
export class HrDashboard {
  selectedLang = 'en';
  isHrSidebarOpen$!: import('rxjs').Observable<boolean>;
  isDashboardHome: boolean = true;
  
  constructor(private hrsidebarService: HrSidebarService, private router: Router) {
      this.isHrSidebarOpen$ = this.hrsidebarService.isHrSidebarOpen$;
      this.isDashboardHome = this.router.url === '/hr-dashboard';
      this.router.events.subscribe((event) => {
        if (event instanceof NavigationEnd) {
          this.isDashboardHome = event.urlAfterRedirects === '/hr-dashboard';
        }
      });
    }
  toggleSidebar() {
    this.hrsidebarService.toggleSidebar();
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
  
  projects = [
    { id: 1, name: 'AivanHR' },
    { id: 2, name: 'AivanERP' },
  ];

  clients = [
    { id: 1, name: 'Client A' },
    { id: 2, name: 'Client B' },
    { id: 3, name: 'Client C' },
  ];

  get projectOptions() { return [{label: 'Choose a project...', value: ''}, ...this.projects.map(p => ({label: p.name, value: p.id}))]; }
  get clientOptions() { return [{label: 'Choose a client...', value: ''}, ...this.clients.map(c => ({label: c.name, value: c.id}))]; }

  kpis = [
    { label: 'TOTAL PROJECTS', value: 2, icon: 'folder', accent: 'gold' as const },
    { label: 'TOTAL CLIENTS', value: 3, icon: 'building', accent: 'blue' as const },
    { label: 'TOTAL EMPLOYEES', value: 23, icon: 'users', accent: 'green' as const },
    { label: 'PRESENT EMPLOYEES', value: 23, icon: 'userCheck', accent: 'green' as const },
    { label: 'ABSENT (APPROVED)', value: 0, icon: 'userMinus', accent: 'orange' as const },
    { label: 'UNSCHEDULED ABSENTS', value: 0, icon: 'userX', accent: 'red' as const },
  ];


  events = [
    { name: 'Kaushal Raj', note: 'Birthday: Mar 22', role: 'Full Stack Developer' },
    { name: 'Sachin', note: 'Birthday: Apr 02', role: 'Full Stack Developer' },
    { name: 'Rishu', note: 'Birthday: Sep 15', role: 'Dev' },
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
        borderWidth: 2,
      },
    ],
  };
  pieChartOptions: ChartConfiguration<'doughnut'>['options'] = {
    cutout: '70%',

    layout: {
      padding: {
        top: 50,
        bottom: 40,
        left: 50,
        right: 50,
      },
    },

    plugins: {
      legend: {
        display: false,
      },
      datalabels: {
        color: '#f8f3f3',
        font: {
          weight: 'bold',
          size: 12,
        },
        formatter: (value: number, context: any) => {
          const total = context.chart._metasets[0].total;
          const percentage = ((value / total) * 100).toFixed(0);
          const label = context.chart.data.labels[context.dataIndex];
          return `${percentage}%`;
        },
        anchor: 'center',
        align: 'center',
        offset: 15,
        clamp: true,
        clip: false,
      },
    },
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
        borderWidth: 2,
      },
    ],
  };

  pieChartOptions2: ChartConfiguration<'doughnut'>['options'] = {
    cutout: '70%',

    layout: {
      padding: {
        top: 50,
        bottom: 40,
        left: 50,
        right: 50,
      },
    },

    plugins: {
      legend: {
        display: false,
      },
      datalabels: {
        color: '#fcf8f8',
        font: {
          weight: 'bold',
          size: 12,
        },
        formatter: (value: number, context: any) => {
          const total = context.chart._metasets[0].total;
          const percentage = ((value / total) * 100).toFixed(0);
          const label = context.chart.data.labels[context.dataIndex];
          return `${percentage}%`;
        },
        anchor: 'center',
        align: 'center',
        offset: 15,
        clamp: true,
        clip: false,
      },
    },
  };
  connectorLinePlugin = {
    id: 'connectorLinePlugin',
    afterDatasetsDraw(chart: any) {
      const { ctx } = chart;

      chart.data.datasets.forEach((dataset: any, i: number) => {
        const meta = chart.getDatasetMeta(i);

        meta.data.forEach((element: any, index: number) => {
          const { x, y, outerRadius } = element;

          const angle = element.startAngle + (element.endAngle - element.startAngle) / 2;


          const startX = x + Math.cos(angle) * outerRadius;
          const startY = y + Math.sin(angle) * outerRadius;


          const lineLength = 20;
          const midX = startX + Math.cos(angle) * lineLength;
          const midY = startY + Math.sin(angle) * lineLength;


          const horizontalLength = 5;
          const endX = midX + (Math.cos(angle) >= 0 ? horizontalLength : -horizontalLength);
          const endY = midY;

          ctx.save();
          ctx.beginPath();
          const bgColor = dataset.backgroundColor[index];
          ctx.strokeStyle = bgColor;
          ctx.lineWidth = 2;


          ctx.moveTo(startX, startY);
          ctx.lineTo(midX, midY);


          ctx.lineTo(endX, endY);

          ctx.stroke();
          ctx.restore();
          const label = chart.data.labels[index];
          ctx.fillStyle = '#000';
          ctx.font = '12px Arial';
          ctx.weight = 'bold';
          ctx.textAlign = Math.cos(angle) >= 0 ? 'left' : 'right';
          ctx.textBaseline = 'middle';

          ctx.fillText(label, endX + (Math.cos(angle) >= 0 ? 5 : -5), endY);
        });
      });
    }
  };


  pieChartPlugins: any[] = [ChartDataLabels, this.connectorLinePlugin];

  // stats

  absenceChartType: 'line' = 'line';

  absenceChartData: ChartConfiguration<'line'>['data'] = {
    labels: ['Mar 04', 'Mar 05', 'Mar 06', 'Mar 07', 'Mar 08', 'Mar 09', 'Mar 10'],
    datasets: [
      {
        label: 'Absence Count',
        data: [0, 0, 0, 0, 0, 0, 0],
        borderColor: '#6b7280',
        backgroundColor: '#6b7280',
        tension: 0.3,
        pointRadius: 4,
        pointHoverRadius: 5,
        fill: false
      }
    ]
  };
  absenceChartOptions: ChartConfiguration<'line'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,

    plugins: {
      legend: {
        display: false
      }
    },

    scales: {
      x: {
        grid: {
          display: false
        },
        ticks: {
          color: '#6b7280'
        }
      },
      y: {
        beginAtZero: true,
        ticks: {
          stepSize: 1,
          color: '#6b7280'
        },
        grid: {
          color: '#e5e7eb'
        },
        title: {
          display: true,
          text: 'Absence Count'
        }
      }
    }
  };

  stats = [
    { total: '0', name: 'Total Employees' },
    { total: '0', name: 'Present Today' },
    { total: '0', name: 'Total Absents' }
  ];

  // recent time sheets
  recentTimeSheets = [
    { employee: 'Kaushal Raj', date: '10-03-2026', punchIn: '09:30 AM', punchOut: '06:00 PM', breakTime: '1.00 hrs', overtime: '0.00 hrs', totalHours: '7.30 hrs', status: 'Present' },
    { employee: 'Rishu ', date: '10-03-2026', punchIn: '00:00 AM', punchOut: '00:00 PM', breakTime: '00.00 hrs', overtime: '00.00 hrs', totalHours: '00.00 hrs', status: 'Absent' },
    { employee: 'Ankit Singh', date: '10-03-2026', punchIn: '09:30 AM', punchOut: '06:00 PM', breakTime: '1.00 hrs', overtime: '0.00 hrs', totalHours: '7.30 hrs', status: 'Present' }
  ];

}

