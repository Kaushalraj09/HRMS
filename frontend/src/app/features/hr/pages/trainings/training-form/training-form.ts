import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router, ActivatedRoute, RouterModule } from '@angular/router';
import { TrainingService } from '../../../../../core/services/training.service';

@Component({
  selector: 'app-training-form',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, RouterModule],
  templateUrl: './training-form.html',
  styleUrls: ['./training-form.css']
})
export class TrainingFormComponent implements OnInit {
  form!: FormGroup;
  isEditMode = false;
  trainingId: number | null = null;
  isLoading = false;
  isSubmitting = false;

  categories = [
    'Technical', 'Compliance', 'Safety', 'HR Policy',
    'Soft Skills', 'Leadership', 'Product Training', 'Onboarding', 'Other'
  ];

  statuses = ['Draft', 'Published', 'Archived'];

  constructor(
    private fb: FormBuilder,
    private trainingService: TrainingService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.initForm();
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      this.isEditMode = true;
      this.trainingId = +idParam;
      this.loadTraining(this.trainingId);
    }
  }

  private initForm(): void {
    const randomCode = 'TRN-' + Math.floor(1000 + Math.random() * 9000);
    this.form = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(200)]],
      code: [randomCode, [Validators.required, Validators.maxLength(50)]],
      category: ['Technical', [Validators.required]],
      description: [''],
      learning_objective: [''],
      trainer_name: ['HR Training Team'],
      estimated_duration_minutes: [60, [Validators.required, Validators.min(1)]],
      start_date: [''],
      end_date: [''],
      status: ['Draft', [Validators.required]]
    });
  }

  loadTraining(id: number): void {
    this.isLoading = true;
    this.trainingService.getTrainingById(id).subscribe({
      next: (t) => {
        this.form.patchValue({
          title: t.title,
          code: t.code,
          category: t.category,
          description: t.description,
          learning_objective: t.learning_objective,
          trainer_name: t.trainer_name,
          estimated_duration_minutes: t.estimated_duration_minutes,
          start_date: t.start_date,
          end_date: t.end_date,
          status: t.status
        });
        this.isLoading = false;
      },
      error: (err) => {
        alert('Failed to load training details: ' + (err.error?.detail || err.message));
        this.router.navigate(['/hr-dashboard/trainings']);
      }
    });
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    const payload = this.form.value;

    if (this.isEditMode && this.trainingId) {
      this.trainingService.updateTraining(this.trainingId, payload).subscribe({
        next: () => {
          this.isSubmitting = false;
          this.router.navigate(['/hr-dashboard/trainings']);
        },
        error: (err) => {
          this.isSubmitting = false;
          alert('Error updating training: ' + (err.error?.detail || err.message));
        }
      });
    } else {
      this.trainingService.createTraining(payload).subscribe({
        next: (res) => {
          this.isSubmitting = false;
          this.router.navigate(['/hr-dashboard/trainings', res.id, 'manage']);
        },
        error: (err) => {
          this.isSubmitting = false;
          alert('Error creating training: ' + (err.error?.detail || err.message));
        }
      });
    }
  }
}
