import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration } from 'chart.js';
import ChartDataLabels from 'chartjs-plugin-datalabels';
import { Navbar } from '../../../../shared/components/navbar/navbar';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { HrSidebarService } from '../../components/hr-sidebar/hr-sidebar.service';
import { FormsModule } from '@angular/forms';
import { HrSidebar } from '../../components/hr-sidebar/hr-sidebar';
import { CustomSelectComponent } from '../../../../shared/components/custom-select/custom-select';
import { DashboardService } from '../../../../core/services/dashboard.service';
import { AuthService } from '../../../../core/services/auth.service';
import { AttendanceService } from '../../../../core/services/attendance.service';
import { EmployeeLocationMap } from '../../components/employee-location-map/employee-location-map';

@Component({
  selector: 'app-hr-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, MatFormFieldModule, MatSelectModule, BaseChartDirective, Navbar, RouterModule, HrSidebar, CustomSelectComponent, EmployeeLocationMap],
  templateUrl: './hr-dashboard.html',
  styleUrls: ['./hr-dashboard.css'],
})
export class HrDashboard implements OnInit {
  selectedLang = 'en';
  isHrSidebarOpen$!: import('rxjs').Observable<boolean>;
  isDashboardHome: boolean = true;
  userName = 'HR User';
  isAdmin = false;
  pendingRequests: any[] = [];
  processedRequests: any[] = [];
  recentTimeSheets: any[] = [];
  dashboardError = '';
  searchTerm = '';

  // Photo viewer modal state
  selectedPhotoUrl: string | null = null;
  selectedPhotoEmployeeName: string = '';

  openPhotoModal(url: string, employeeName: string): void {
    this.selectedPhotoUrl = url;
    this.selectedPhotoEmployeeName = employeeName;
  }

  closePhotoModal(): void {
    this.selectedPhotoUrl = null;
    this.selectedPhotoEmployeeName = '';
  }
  
  constructor(
    private hrsidebarService: HrSidebarService,
    private router: Router,
    private readonly dashboardService: DashboardService,
    private readonly authService: AuthService,
    private readonly attendanceService: AttendanceService,
    private readonly cdr: ChangeDetectorRef
  ) {
      this.isHrSidebarOpen$ = this.hrsidebarService.isHrSidebarOpen$;
      this.isDashboardHome = this.router.url.split('?')[0] === '/hr-dashboard';
      this.userName = this.authService.getDisplayName();
      this.router.events.subscribe((event) => {
        if (event instanceof NavigationEnd) {
          this.isDashboardHome = event.urlAfterRedirects.split('?')[0] === '/hr-dashboard';
          this.cdr.detectChanges();
        }
      });
  }

  ngOnInit() {
    const user = this.authService.getCurrentUser();
    this.isAdmin = user?.role === 'admin';

    this.dashboardService.getHrDashboard().subscribe({
      next: (data) => {
        this.dashboardError = '';
        this.workFromHome = data.workModeBreakdown[0];
        this.workFromOffice = data.workModeBreakdown[1];
        this.total = this.workFromHome + this.workFromOffice;
        this.female = data.genderBreakdown[0];
        this.male = data.genderBreakdown[1];
        this.gendertotal = this.female + this.male;
        this.stats = data.quickStats.map(item => ({ total: String(item.total), name: item.name }));
        this.recentTimeSheets = data.recentTimeSheets;
        this.events = data.upcomingEvents;
        this.kpis = [
          { label: 'TOTAL EMPLOYEES', value: data.totalEmployees, icon: 'users', accent: 'blue' as const },
          { label: 'WORKING', value: data.checkedInEmployees, icon: 'userClock', accent: 'blue' as const },
          { label: 'PRESENT', value: data.presentEmployees, icon: 'userCheck', accent: 'green' as const },
          { label: 'ABSENT', value: data.absentEmployees || 0, icon: 'userX', accent: 'red' as const },
          { label: 'NOT MARKED', value: data.notMarkedEmployees, icon: 'minus', accent: 'gold' as const },
          { label: 'HR USERS', value: Number(this.stats[0]?.total || 0), icon: 'building', accent: 'blue' as const },
        ];
        this.pieChartData = {
          labels: ['Remote', 'Office'],
          datasets: [
            {
              data: [this.workFromHome, this.workFromOffice],
              backgroundColor: ['#ff4d6d', '#3a86ff'],
              borderWidth: 2,
            }
          ]
        };
        this.pieChartData2 = {
          labels: ['Female', 'Male'],
          datasets: [
            {
              data: [this.female, this.male],
              backgroundColor: ['#db2777', '#4cc9f0'],
              borderWidth: 2,
            }
          ]
        };
        this.cdr.detectChanges();
      },
      error: (error) => {
        this.dashboardError = error?.error?.detail || 'Unable to load HR dashboard data.';
        this.cdr.detectChanges();
      }
    });
    this.loadPendingRequests();
    this.loadProcessedRequests();

    if (user) {
      this.attendanceService.connectWebSocket(user.id);
    }

    this.attendanceService.timeoffUpdate$.subscribe((event: any) => {
      if (event?.type === 'TIMEOFF_REQUEST') {
        this.loadPendingRequests();
       }
     });
  }

