import { Component, OnInit, ChangeDetectorRef, NgZone } from '@angular/core';
import { CommonModule, Location } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { ActivatedRoute, RouterModule, Router } from '@angular/router';
import { TrainingService } from '../../../../../core/services/training.service';
import { Assessment, AssessmentQuestion } from '../../../../../core/models/training.model';
import { ToastService } from '../../../../../core/services/toast.service';

import { CustomSelectComponent } from '../../../../../shared/components/custom-select/custom-select';

@Component({
  selector: 'app-assessment-builder',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, RouterModule, CustomSelectComponent],
  templateUrl: './assessment-builder.html',
  styleUrls: ['./assessment-builder.css']
})
export class AssessmentBuilderComponent implements OnInit {
  trainingId!: number;
  assessment: Assessment | null = null;
  isLoading = true;
  isSavingAssessment = false;
  isAddingQuestion = false;

  readonly difficultySelectOptions = [
    { label: 'Easy', value: 'Easy' },
    { label: 'Medium', value: 'Medium' },
    { label: 'Hard', value: 'Hard' }
  ];

  settingsForm!: FormGroup;
  questionForm!: FormGroup;
  selectedCorrectOptionIndex = 1; // 0=A, 1=B, 2=C, 3=D

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
    this.toastService.show(type, message, { duration });
  }

  closeToast(): void {}

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

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private trainingService: TrainingService,
    private cdr: ChangeDetectorRef,
    private ngZone: NgZone,
    private location: Location,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      this.trainingId = +idParam;
      this.initForms();
      this.loadAssessment();
    }
  }

  getBasePrefix(): string {
    return this.router.url.includes('/master-dashboard') ? '/master-dashboard' : '/hr-dashboard';
  }

  getManageRoute(): string[] {
    return [this.getBasePrefix(), 'trainings', this.trainingId.toString(), 'manage'];
  }

  getTrainingsListRoute(): string {
    return `${this.getBasePrefix()}/trainings`;
  }

  goBack(): void {
    this.location.back();
  }

  private initForms(): void {
    this.settingsForm = this.fb.group({
      title: ['Assessment Test', [Validators.required, Validators.maxLength(200)]],
      description: [''],
      instructions: ['Please answer all questions carefully before the countdown timer expires.'],
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

  loadAssessment(): void {
    this.isLoading = true;
    this.cdr.detectChanges();
    this.trainingService.getAssessment(this.trainingId).subscribe({
      next: (data) => {
        this.assessment = data;
        this.settingsForm.patchValue({
          title: data.title,
          description: data.description,
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
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        // Assessment not created yet -> set defaults from training title
        this.trainingService.getTrainingById(this.trainingId).subscribe((t) => {
          this.settingsForm.patchValue({ title: `${t.title} Assessment Test` });
          this.isLoading = false;
          this.cdr.detectChanges();
        });
      }
    });
  }

  saveAssessmentSettings(): void {
    if (this.settingsForm.invalid) return;
    this.isSavingAssessment = true;
    this.trainingService.saveAssessment(this.trainingId, this.settingsForm.value).subscribe({
      next: (res) => {
        this.isSavingAssessment = false;
        this.showToast('Assessment settings saved successfully.', 'success');
        this.loadAssessment();
      },
      error: (err) => {
        this.isSavingAssessment = false;
        this.showToast('Error saving assessment: ' + (err.error?.detail || err.message), 'error');
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
    if (!this.assessment || !this.assessment.id) {
      this.showToast('Please save the assessment settings first before adding questions.', 'error');
      return;
    }

    if (this.questionForm.invalid) {
      this.questionForm.markAllAsTouched();
      this.showToast('Please fill out all question fields and options.', 'error');
      return;
    }

    this.isAddingQuestion = true;
    this.setCorrectOption(this.selectedCorrectOptionIndex);

    this.trainingService.addQuestion(this.assessment.id, this.questionForm.value).subscribe({
      next: () => {
        this.isAddingQuestion = false;
        this.resetQuestionForm();
        this.showToast('Question added successfully.', 'success');
        this.loadAssessment();
      },
      error: (err) => {
        this.isAddingQuestion = false;
        this.showToast('Error adding question: ' + (err.error?.detail || err.message), 'error');
      }
    });
  }

  deleteQuestion(qId: number): void {
    const assessmentId = this.assessment?.id;
    if (!assessmentId) return;
    this.openConfirm({
      title: 'Delete Question',
      message: 'Are you sure you want to delete this MCQ question from the assessment?',
      confirmBtnText: 'Delete Question',
      confirmBtnClass: 'btn-danger',
      iconClass: 'fas fa-trash',
      onConfirm: () => {
        this.trainingService.deleteQuestion(assessmentId, qId).subscribe({
          next: () => {
            this.showToast('Question deleted successfully.', 'success');
            this.loadAssessment();
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
  }
}
