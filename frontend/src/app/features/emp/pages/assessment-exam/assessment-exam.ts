import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { TrainingService } from '../../../../core/services/training.service';
import { AssessmentAttemptStartResponse, AssessmentQuestion } from '../../../../core/models/training.model';

@Component({
  selector: 'app-assessment-exam',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './assessment-exam.html',
  styleUrls: ['./assessment-exam.css']
})
export class AssessmentExamComponent implements OnInit, OnDestroy {
  assessmentId!: number;
  examData: AssessmentAttemptStartResponse | null = null;
  currentQuestionIndex = 0;
  selectedAnswers: { [qId: number]: number } = {}; // { question_id: selected_option_id }

  timerSeconds = 0;
  timerInterval: any = null;
  isLoading = true;
  isSubmitting = false;

  showConfirmModal = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private trainingService: TrainingService
  ) {}

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      this.assessmentId = +idParam;
      this.startExam();
    }
  }

  ngOnDestroy(): void {
    this.stopTimer();
  }

  startExam(): void {
    this.isLoading = true;
    this.trainingService.startAssessment(this.assessmentId).subscribe({
      next: (res) => {
        this.examData = res;
        this.selectedAnswers = { ...res.saved_answers };
        this.timerSeconds = res.time_remaining_seconds;
        this.startTimer();
        this.isLoading = false;
      },
      error: (err) => {
        alert('Could not start assessment: ' + (err.error?.detail || err.message));
        this.router.navigate(['/emp-dashboard/my-trainings']);
      }
    });
  }

  startTimer(): void {
    this.stopTimer();
    this.timerInterval = setInterval(() => {
      if (this.timerSeconds > 0) {
        this.timerSeconds--;
      } else {
        this.stopTimer();
        alert('Time expired! Your assessment is automatically submitting.');
        this.confirmSubmit();
      }
    }, 1000);
  }

  stopTimer(): void {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  get formattedTime(): string {
    const mins = Math.floor(this.timerSeconds / 60);
    const secs = this.timerSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  get currentQuestion(): AssessmentQuestion | null {
    if (!this.examData || !this.examData.questions) return null;
    return this.examData.questions[this.currentQuestionIndex] || null;
  }

  selectOption(qId?: number, optId?: number): void {
    if (!qId || !optId) return;
    this.selectedAnswers[qId] = optId;
    if (this.examData?.attempt_id) {
      this.trainingService.saveAnswer(this.examData.attempt_id, qId, optId).subscribe({
        error: (err) => console.error('Error saving answer draft:', err)
      });
    }
  }

  isOptionSelected(qId?: number, optId?: number): boolean {
    if (!qId || !optId) return false;
    return this.selectedAnswers[qId] === optId;
  }

  isQuestionAnswered(qId?: number): boolean {
    if (!qId) return false;
    return !!this.selectedAnswers[qId];
  }

  goToQuestion(idx: number): void {
    if (this.examData && idx >= 0 && idx < this.examData.questions.length) {
      this.currentQuestionIndex = idx;
    }
  }

  nextQuestion(): void {
    if (this.examData && this.currentQuestionIndex < this.examData.questions.length - 1) {
      this.currentQuestionIndex++;
    }
  }

  prevQuestion(): void {
    if (this.currentQuestionIndex > 0) {
      this.currentQuestionIndex--;
    }
  }

  get answeredCount(): number {
    return Object.keys(this.selectedAnswers).length;
  }

  get unansweredCount(): number {
    if (!this.examData) return 0;
    return this.examData.total_questions - this.answeredCount;
  }

  openSubmitModal(): void {
    this.showConfirmModal = true;
  }

  closeSubmitModal(): void {
    this.showConfirmModal = false;
  }

  confirmSubmit(): void {
    if (!this.examData?.attempt_id || this.isSubmitting) return;
    this.isSubmitting = true;
    this.stopTimer();

    this.trainingService.submitAssessment(this.examData.attempt_id).subscribe({
      next: (res) => {
        this.isSubmitting = false;
        this.showConfirmModal = false;
        this.router.navigate(['/emp-dashboard/assessment-result', res.attempt_id]);
      },
      error: (err) => {
        this.isSubmitting = false;
        alert('Submission failed: ' + (err.error?.detail || err.message));
      }
    });
  }
}
