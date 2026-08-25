import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  Training,
  TrainingMaterial,
  TrainingAssignment,
  Assessment,
  AssessmentQuestion,
  AssessmentAttemptStartResponse,
  AssessmentResult,
  EmployeeTrainingView,
  TrainingKPI,
  TrainingReportRow
} from '../models/training.model';

@Injectable({
  providedIn: 'root'
})
export class TrainingService {
  private apiUrl = `${environment.apiBaseUrl}/trainings`;

  constructor(private http: HttpClient) {}

  // ─── HR Training CRUD & Analytics ───────────────────────────────────────

  getKPIs(): Observable<TrainingKPI> {
    return this.http.get<TrainingKPI>(`${this.apiUrl}/kpi-dashboard`);
  }

  getTrainings(params?: {
    search?: string;
    category?: string;
    status?: string;
    department?: string;
    page?: number;
    limit?: number;
  }): Observable<{ items: Training[]; total: number; page: number; limit: number }> {
    let httpParams = new HttpParams();
    if (params) {
      if (params.search) httpParams = httpParams.set('search', params.search);
      if (params.category) httpParams = httpParams.set('category', params.category);
      if (params.status) httpParams = httpParams.set('status', params.status);
      if (params.department) httpParams = httpParams.set('department', params.department);
      if (params.page) httpParams = httpParams.set('page', params.page.toString());
      if (params.limit) httpParams = httpParams.set('limit', params.limit.toString());
    }
    return this.http.get<{ items: Training[]; total: number; page: number; limit: number }>(
      this.apiUrl,
      { params: httpParams }
    );
  }

  getTrainingById(id: number): Observable<Training> {
    return this.http.get<Training>(`${this.apiUrl}/${id}`);
  }

  createTraining(trainingData: Partial<Training>): Observable<Training> {
    return this.http.post<Training>(this.apiUrl, trainingData);
  }

  updateTraining(id: number, trainingData: Partial<Training>): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/${id}`, trainingData);
  }

  archiveTraining(id: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/${id}`);
  }

  // ─── Material Management ──────────────────────────────────────────────────

  uploadMaterial(
    trainingId: number,
    file: File,
    description?: string,
    isRequired: boolean = true
  ): Observable<TrainingMaterial> {
    const formData = new FormData();
    formData.append('file', file);
    if (description) formData.append('description', description);
    formData.append('is_required', isRequired ? 'true' : 'false');

    return this.http.post<TrainingMaterial>(`${this.apiUrl}/${trainingId}/materials`, formData);
  }

  deleteMaterial(trainingId: number, materialId: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/${trainingId}/materials/${materialId}`);
  }

  reorderMaterials(trainingId: number, items: Array<{ material_id: number; display_order: number }>): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/${trainingId}/materials/reorder`, { items });
  }

  getDownloadUrl(trainingId: number, materialId: number): string {
    return `${this.apiUrl}/${trainingId}/materials/${materialId}/download`;
  }

  // ─── Assignments Management ──────────────────────────────────────────────

  assignTraining(
    trainingId: number,
    data: {
      assignment_type: 'All' | 'Selected' | 'Department' | 'Team' | 'Designation';
      employee_ids?: number[];
      departments?: string[];
      designations?: string[];
      due_date?: string;
    }
  ): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/${trainingId}/assign`, data);
  }

  getAssignments(trainingId: number): Observable<TrainingAssignment[]> {
    return this.http.get<TrainingAssignment[]>(`${this.apiUrl}/${trainingId}/assignments`);
  }

  // ─── Assessment Builder (HR) ──────────────────────────────────────────────

  saveAssessment(trainingId: number, assessmentData: Partial<Assessment>): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/${trainingId}/assessment`, assessmentData);
  }

  getAssessment(trainingId: number): Observable<Assessment> {
    return this.http.get<Assessment>(`${this.apiUrl}/${trainingId}/assessment`);
  }

  addQuestion(assessmentId: number, questionData: Partial<AssessmentQuestion>): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/assessments/${assessmentId}/questions`, questionData);
  }

  deleteQuestion(assessmentId: number, questionId: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/assessments/${assessmentId}/questions/${questionId}`);
  }

  // ─── Reports ─────────────────────────────────────────────────────────────

  getReports(params?: {
    training_id?: number;
    department?: string;
    employee_id?: number;
    status_filter?: string;
  }): Observable<TrainingReportRow[]> {
    let httpParams = new HttpParams();
    if (params) {
      if (params.training_id) httpParams = httpParams.set('training_id', params.training_id.toString());
      if (params.department) httpParams = httpParams.set('department', params.department);
      if (params.employee_id) httpParams = httpParams.set('employee_id', params.employee_id.toString());
      if (params.status_filter) httpParams = httpParams.set('status_filter', params.status_filter);
    }
    return this.http.get<TrainingReportRow[]>(`${this.apiUrl}/reports/completion`, { params: httpParams });
  }

  // ─── Employee Endpoints ───────────────────────────────────────────────────

  getMyTrainings(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/my/all`);
  }

  getMyTrainingDetail(trainingId: number): Observable<EmployeeTrainingView> {
    return this.http.get<EmployeeTrainingView>(`${this.apiUrl}/my/${trainingId}`);
  }

  recordMaterialProgress(
    trainingId: number,
    materialId: number,
    progressPct: number = 100,
    isCompleted: boolean = true
  ): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/my/${trainingId}/materials/${materialId}/progress`, {
      progress_percentage: progressPct,
      is_completed: isCompleted
    });
  }

  // ─── Assessment Exam Attempt & Evaluation ─────────────────────────────────

  startAssessment(assessmentId: number): Observable<AssessmentAttemptStartResponse> {
    return this.http.post<AssessmentAttemptStartResponse>(`${this.apiUrl}/assessments/${assessmentId}/attempts/start`, {});
  }

  saveAnswer(attemptId: number, questionId: number, selectedOptionId: number): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/attempts/${attemptId}/save-answer`, {
      question_id: questionId,
      selected_option_id: selectedOptionId
    });
  }

  submitAssessment(attemptId: number): Observable<AssessmentResult> {
    return this.http.post<AssessmentResult>(`${this.apiUrl}/attempts/${attemptId}/submit`, {});
  }

  getAttemptResult(attemptId: number): Observable<AssessmentResult> {
    return this.http.get<AssessmentResult>(`${this.apiUrl}/attempts/${attemptId}/result`);
  }
}
