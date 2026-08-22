import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { TrainingService } from '../../../../core/services/training.service';
import { AssessmentResult } from '../../../../core/models/training.model';

@Component({
  selector: 'app-assessment-result',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './assessment-result.html',
  styleUrls: ['./assessment-result.css']
})
export class AssessmentResultComponent implements OnInit {
  attemptId!: number;
  result: AssessmentResult | null = null;
  isLoading = true;

  constructor(
    private route: ActivatedRoute,
    private trainingService: TrainingService
  ) {}

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      this.attemptId = +idParam;
      this.loadResult();
    }
  }

  loadResult(): void {
    this.isLoading = true;
    this.trainingService.getAttemptResult(this.attemptId).subscribe({
      next: (res) => {
        this.result = res;
        this.isLoading = false;
      },
      error: (err) => {
        alert('Failed to load attempt result: ' + (err.error?.detail || err.message));
        this.isLoading = false;
      }
    });
  }
}
