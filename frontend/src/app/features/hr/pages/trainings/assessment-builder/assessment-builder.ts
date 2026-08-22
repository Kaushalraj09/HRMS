import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { ActivatedRoute, RouterModule, Router } from '@angular/router';
import { TrainingService } from '../../../../../core/services/training.service';
import { Assessment, AssessmentQuestion } from '../../../../../core/models/training.model';

@Component({
  selector: 'app-assessment-builder',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, RouterModule],
  templateUrl: './assessment-builder.html',
  styleUrls: ['./assessment-builder.css']
})
export class AssessmentBuilderComponent implements OnInit {
  trainingId!: number;
  assessment: Assessment | null = null;
  isLoading = true;
  isSavingAssessment = false;
  isAddingQuestion = false;

  settingsForm!: FormGroup;
  questionForm!: FormGroup;
  selectedCorrectOptionIndex = 1; // 0=A, 1=B, 2=C, 3=D

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private fb: FormBuilder,
    private trainingService: TrainingService
  ) {}

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      this.trainingId = +idParam;
      this.initForms();
      this.loadAssessment();
    }
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
      },
      error: () => {
        // Assessment not created yet -> set defaults from training title
        this.trainingService.getTrainingById(this.trainingId).subscribe((t) => {
          this.settingsForm.patchValue({ title: `${t.title} Assessment Test` });
          this.isLoading = false;
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
        alert('Assessment settings saved successfully.');
        this.loadAssessment();
      },
      error: (err) => {
        this.isSavingAssessment = false;
        alert('Error saving assessment: ' + (err.error?.detail || err.message));
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
      alert('Please save the assessment settings first before adding questions.');
      return;
    }

    if (this.questionForm.invalid) {
      this.questionForm.markAllAsTouched();
      alert('Please fill out all question fields and options.');
      return;
    }

    this.isAddingQuestion = true;
    this.setCorrectOption(this.selectedCorrectOptionIndex);

    this.trainingService.addQuestion(this.assessment.id, this.questionForm.value).subscribe({
      next: () => {
        this.isAddingQuestion = false;
        this.resetQuestionForm();
        this.loadAssessment();
      },
      error: (err) => {
        this.isAddingQuestion = false;
        alert('Error adding question: ' + (err.error?.detail || err.message));
      }
    });
  }

  deleteQuestion(qId: number): void {
    if (!this.assessment?.id) return;
    if (confirm('Delete this question?')) {
      this.trainingService.deleteQuestion(this.assessment.id, qId).subscribe({
        next: () => this.loadAssessment(),
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
}
