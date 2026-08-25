import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { TrainingService } from '../../../../core/services/training.service';

@Component({
  selector: 'app-my-trainings',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './my-trainings.html',
  styleUrls: ['./my-trainings.css']
})
export class MyTrainingsComponent implements OnInit {
  trainings: any[] = [];
  filteredTrainings: any[] = [];
  isLoading = true;
  activeFilter: 'ALL' | 'IN_PROGRESS' | 'COMPLETED' | 'NOT_STARTED' = 'ALL';
  searchQuery = '';
  selectedCategory = 'ALL';
  categories: string[] = ['ALL'];

  constructor(
    private trainingService: TrainingService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadMyTrainings();
  }

  loadMyTrainings(): void {
    this.isLoading = true;
    this.cdr.detectChanges();
    this.trainingService.getMyTrainings().subscribe({
      next: (data) => {
        this.trainings = data || [];
        this.extractCategories();
        this.applyFilter();
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error loading my trainings:', err);
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  extractCategories(): void {
    const cats = new Set<string>();
    cats.add('ALL');
    (this.trainings || []).forEach((t) => {
      if (t && t.category) {
        cats.add(t.category);
      }
    });
    this.categories = Array.from(cats);
  }

  setFilter(filter: 'ALL' | 'IN_PROGRESS' | 'COMPLETED' | 'NOT_STARTED'): void {
    this.activeFilter = filter;
    this.applyFilter();
  }

  setCategory(category: string): void {
    this.selectedCategory = category;
    this.applyFilter();
  }

  onSearchChange(): void {
    this.applyFilter();
  }

  clearFilters(): void {
    this.activeFilter = 'ALL';
    this.selectedCategory = 'ALL';
    this.searchQuery = '';
    this.applyFilter();
  }

  get inProgressCount(): number {
    return this.trainings.filter((t) => t.status === 'IN_PROGRESS').length;
  }

  get notStartedCount(): number {
    return this.trainings.filter((t) => t.status === 'NOT_STARTED').length;
  }

  get completedCount(): number {
    return this.trainings.filter((t) => t.status === 'COMPLETED').length;
  }

  applyFilter(): void {
    let result = [...this.trainings];

    if (this.activeFilter !== 'ALL') {
      result = result.filter((t) => t.status === this.activeFilter);
    }

    if (this.selectedCategory !== 'ALL') {
      result = result.filter((t) => t.category === this.selectedCategory);
    }

    if (this.searchQuery && this.searchQuery.trim() !== '') {
      const q = this.searchQuery.toLowerCase().trim();
      result = result.filter(
        (t) =>
          (t.title && t.title.toLowerCase().includes(q)) ||
          (t.description && t.description.toLowerCase().includes(q)) ||
          (t.category && t.category.toLowerCase().includes(q))
      );
    }

    this.filteredTrainings = result;
  }
}

