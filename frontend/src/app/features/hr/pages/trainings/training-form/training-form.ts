import { Component, OnInit, ChangeDetectorRef, NgZone } from '@angular/core';
import { CommonModule, Location } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router, ActivatedRoute, RouterModule } from '@angular/router';
import { TrainingService } from '../../../../../core/services/training.service';

import { CustomDatepickerComponent } from '../../../../../shared/components/custom-datepicker/custom-datepicker';
import { CustomSelectComponent } from '../../../../../shared/components/custom-select/custom-select';

@Component({
  selector: 'app-training-form',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, RouterModule, CustomDatepickerComponent, CustomSelectComponent],
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

  get categorySelectOptions(): { label: string; value: string }[] {
    return this.categories.map(c => ({ label: c, value: c }));
  }

  readonly statusSelectOptions = [
    { label: 'Draft (Only visible to HR)', value: 'Draft' },
    { label: 'Published (Active & Assignable)', value: 'Published' },
    { label: 'Archived', value: 'Archived' }
  ];

  // In-App Toast Popup State
  toast = {
    show: false,
    message: '',
    type: 'success' as 'success' | 'error' | 'info',
    timeout: null as any
  };

  showToast(message: string, type: 'success' | 'error' | 'info' = 'success', duration = 5000): void {
    if (this.toast.timeout) clearTimeout(this.toast.timeout);
    this.ngZone.run(() => {
      this.toast = {
        show: true,
        message,
        type,
        timeout: setTimeout(() => {
          this.ngZone.run(() => {
            this.toast.show = false;
            this.cdr.detectChanges();
          });
        }, duration)
      };
      this.cdr.detectChanges();
    });
  }

  closeToast(): void {
    if (this.toast.timeout) clearTimeout(this.toast.timeout);
    this.ngZone.run(() => {
      this.toast.show = false;
      this.cdr.detectChanges();
    });
  }

  constructor(
    private fb: FormBuilder,
    private trainingService: TrainingService,
    private router: Router,
    private route: ActivatedRoute,
    private cdr: ChangeDetectorRef,
    private ngZone: NgZone,
    private location: Location
  ) {}

  ngOnInit(): void {
    this.initForm();
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      this.isEditMode = true;
      this.trainingId = +idParam;
      this.loadTraining();
    } else {
      this.isLoading = false;
    }
  }

  getBasePrefix(): string {
    return this.router.url.includes('/master-dashboard') ? '/master-dashboard' : '/hr-dashboard';
  }

  getTrainingsListRoute(): string {
    return `${this.getBasePrefix()}/trainings`;
  }

  goBack(): void {
    this.location.back();
  }

  initForm(): void {
    this.form = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(200)]],
      category: ['Technical', Validators.required],
      description: [''],
      learning_objective: [''],
      trainer_name: [''],
      estimated_duration_minutes: [null, [Validators.min(1)]],
      start_date: [null],
      end_date: [null],
      status: ['Draft', Validators.required]
    });
  }

  loadTraining(): void {
    this.isLoading = true;
    this.cdr.detectChanges();
    this.trainingService.getTrainingById(this.trainingId!).subscribe({
      next: (t) => {
        this.form.patchValue({
          title: t.title || '',
          category: t.category || 'Technical',
          description: t.description || '',
          learning_objective: t.learning_objective || '',
          trainer_name: t.trainer_name || '',
          estimated_duration_minutes: t.estimated_duration_minutes || null,
          start_date: t.start_date || null,
          end_date: t.end_date || null,
          status: t.status || 'Draft'
        });
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.isLoading = false;
        this.showToast('Failed to load training details: ' + (err.error?.detail || err.message), 'error');
        this.router.navigate([this.getTrainingsListRoute()]);
        this.cdr.detectChanges();
      }
    });
  }

  private formatError(err: any): string {
    if (!err) return 'Unknown error';
    const detail = err.error?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((d: any) => `${d.loc ? d.loc.join('.') + ': ' : ''}${d.msg || JSON.stringify(d)}`).join('\n');
    }
    if (typeof detail === 'object' && detail !== null) {
      return JSON.stringify(detail);
    }
    return err.message || 'Unexpected server error';
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.showToast('Please fill in all required fields.', 'error');
      return;
    }

    this.isSubmitting = true;
    const raw = this.form.value;
    const payload = {
      ...raw,
      start_date: raw.start_date ? raw.start_date : null,
      end_date: raw.end_date ? raw.end_date : null,
    };

    if (this.isEditMode && this.trainingId) {
      this.trainingService.updateTraining(this.trainingId, payload).subscribe({
        next: () => {
          this.isSubmitting = false;
          this.router.navigate([this.getTrainingsListRoute()]);
        },
        error: (err) => {
          this.isSubmitting = false;
          this.showToast('Error updating training: ' + this.formatError(err), 'error');
        }
      });
    } else {
      this.trainingService.createTraining(payload).subscribe({
        next: (res) => {
          this.isSubmitting = false;
          this.router.navigate([this.getBasePrefix(), 'trainings', res.id.toString(), 'manage']);
        },
        error: (err) => {
          this.isSubmitting = false;
          this.showToast('Error creating training: ' + this.formatError(err), 'error');
        }
      });
    }
  }
}
