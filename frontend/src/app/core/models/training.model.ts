export interface TrainingMaterial {
  id: number;
  training_id: number;
  file_name: string;
  storage_path: string;
  file_type: 'document' | 'video' | 'audio' | 'image';
  mime_type: string;
  file_size: number;
  description?: string;
  display_order: number;
  is_required: boolean;
  uploaded_by_user_id: number;
  created_at: string;
  is_completed?: boolean;
  download_url?: string;
}

export interface Training {
  id: number;
  title: string;
  code: string;
  category: string;
  description?: string;
  learning_objective?: string;
  trainer_name?: string;
  trainer_user_id?: number;
  estimated_duration_minutes: number;
  start_date?: string;
  end_date?: string;
  status: 'Draft' | 'Published' | 'Archived';
  created_by_user_id: number;
  created_at: string;
  updated_at?: string;
  materials?: TrainingMaterial[];
  has_assessment?: boolean;
  assigned_count?: number;
  completed_count?: number;
  completion_percentage?: number;
}

export interface TrainingAssignment {
  id: number;
  training_id: number;
  employee_id: number;
  employee_name?: string;
  employee_code?: string;
  department?: string;
  assignment_type: 'All' | 'Selected' | 'Department' | 'Team' | 'Designation';
  assigned_at: string;
  due_date?: string;
  status: 'NOT_STARTED' | 'IN_PROGRESS' | 'COMPLETED';
  progress_percentage: number;
  started_at?: string;
  completed_at?: string;
  assessment_status?: string;
  assessment_score?: string;
}

export interface AssessmentOption {
  id?: number;
  question_id?: number;
  option_key: 'A' | 'B' | 'C' | 'D';
  option_text: string;
  is_correct?: boolean;
  display_order?: number;
}

export interface AssessmentQuestion {
  id?: number;
  assessment_id?: number;
  question_text: string;
  marks: number;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  display_order: number;
  explanation?: string;
  options: AssessmentOption[];
}

export interface Assessment {
  id?: number;
  training_id: number;
  title: string;
  description?: string;
  instructions?: string;
  duration_minutes: number;
  passing_percentage: number;
  max_attempts: number;
  randomize_questions: boolean;
  randomize_options: boolean;
  show_result: boolean;
  show_correct_answers: boolean;
  status: string;
  questions?: AssessmentQuestion[];
}

export interface AssessmentAttemptStartResponse {
  attempt_id: number;
  assessment_id: number;
  assessment_title: string;
  instructions?: string;
  duration_minutes: number;
  started_at: string;
  time_remaining_seconds: number;
  total_questions: number;
  questions: AssessmentQuestion[];
  saved_answers: { [questionId: number]: number };
}

export interface AssessmentResult {
  attempt_id: number;
  assessment_id?: number;
  assessment_title?: string;
  employee_id?: number;
  status: string;
  started_at?: string;
  submitted_at?: string;
  score: number;
  total_marks: number;
  percentage: number;
  passed: boolean;
  total_questions?: number;
  correct_answers_count?: number;
  incorrect_answers_count?: number;
  unanswered_count?: number;
  show_correct_answers: boolean;
  review?: Array<{
    question_id: number;
    question_text: string;
    your_option: string;
    correct_option: string;
    is_correct: boolean;
    explanation?: string;
  }>;
}

export interface EmployeeTrainingView {
  assignment_id: number;
  training_id: number;
  title: string;
  code: string;
  category: string;
  description?: string;
  learning_objective?: string;
  trainer_name?: string;
  estimated_duration_minutes: number;
  start_date?: string;
  due_date?: string;
  assignment_status: string;
  progress_percentage: number;
  materials: TrainingMaterial[];
  has_assessment: boolean;
  assessment?: {
    id: number;
    title: string;
    description?: string;
    instructions?: string;
    duration_minutes: number;
    passing_percentage: number;
    max_attempts: number;
    show_result: boolean;
  };
  user_attempts_count: number;
  can_take_assessment: boolean;
  last_attempt_result?: {
    attempt_id: number;
    score: number;
    total_marks: number;
    percentage: number;
    passed: boolean;
    submitted_at: string;
  };
}

export interface TrainingKPI {
  total_trainings: number;
  active_trainings: number;
  assigned_employees: number;
  completed_trainings: number;
  pending_trainings: number;
  avg_assessment_score: number;
  completion_breakdown: { [key: string]: number };
  assessment_performance: { [key: string]: number };
  department_completion: Array<{
    department: string;
    completion_percentage: number;
    assigned_count: number;
    completed_count: number;
  }>;
}

export interface TrainingReportRow {
  assignment_id: number;
  employee_id: number;
  employee_name: string;
  employee_code: string;
  department: string;
  training_title: string;
  category: string;
  assigned_date: string;
  started_date?: string;
  completed_date?: string;
  due_date?: string;
  progress_percentage: number;
  assignment_status: string;
  assessment_title: string;
  score: string;
  percentage: string;
  result: string;
}
