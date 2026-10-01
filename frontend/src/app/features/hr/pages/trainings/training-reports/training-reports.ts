import { Component, OnInit, ChangeDetectorRef, NgZone } from '@angular/core';
import { CommonModule, Location } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { TrainingService } from '../../../../../core/services/training.service';
import { TrainingReportRow, Training } from '../../../../../core/models/training.model';
import { MasterDataService } from '../../../../../core/services/master-data.service';
import { ToastService } from '../../../../../core/services/toast.service';
import { CustomSelectComponent, SelectOption } from '../../../../../shared/components/custom-select/custom-select';
import { exportTableToPdf } from '../../../../../core/utils/pdf-export.util';

@Component({
  selector: 'app-training-reports',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, CustomSelectComponent],
  templateUrl: './training-reports.html',
  styleUrls: ['./training-reports.css']
})
export class TrainingReportsComponent implements OnInit {
  reports: TrainingReportRow[] = [];
  trainings: Training[] = [];
  departments: any[] = [];
  isLoading = false;

  // Filters
  selectedTrainingId: number | null = null;
  selectedDepartment = '';
  selectedStatus = '';

  get trainingOptions(): SelectOption[] {
    return [
      { label: 'All Trainings', value: null },
      ...this.trainings.map(t => ({ label: `${t.title} (${t.code})`, value: t.id }))
    ];
  }

  get departmentOptions(): SelectOption[] {
    return [
      { label: 'All Departments', value: '' },
      ...this.departments.map(d => ({ label: d.name, value: d.name }))
    ];
  }

  get statusOptions(): SelectOption[] {
    return [
      { label: 'All Statuses', value: '' },
      { label: 'Completed', value: 'COMPLETED' },
      { label: 'In Progress', value: 'IN_PROGRESS' },
      { label: 'Not Started', value: 'NOT_STARTED' }
    ];
  }

  // In-App Toast Popup State
  toast = {
    show: false,
    message: '',
    type: 'success' as 'success' | 'error' | 'info',
    timeout: null as any
  };

  showToast(message: string, type: 'success' | 'error' | 'info' = 'success', duration = 5000): void {
    this.toastService.show(type, message, { duration });
  }

  closeToast(): void {}

  constructor(
    private trainingService: TrainingService,
    private masterDataService: MasterDataService,
    private cdr: ChangeDetectorRef,
    private ngZone: NgZone,
    private router: Router,
    private location: Location,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.loadTrainings();
    this.loadDepartments();
    this.loadReports();
  }

  getBasePrefix(): string {
    return this.router.url.includes('/master-dashboard') ? '/master-dashboard' : (this.router.url.includes('/emp-dashboard') ? '/emp-dashboard' : '/hr-dashboard');
  }

  getTrainingsListRoute(): string {
    return `${this.getBasePrefix()}/trainings`;
  }

  goBack(): void {
    this.location.back();
  }

  loadTrainings(): void {
    this.trainingService.getTrainings({ limit: 1000 }).subscribe((res: any) => {
      this.trainings = res.items || [];
      this.cdr.detectChanges();
    });
  }

  loadDepartments(): void {
    this.masterDataService.getDepartments().subscribe((res: any) => {
      this.departments = res || [];
      this.cdr.detectChanges();
    });
  }

  loadReports(): void {
    this.isLoading = true;
    this.cdr.detectChanges();
    this.trainingService
      .getReports({
        training_id: this.selectedTrainingId || undefined,
        department: this.selectedDepartment || undefined,
        status_filter: this.selectedStatus || undefined
      })
      .subscribe({
        next: (data) => {
          this.reports = data;
          this.isLoading = false;
          this.cdr.detectChanges();
        },
        error: (err) => {
          console.error('Error loading reports:', err);
          this.isLoading = false;
          this.cdr.detectChanges();
        }
      });
  }

  resetFilters(): void {
    this.selectedTrainingId = null;
    this.selectedDepartment = '';
    this.selectedStatus = '';
    this.loadReports();
  }

  exportToPDF(): void {
    if (!this.reports || this.reports.length === 0) {
      this.showToast('No report data available to export.', 'info');
      return;
    }

    const headers = [
      'Emp Code',
      'Employee Name',
      'Department',
      'Training Program',
      'Assigned Date',
      'Completed Date',
      'Progress',
      'Status',
      'Assessment',
      'Score',
      'Result'
    ];

    const rows = this.reports.map((r) => [
      r.employee_code || '-',
      r.employee_name || '-',
      r.department || '-',
      r.category ? `${r.training_title} (${r.category})` : (r.training_title || '-'),
      r.assigned_date ? new Date(r.assigned_date).toLocaleDateString() : '-',
      r.completed_date ? new Date(r.completed_date).toLocaleDateString() : '-',
      `${r.progress_percentage ?? 0}%`,
      r.assignment_status || '-',
      r.assessment_title || 'N/A',
      r.score !== null && r.score !== undefined ? `${r.score} (${r.percentage || '0%'})` : (r.percentage ? `${r.percentage}%` : '-'),
      r.result || '-'
    ]);

    const totalEnrolled = this.reports.length;
    const completedCount = this.reports.filter(
      (r) => (r.assignment_status || '').toUpperCase() === 'COMPLETED' || (r.progress_percentage || 0) >= 100
    ).length;
    const inProgressCount = this.reports.filter(
      (r) => (r.assignment_status || '').toUpperCase() === 'IN_PROGRESS'
    ).length;
    const passedCount = this.reports.filter(
      (r) => (r.result || '').toUpperCase() === 'PASS'
    ).length;

    exportTableToPdf({
      title: 'Training & Assessment Executive Report',
      subtitle: 'Official workforce learning progress, completion records, and assessment performance',
      filename: `training_report_${new Date().toISOString().slice(0, 10)}.pdf`,
      headers,
      rows,
      metadata: [
        { label: 'Total Enrolled', value: totalEnrolled },
        { label: 'Completed', value: completedCount },
        { label: 'In Progress', value: inProgressCount },
        { label: 'Passed Assessments', value: passedCount }
      ]
    });
  }

  exportToCSV(): void {
    this.exportToPDF();
  }
}
