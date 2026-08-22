import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { TrainingService } from '../../../../core/services/training.service';

@Component({
  selector: 'app-training-widget',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './training-widget.html',
  styleUrls: ['./training-widget.css']
})
export class TrainingWidgetComponent implements OnInit {
  trainings: any[] = [];
  assignedCount = 0;
  inProgressCount = 0;
  completedCount = 0;
  nextUrgentTraining: any = null;
  isLoading = true;

  constructor(private trainingService: TrainingService) {}

  ngOnInit(): void {
    this.loadWidgetData();
  }

  loadWidgetData(): void {
    this.isLoading = true;
    this.trainingService.getMyTrainings().subscribe({
      next: (data) => {
        this.trainings = data || [];
        this.assignedCount = this.trainings.length;
        this.inProgressCount = this.trainings.filter((t) => t.status === 'IN_PROGRESS').length;
        this.completedCount = this.trainings.filter((t) => t.status === 'COMPLETED').length;

        // Find next urgent pending training
        const pending = this.trainings.filter((t) => t.status !== 'COMPLETED');
        if (pending.length > 0) {
          this.nextUrgentTraining = pending[0];
        }
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading training widget:', err);
        this.isLoading = false;
      }
    });
  }
}
