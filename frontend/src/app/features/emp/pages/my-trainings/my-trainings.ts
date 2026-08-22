import { Component, OnInit } from '@angular/core';
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

  constructor(private trainingService: TrainingService) {}

  ngOnInit(): void {
    this.loadMyTrainings();
  }

  loadMyTrainings(): void {
    this.isLoading = true;
    this.trainingService.getMyTrainings().subscribe({
      next: (data) => {
        this.trainings = data;
        this.applyFilter();
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading my trainings:', err);
        this.isLoading = false;
      }
    });
  }

  setFilter(filter: 'ALL' | 'IN_PROGRESS' | 'COMPLETED' | 'NOT_STARTED'): void {
    this.activeFilter = filter;
    this.applyFilter();
  }

  applyFilter(): void {
    if (this.activeFilter === 'ALL') {
      this.filteredTrainings = [...this.trainings];
    } else {
      this.filteredTrainings = this.trainings.filter((t) => t.status === this.activeFilter);
    }
  }
}
