import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { TrainingService } from '../../../../../core/services/training.service';
import { Training, TrainingKPI } from '../../../../../core/models/training.model';

@Component({
  selector: 'app-training-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './training-list.html',
  styleUrls: ['./training-list.css']
})
export class TrainingListComponent implements OnInit {
  kpis: TrainingKPI | null = null;
  trainings: Training[] = [];
  totalTrainings = 0;

  // Filters
  searchTerm = '';
  selectedCategory = '';
  selectedStatus = '';
  selectedDepartment = '';
  page = 1;
  limit = 10;
  isLoading = false;

  categories = [
    'Technical', 'Compliance', 'Safety', 'HR Policy',
    'Soft Skills', 'Leadership', 'Product Training', 'Onboarding', 'Other'
  ];

  statuses = ['Draft', 'Published', 'Archived'];

  departments = ['Engineering', 'HR', 'Finance', 'Sales', 'Marketing', 'Operations', 'Legal'];

  // Modal controls
  isCreateModalOpen = false;

  constructor(
    private trainingService: TrainingService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadKPIs();
    this.loadTrainings();
  }

  loadKPIs(): void {
    this.trainingService.getKPIs().subscribe({
      next: (data) => (this.kpis = data),
      error: (err) => console.error('Error loading KPIs:', err)
    });
  }

  loadTrainings(): void {
    this.isLoading = true;
    this.trainingService
      .getTrainings({
        search: this.searchTerm,
        category: this.selectedCategory,
        status: this.selectedStatus,
        department: this.selectedDepartment,
        page: this.page,
        limit: this.limit
      })
      .subscribe({
        next: (res) => {
          this.trainings = res.items;
          this.totalTrainings = res.total;
          this.isLoading = false;
        },
        error: (err) => {
          console.error('Error loading trainings:', err);
          this.isLoading = false;
        }
      });
  }

  onSearch(): void {
    this.page = 1;
    this.loadTrainings();
  }

  resetFilters(): void {
    this.searchTerm = '';
    this.selectedCategory = '';
    this.selectedStatus = '';
    this.selectedDepartment = '';
    this.page = 1;
    this.loadTrainings();
  }

  archiveTraining(id: number): void {
    if (confirm('Are you sure you want to archive this training program?')) {
      this.trainingService.archiveTraining(id).subscribe({
        next: () => {
          this.loadKPIs();
          this.loadTrainings();
        },
        error: (err) => alert('Failed to archive training: ' + (err.error?.detail || err.message))
      });
    }
  }

  navigateTo(path: string): void {
    this.router.navigate([path]);
  }
}
