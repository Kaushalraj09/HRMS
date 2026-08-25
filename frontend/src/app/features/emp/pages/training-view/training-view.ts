import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule, Router } from '@angular/router';
import { TrainingService } from '../../../../core/services/training.service';
import { EmployeeTrainingView, TrainingMaterial } from '../../../../core/models/training.model';

@Component({
  selector: 'app-training-view',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './training-view.html',
  styleUrls: ['./training-view.css']
})
export class TrainingViewComponent implements OnInit {
  trainingId!: number;
  data: EmployeeTrainingView | null = null;
  selectedMaterial: TrainingMaterial | null = null;
  isLoading = true;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private trainingService: TrainingService
  ) {}

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      this.trainingId = +idParam;
      this.loadDetail();
    }
  }

  loadDetail(): void {
    this.isLoading = true;
    this.trainingService.getMyTrainingDetail(this.trainingId).subscribe({
      next: (res) => {
        this.data = res;
        if (res.materials && res.materials.length > 0) {
          // Select first incomplete or first material
          const firstIncomplete = res.materials.find((m) => !m.is_completed);
          this.selectedMaterial = firstIncomplete || res.materials[0];
        }
        this.isLoading = false;
      },
      error: (err) => {
        alert('Failed to load training details: ' + (err.error?.detail || err.message));
        this.isLoading = false;
      }
    });
  }

  selectMaterial(mat: TrainingMaterial): void {
    this.selectedMaterial = mat;
  }

  markMaterialCompleted(mat: TrainingMaterial): void {
    this.trainingService.recordMaterialProgress(this.trainingId, mat.id, 100, true).subscribe({
      next: () => {
        mat.is_completed = true;
        this.loadDetail();
      },
      error: (err) => alert('Failed to record progress: ' + (err.error?.detail || err.message))
    });
  }

  startAssessment(): void {
    if (!this.data?.assessment?.id) return;
    this.router.navigate(['/emp-dashboard/assessment', this.data.assessment.id]);
  }
}