  loadPendingRequests() {
    this.attendanceService.getPendingTimeOffRequests().subscribe(requests => {
      this.pendingRequests = requests;
      this.cdr.detectChanges();
    });
  }

  loadProcessedRequests() {
    this.attendanceService.getProcessedTimeOffRequests().subscribe(requests => {
      this.processedRequests = requests;
      this.cdr.detectChanges();
    });
  }

  processRequest(requestId: number, action: string, type: string = 'Full') {
    let approvedHours: number | undefined;
    if (action === 'APPROVE') {
      const req = this.pendingRequests.find(r => r.id === requestId);
      approvedHours = req?.duration_hours;
    }
    
    this.attendanceService.approveTimeOffRequest(requestId, action, approvedHours).subscribe({
      next: () => {
        alert(`Request ${action.toLowerCase()}d successfully`);
        this.loadPendingRequests();
        this.loadProcessedRequests();
      },
      error: (err) => alert(err?.error?.detail || "Error processing request")
    });
  }

  toggleSidebar() {
    this.hrsidebarService.toggleSidebar();
  }

  onSearch(term: string) {
    this.searchTerm = term || '';
  }

  openProfile() {
    console.log('Opening profile');
  }
  
  projects = [
    { id: 1, name: 'Engineering' },
    { id: 2, name: 'Human Resources' },
    { id: 3, name: 'Finance' },
  ];

  clients = [
    { id: 1, name: 'Office' },
    { id: 2, name: 'Remote' },
    { id: 3, name: 'Hybrid' },
  ];

  get projectOptions() { return [{label: 'Choose a project...', value: ''}, ...this.projects.map(p => ({label: p.name, value: p.id}))]; }
  get clientOptions() { return [{label: 'Choose a client...', value: ''}, ...this.clients.map(c => ({label: c.name, value: c.id}))]; }

  get filteredRecentTimeSheets(): any[] {
    return this.recentTimeSheets.filter((sheet) => this.matchesSearch([
      sheet.employee,
      sheet.employeeCode,
      sheet.date,
      sheet.punchIn,
      sheet.punchOut,
      sheet.breakTime,
      sheet.overtime,
      sheet.totalHours,
      sheet.status
    ]));
  }

  get filteredEvents(): any[] {
    return this.events.filter((event) => this.matchesSearch([event.name, event.note, event.role]));
  }

  kpis: any[] = [];


  events: any[] = [];


  // charts

  workFromHome = 4;
  workFromOffice = 1;

  total = this.workFromHome + this.workFromOffice;

  pieChartType: 'doughnut' = 'doughnut';

  pieChartData: ChartConfiguration<'doughnut'>['data'] = {
    labels: ['Remote', 'Office'],
    datasets: [
      {
        data: [this.workFromHome, this.workFromOffice],
        backgroundColor: ['#ff4d6d', '#3a86ff'],
        borderWidth: 2,
      },
    ],
  };
  pieChartOptions: ChartConfiguration<'doughnut'>['options'] = {
    cutout: '70%',

    layout: {
      padding: {
        top: 20,
        bottom: 20,
        left: 45,
        right: 45,
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
          const dataset = context.chart.data.datasets[context.datasetIndex];
          const total = dataset.data.reduce((sum: number, val: number) => sum + (val || 0), 0);
          if (total === 0) return '0%';
          const percentage = ((value / total) * 100).toFixed(0);
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
        data: [this.female, this.male],
        backgroundColor: ['#db2777', '#4cc9f0'],
        borderWidth: 2,
      },
    ],
  };

  pieChartOptions2: ChartConfiguration<'doughnut'>['options'] = {
    cutout: '70%',

    layout: {
      padding: {
        top: 20,
        bottom: 20,
        left: 45,
        right: 45,
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
          const dataset = context.chart.data.datasets[context.datasetIndex];
          const total = dataset.data.reduce((sum: number, val: number) => sum + (val || 0), 0);
          if (total === 0) return '0%';
          const percentage = ((value / total) * 100).toFixed(0);
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


          const lineLength = 8;
          const midX = startX + Math.cos(angle) * lineLength;
          const midY = startY + Math.sin(angle) * lineLength;


          const horizontalLength = 4;
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
          ctx.fillStyle = '#1e293b';
          ctx.font = 'bold 11px Arial';
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

  stats: any[] = [];

  private matchesSearch(values: Array<string | number | undefined | null>): boolean {
    const query = this.searchTerm.trim().toLowerCase();
    if (!query) {
      return true;
    }

    return values.some((value) => String(value ?? '').toLowerCase().includes(query));
  }
}
