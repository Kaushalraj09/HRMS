import { Component, OnInit, ChangeDetectorRef, HostListener, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { TrainingService } from '../../../../../core/services/training.service';
import { Training, TrainingKPI, Assessment, AssessmentQuestion } from '../../../../../core/models/training.model';
import { CustomSelectComponent, SelectOption } from '../../../../../shared/components/custom-select/custom-select';
import { CustomDatepickerComponent } from '../../../../../shared/components/custom-datepicker/custom-datepicker';

@Component({
  selector: 'app-training-list',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, RouterModule, CustomSelectComponent, CustomDatepickerComponent],
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

  // Dropdown toggle state
  activeDropdownId: number | null = null;

  // Custom Confirmation Popup State
  confirmModal = {
    isOpen: false,
    title: '',
    message: '',
    confirmBtnText: 'Confirm',
    cancelBtnText: 'Cancel',
    confirmBtnClass: 'btn-primary',
    iconClass: 'fas fa-exclamation-triangle',
    onConfirm: () => {}
  };

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

  openConfirm(options: {
    title: string;
    message: string;
    confirmBtnText?: string;
    cancelBtnText?: string;
    confirmBtnClass?: string;
    iconClass?: string;
    onConfirm: () => void;
  }): void {
    this.confirmModal = {
      isOpen: true,
      title: options.title,
      message: options.message,
      confirmBtnText: options.confirmBtnText || 'Confirm',
      cancelBtnText: options.cancelBtnText || 'Cancel',
      confirmBtnClass: options.confirmBtnClass || 'btn-primary',
      iconClass: options.iconClass || 'fas fa-exclamation-triangle',
      onConfirm: options.onConfirm
    };
    this.cdr.detectChanges();
  }

  closeConfirm(): void {
    this.confirmModal.isOpen = false;
    this.cdr.detectChanges();
  }

  executeConfirm(): void {
    const action = this.confirmModal.onConfirm;
    this.closeConfirm();
    if (action) action();
  }

  @HostListener('document:click')
  onDocumentClick(): void {
    if (this.activeDropdownId !== null) {
      this.activeDropdownId = null;
      this.cdr.detectChanges();
    }
  }

  toggleDropdown(id: number, event: Event): void {
    event.stopPropagation();
    this.activeDropdownId = this.activeDropdownId === id ? null : id;
    this.cdr.detectChanges();
  }

  categories = [
    'Technical', 'Compliance', 'Safety', 'HR Policy',
    'Soft Skills', 'Leadership', 'Product Training', 'Onboarding', 'Other'
  ];

  statuses = ['Draft', 'Published', 'Archived'];

  departments = ['Engineering', 'HR', 'Finance', 'Sales', 'Marketing', 'Operations', 'Legal'];

  get categorySelectOptions(): { label: string; value: string }[] {
    return this.categories.map(c => ({ label: c, value: c }));
  }

  readonly statusModalSelectOptions = [
    { label: 'Published', value: 'Published' },
    { label: 'Draft', value: 'Draft' },
    { label: 'Archived', value: 'Archived' }
  ];

  readonly difficultySelectOptions = [
    { label: 'Beginner', value: 'Beginner' },
    { label: 'Intermediate', value: 'Intermediate' },
    { label: 'Advanced', value: 'Advanced' }
  ];

  get categoryOptions(): SelectOption[] {
    return [
      { label: 'All Categories', value: '' },
      ...this.categories.map(c => ({ label: c, value: c }))
    ];
  }

  get statusOptions(): SelectOption[] {
    return [
      { label: 'All Statuses', value: '' },
      ...this.statuses.map(s => ({ label: s, value: s }))
    ];
  }

  get departmentOptions(): SelectOption[] {
    return [
      { label: 'All Departments', value: '' },
      ...this.departments.map(d => ({ label: d, value: d }))
    ];
  }

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
    private cdr: ChangeDetectorRef,
    private ngZone: NgZone
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

  onSubmitCreateTraining(): void {
    if (this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }

    this.isSubmittingTraining = true;
    this.cdr.detectChanges();

    const raw = this.createForm.value;
    const payload = {
      ...raw,
      start_date: raw.start_date ? raw.start_date : null,
      end_date: raw.end_date ? raw.end_date : null,
    };

    this.trainingService.createTraining(payload).subscribe({
      next: (res) => {
        this.isSubmittingTraining = false;
        this.closeCreateModal();
        this.showToast('Training program created successfully.', 'success');
        this.loadKPIs();
        this.loadTrainings();
      },
      error: (err) => {
        this.isSubmittingTraining = false;
        this.showToast('Error creating training program: ' + this.formatError(err), 'error');
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
        this.showToast('Assessment settings saved successfully.', 'success');
        this.loadAssessmentForTraining(this.activeAssessmentTraining!.id);
      },
      error: (err) => {
        this.isSavingAssessmentSettings = false;
        this.showToast('Error saving assessment: ' + (err.error?.detail || err.message), 'error');
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
      this.showToast('Please save assessment settings first before adding questions.', 'error');
      return;
    }

    if (this.questionForm.invalid) {
      this.questionForm.markAllAsTouched();
      this.showToast('Please fill in all question fields and options.', 'error');
      return;
    }

    this.isAddingQuestion = true;
    this.setCorrectOption(this.selectedCorrectOptionIndex);
    this.cdr.detectChanges();

    this.trainingService.addQuestion(this.assessmentData.id, this.questionForm.value).subscribe({
      next: () => {
        this.isAddingQuestion = false;
        this.resetQuestionForm();
        this.showToast('Question added to assessment successfully.', 'success');
        this.loadAssessmentForTraining(this.activeAssessmentTraining!.id);
      },
      error: (err) => {
        this.isAddingQuestion = false;
        this.showToast('Error adding question: ' + (err.error?.detail || err.message), 'error');
        this.cdr.detectChanges();
      }
    });
  }

  deleteQuestion(qId: number): void {
    const assessmentId = this.assessmentData?.id;
    const activeTrnId = this.activeAssessmentTraining?.id;
    if (!assessmentId || !activeTrnId) return;
    this.openConfirm({
      title: 'Delete Question',
      message: 'Are you sure you want to delete this question from the assessment?',
      confirmBtnText: 'Delete Question',
      confirmBtnClass: 'btn-danger',
      iconClass: 'fas fa-trash',
      onConfirm: () => {
        this.trainingService.deleteQuestion(assessmentId, qId).subscribe({
          next: () => {
            this.showToast('Question deleted successfully.', 'success');
            this.loadAssessmentForTraining(activeTrnId);
          },
          error: (err) => this.showToast('Delete failed: ' + (err.error?.detail || err.message), 'error')
        });
      }
    });
  }

  resetQuestionForm(): void {
    this.questionForm.reset({
      question_text: '',
      marks: 1,
      difficulty: 'Medium',
      explanation: ''
    });
    const opts = this.optionsArray;
    opts.clear();
    const defaults = ['A', 'B', 'C', 'D'];
    defaults.forEach((key, idx) => {
      opts.push(
        this.fb.group({
          option_key: [key],
          option_text: ['', Validators.required],
          is_correct: [idx === 1]
        })
      );
    });
    this.selectedCorrectOptionIndex = 1;
    this.cdr.detectChanges();
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

  getLearnerRoute(id: number): string[] {
    return [this.getBasePrefix(), 'trainings', id.toString(), 'view'];
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
    this.openConfirm({
      title: 'Archive Training Program',
      message: 'Are you sure you want to archive this training program? It will be deactivated and moved to archive.',
      confirmBtnText: 'Archive Program',
      confirmBtnClass: 'btn-danger',
      iconClass: 'fas fa-archive',
      onConfirm: () => {
        this.trainingService.archiveTraining(id).subscribe({
          next: () => {
            this.showToast('Training program archived successfully.', 'success');
            this.loadKPIs();
            this.loadTrainings();
          },
          error: (err) => this.showToast('Failed to archive training: ' + (err.error?.detail || err.message), 'error')
        });
      }
    });
  }

  restoreTraining(id: number): void {
    this.openConfirm({
      title: 'Restore Training Program',
      message: 'Restore this training program to Published status and make it active again?',
      confirmBtnText: 'Restore Program',
      confirmBtnClass: 'btn-success',
      iconClass: 'fas fa-trash-restore',
      onConfirm: () => {
        this.trainingService.restoreTraining(id).subscribe({
          next: () => {
            this.showToast('Training program restored to Published.', 'success');
            this.loadKPIs();
            this.loadTrainings();
          },
          error: (err) => this.showToast('Failed to restore training: ' + (err.error?.detail || err.message), 'error')
        });
      }
    });
  }

  publishTraining(id: number): void {
    this.openConfirm({
      title: 'Publish Training Program',
      message: 'Publish this training program to make it active and accessible to assigned employees?',
      confirmBtnText: 'Publish Program',
      confirmBtnClass: 'btn-success',
      iconClass: 'fas fa-globe',
      onConfirm: () => {
        this.trainingService.publishTraining(id).subscribe({
          next: () => {
            this.showToast('Training program published successfully.', 'success');
            this.loadKPIs();
            this.loadTrainings();
          },
          error: (err) => this.showToast('Failed to publish training: ' + (err.error?.detail || err.message), 'error')
        });
      }
    });
  }

  navigateTo(path: string): void {
    this.router.navigate([path]);
  }
}
