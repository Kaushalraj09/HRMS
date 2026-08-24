import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { TrainingService } from '../../../../../core/services/training.service';
import { Training, TrainingKPI, Assessment, AssessmentQuestion } from '../../../../../core/models/training.model';

@Component({
  selector: 'app-training-list',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, RouterModule],
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

  // Modal 1: Create Training Modal Form
  isCreateModalOpen = false;
  isSubmittingTraining = false;
  createForm!: FormGroup;

  // Modal 2: Assessment Builder / Create Test Modal Form
  isAssessmentModalOpen = false;
  activeAssessmentTraining: Training | null = null;
  assessmentData: Assessment | null = null;
  isLoadingAssessment = false;
  isSavingAssessmentSettings = false;
  isAddingQuestion = false;
  assessmentSettingsForm!: FormGroup;
  questionForm!: FormGroup;
  selectedCorrectOptionIndex = 1;

  constructor(
    private fb: FormBuilder,
    private trainingService: TrainingService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.initCreateForm();
    this.initAssessmentForms();
    this.loadKPIs();
    this.loadTrainings();
  }

  // ─── Modal 1: Create Training Form Methods ──────────────────────────────

  initCreateForm(): void {
    const randomCode = 'TRN-' + Math.floor(1000 + Math.random() * 9000);
    this.createForm = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(200)]],
      code: [randomCode, [Validators.required, Validators.maxLength(50)]],
      category: ['Technical', [Validators.required]],
      description: [''],
      learning_objective: [''],
      trainer_name: ['HR Training Team'],
      estimated_duration_minutes: [60, [Validators.required, Validators.min(1)]],
      start_date: [''],
      end_date: [''],
      status: ['Published', [Validators.required]]
    });
  }

  openCreateModal(): void {
    this.initCreateForm();
    this.isCreateModalOpen = true;
    this.cdr.detectChanges();
  }

  closeCreateModal(): void {
    this.isCreateModalOpen = false;
    this.cdr.detectChanges();
  }

  onSubmitCreateTraining(): void {
    if (this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }

    this.isSubmittingTraining = true;
    this.cdr.detectChanges();

    this.trainingService.createTraining(this.createForm.value).subscribe({
      next: (res) => {
        this.isSubmittingTraining = false;
        this.closeCreateModal();
        this.loadKPIs();
        this.loadTrainings();
      },
      error: (err) => {
        this.isSubmittingTraining = false;
        alert('Error creating training program: ' + (err.error?.detail || err.message));
        this.cdr.detectChanges();
      }
    });
  }

  // ─── Modal 2: Assessment Builder / Create Test Methods ──────────────────

  initAssessmentForms(): void {
    this.assessmentSettingsForm = this.fb.group({
      title: ['Assessment Test', [Validators.required, Validators.maxLength(200)]],
      instructions: ['Please answer all questions carefully before timer expires.'],
      duration_minutes: [20, [Validators.required, Validators.min(1)]],
      passing_percentage: [60, [Validators.required, Validators.min(0), Validators.max(100)]],
      max_attempts: [1, [Validators.required, Validators.min(1)]],
      randomize_questions: [false],
      randomize_options: [false],
      show_result: [true],
      show_correct_answers: [false],
      status: ['Published']
    });

    this.questionForm = this.fb.group({
      question_text: ['', [Validators.required]],
      marks: [1, [Validators.required, Validators.min(0.5)]],
      difficulty: ['Medium', [Validators.required]],
      explanation: [''],
      options: this.fb.array([
        this.fb.group({ option_key: ['A'], option_text: ['', Validators.required], is_correct: [false] }),
        this.fb.group({ option_key: ['B'], option_text: ['', Validators.required], is_correct: [true] }),
        this.fb.group({ option_key: ['C'], option_text: ['', Validators.required], is_correct: [false] }),
        this.fb.group({ option_key: ['D'], option_text: ['', Validators.required], is_correct: [false] })
      ])
    });
  }

  get optionsArray(): FormArray {
    return this.questionForm.get('options') as FormArray;
  }

  openAssessmentModal(item: Training): void {
    this.activeAssessmentTraining = item;
    this.isAssessmentModalOpen = true;
    this.initAssessmentForms();
    this.loadAssessmentForTraining(item.id);
    this.cdr.detectChanges();
  }

  closeAssessmentModal(): void {
    this.isAssessmentModalOpen = false;
    this.activeAssessmentTraining = null;
    this.assessmentData = null;
    this.loadTrainings();
    this.cdr.detectChanges();
  }

  loadAssessmentForTraining(trainingId: number): void {
    this.isLoadingAssessment = true;
    this.cdr.detectChanges();
    this.trainingService.getAssessment(trainingId).subscribe({
      next: (data) => {
        this.assessmentData = data;
        this.assessmentSettingsForm.patchValue({
          title: data.title,
          instructions: data.instructions,
          duration_minutes: data.duration_minutes,
          passing_percentage: data.passing_percentage,
          max_attempts: data.max_attempts,
          randomize_questions: data.randomize_questions,
          randomize_options: data.randomize_options,
          show_result: data.show_result,
          show_correct_answers: data.show_correct_answers,
          status: data.status
        });
        this.isLoadingAssessment = false;
        this.cdr.detectChanges();
      },
      error: () => {
        if (this.activeAssessmentTraining) {
          this.assessmentSettingsForm.patchValue({ title: `${this.activeAssessmentTraining.title} Test` });
        }
        this.isLoadingAssessment = false;
        this.cdr.detectChanges();
      }
    });
  }

  saveAssessmentSettings(): void {
    if (!this.activeAssessmentTraining || this.assessmentSettingsForm.invalid) return;
    this.isSavingAssessmentSettings = true;
    this.cdr.detectChanges();

    this.trainingService.saveAssessment(this.activeAssessmentTraining.id, this.assessmentSettingsForm.value).subscribe({
      next: () => {
        this.isSavingAssessmentSettings = false;
        this.loadAssessmentForTraining(this.activeAssessmentTraining!.id);
      },
      error: (err) => {
        this.isSavingAssessmentSettings = false;
        alert('Error saving assessment: ' + (err.error?.detail || err.message));
        this.cdr.detectChanges();
      }
    });
  }

  setCorrectOption(idx: number): void {
    this.selectedCorrectOptionIndex = idx;
    const opts = this.optionsArray;
    for (let i = 0; i < opts.length; i++) {
      opts.at(i).get('is_correct')?.setValue(i === idx);
    }
  }

  addQuestion(): void {
    if (!this.assessmentData || !this.assessmentData.id) {
      alert('Please save assessment settings first before adding questions.');
      return;
    }

    if (this.questionForm.invalid) {
      this.questionForm.markAllAsTouched();
      alert('Please fill in all question fields and options.');
      return;
    }

    this.isAddingQuestion = true;
    this.setCorrectOption(this.selectedCorrectOptionIndex);
    this.cdr.detectChanges();

    this.trainingService.addQuestion(this.assessmentData.id, this.questionForm.value).subscribe({
      next: () => {
        this.isAddingQuestion = false;
        this.resetQuestionForm();
        this.loadAssessmentForTraining(this.activeAssessmentTraining!.id);
      },
      error: (err) => {
        this.isAddingQuestion = false;
        alert('Error adding question: ' + (err.error?.detail || err.message));
        this.cdr.detectChanges();
      }
    });
  }

  deleteQuestion(qId: number): void {
    if (!this.assessmentData?.id) return;
    if (confirm('Delete this question from assessment?')) {
      this.trainingService.deleteQuestion(this.assessmentData.id, qId).subscribe({
        next: () => this.loadAssessmentForTraining(this.activeAssessmentTraining!.id),
        error: (err) => alert('Delete failed: ' + (err.error?.detail || err.message))
      });
    }
  }

  resetQuestionForm(): void {
    this.questionForm.reset({
      question_text: '',
      marks: 1,
      difficulty: 'Medium',
      explanation: ''
    });
    const opts = this.optionsArray;
    const keys: Array<'A'|'B'|'C'|'D'> = ['A', 'B', 'C', 'D'];
    for (let i = 0; i < 4; i++) {
      opts.at(i).patchValue({
        option_key: keys[i],
        option_text: '',
        is_correct: i === 1
      });
    }
    this.selectedCorrectOptionIndex = 1;
  }

  getBasePrefix(): string {
    return this.router.url.includes('/master-dashboard') ? '/master-dashboard' : '/hr-dashboard';
  }

  getCreateRoute(): string {
    return `${this.getBasePrefix()}/trainings/create`;
  }

  getReportsRoute(): string {
    return `${this.getBasePrefix()}/training-reports`;
  }

  getManageRoute(id: number): string[] {
    return [this.getBasePrefix(), 'trainings', id.toString(), 'manage'];
  }

  getAssessmentRoute(id: number): string[] {
    return [this.getBasePrefix(), 'trainings', id.toString(), 'assessment'];
  }

  getEditRoute(id: number): string[] {
    return [this.getBasePrefix(), 'trainings', id.toString(), 'edit'];
  }

  loadKPIs(): void {
    this.trainingService.getKPIs().subscribe({
      next: (data) => {
        this.kpis = data;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error loading KPIs:', err);
        this.cdr.detectChanges();
      }
    });
  }

  loadTrainings(): void {
    this.isLoading = true;
    this.cdr.detectChanges();
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
          this.trainings = res.items || [];
          this.totalTrainings = res.total || 0;
          this.isLoading = false;
          this.cdr.detectChanges();
        },
        error: (err) => {
          console.error('Error loading trainings:', err);
          this.isLoading = false;
          this.cdr.detectChanges();
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
