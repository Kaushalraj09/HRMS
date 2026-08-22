import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { TrainingService } from '../../../../../core/services/training.service';
import { TrainingReportRow, Training } from '../../../../../core/models/training.model';
import { MasterDataService } from '../../../../../core/services/master-data.service';

@Component({
  selector: 'app-training-reports',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
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

  constructor(
    private trainingService: TrainingService,
    private masterDataService: MasterDataService
  ) {}

  ngOnInit(): void {
    this.loadTrainings();
    this.loadDepartments();
    this.loadReports();
  }

  loadTrainings(): void {
    this.trainingService.getTrainings({ limit: 100 }).subscribe((res) => (this.trainings = res.items || []));
  }

  loadDepartments(): void {
    this.masterDataService.getDepartments().subscribe((res: any) => (this.departments = res || []));
  }

  loadReports(): void {
    this.isLoading = true;
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
        },
        error: (err) => {
          console.error('Error loading reports:', err);
          this.isLoading = false;
        }
      });
  }

  resetFilters(): void {
    this.selectedTrainingId = null;
    this.selectedDepartment = '';
    this.selectedStatus = '';
    this.loadReports();
  }

  exportToCSV(): void {
    if (!this.reports || this.reports.length === 0) {
      alert('No report data available to export.');
      return;
    }

    const headers = [
      'Employee Code',
      'Employee Name',
      'Department',
      'Training Program',
      'Category',
      'Assigned Date',
      'Completed Date',
      'Progress %',
      'Assignment Status',
      'Assessment Title',
      'Score',
      'Percentage',
      'Pass/Fail Result'
    ];

    const rows = this.reports.map((r) => [
      `"${r.employee_code || ''}"`,
      `"${r.employee_name || ''}"`,
      `"${r.department || ''}"`,
      `"${r.training_title || ''}"`,
      `"${r.category || ''}"`,
      `"${r.assigned_date ? new Date(r.assigned_date).toLocaleDateString() : ''}"`,
      `"${r.completed_date ? new Date(r.completed_date).toLocaleDateString() : ''}"`,
      `"${r.progress_percentage || 0}%"`,
      `"${r.assignment_status || ''}"`,
      `"${r.assessment_title || ''}"`,
      `"${r.score || ''}"`,
      `"${r.percentage || ''}"`,
      `"${r.result || ''}"`
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Training_Report_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}
