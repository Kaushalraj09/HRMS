import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterModule, Router } from '@angular/router';
import { TrainingService } from '../../../../../core/services/training.service';
import { Training, TrainingMaterial, TrainingAssignment } from '../../../../../core/models/training.model';
import { MasterDataService } from '../../../../../core/services/master-data.service';
import { EmployeeService } from '../../../../../core/services/employee.service';

@Component({
  selector: 'app-training-manage',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './training-manage.html',
  styleUrls: ['./training-manage.css']
})
export class TrainingManageComponent implements OnInit {
  trainingId!: number;
  training: Training | null = null;
  activeTab: 'content' | 'assignments' = 'content';
  isLoading = true;

  // Material upload state
  selectedFile: File | null = null;
  materialDescription = '';
  isRequiredMaterial = true;
  isUploading = false;

  // Assignments state
  assignmentType: 'All' | 'Selected' | 'Department' | 'Designation' = 'All';
  dueDate = '';
  assignments: TrainingAssignment[] = [];
  isAssigning = false;

  // Employee & Master data selection lists
  allEmployees: any[] = [];
  selectedEmployeeIds: number[] = [];
  employeeSearchTerm = '';

  departments: any[] = [];
  selectedDepartmentNames: string[] = [];

  designations: any[] = [];
  selectedDesignationNames: string[] = [];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private trainingService: TrainingService,
    private masterDataService: MasterDataService,
    private employeeService: EmployeeService
  ) {}

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      this.trainingId = +idParam;
      this.loadTraining();
      this.loadAssignments();
      this.loadMasterData();
    }
  }

  loadTraining(): void {
    this.isLoading = true;
    this.trainingService.getTrainingById(this.trainingId).subscribe({
      next: (data) => {
        this.training = data;
        this.isLoading = false;
      },
      error: (err) => {
        alert('Failed to load training details: ' + (err.error?.detail || err.message));
        this.isLoading = false;
      }
    });
  }

  loadAssignments(): void {
    this.trainingService.getAssignments(this.trainingId).subscribe({
      next: (data) => (this.assignments = data),
      error: (err) => console.error('Error loading assignments:', err)
    });
  }

  loadMasterData(): void {
    this.masterDataService.getDepartments().subscribe((res: any) => (this.departments = res || []));
    this.masterDataService.getDesignations().subscribe((res: any) => (this.designations = res || []));
    this.employeeService.getEmployees(1, 100, '', '', '', '').subscribe((res: any) => (this.allEmployees = res.items || res || []));
  }

  // ─── Material Methods ───────────────────────────────────────────────────

  onFileSelected(event: any): void {
    const files = event.target.files;
    if (files && files.length > 0) {
      this.selectedFile = files[0];
    }
  }

  uploadMaterial(): void {
    if (!this.selectedFile) {
      alert('Please select a file to upload.');
      return;
    }

    this.isUploading = true;
    this.trainingService
      .uploadMaterial(this.trainingId, this.selectedFile, this.materialDescription, this.isRequiredMaterial)
      .subscribe({
        next: () => {
          this.selectedFile = null;
          this.materialDescription = '';
          this.isUploading = false;
          this.loadTraining();
        },
        error: (err) => {
          this.isUploading = false;
          alert('Upload failed: ' + (err.error?.detail || err.message));
        }
      });
  }

  deleteMaterial(matId: number): void {
    if (confirm('Delete this material?')) {
      this.trainingService.deleteMaterial(this.trainingId, matId).subscribe({
        next: () => this.loadTraining(),
        error: (err) => alert('Delete failed: ' + (err.error?.detail || err.message))
      });
    }
  }

  getDownloadUrl(matId: number): string {
    return this.trainingService.getDownloadUrl(this.trainingId, matId);
  }

  // ─── Assignment Methods ─────────────────────────────────────────────────

  toggleEmployeeSelection(empId: number): void {
    const idx = this.selectedEmployeeIds.indexOf(empId);
    if (idx > -1) {
      this.selectedEmployeeIds.splice(idx, 1);
    } else {
      this.selectedEmployeeIds.push(empId);
    }
  }

  isEmployeeSelected(empId: number): boolean {
    return this.selectedEmployeeIds.includes(empId);
  }

  toggleDeptSelection(deptName: string): void {
    const idx = this.selectedDepartmentNames.indexOf(deptName);
    if (idx > -1) {
      this.selectedDepartmentNames.splice(idx, 1);
    } else {
      this.selectedDepartmentNames.push(deptName);
    }
  }

  isDeptSelected(deptName: string): boolean {
    return this.selectedDepartmentNames.includes(deptName);
  }

  get filteredEmployees(): any[] {
    if (!this.employeeSearchTerm) return this.allEmployees;
    const s = this.employeeSearchTerm.toLowerCase();
    return this.allEmployees.filter(
      (e) =>
        (e.first_name + ' ' + e.last_name).toLowerCase().includes(s) ||
        (e.employee_code || '').toLowerCase().includes(s) ||
        (e.department || '').toLowerCase().includes(s)
    );
  }

  submitAssignment(): void {
    this.isAssigning = true;
    const payload: any = {
      assignment_type: this.assignmentType,
      due_date: this.dueDate || undefined
    };

    if (this.assignmentType === 'Selected') {
      payload.employee_ids = this.selectedEmployeeIds;
    } else if (this.assignmentType === 'Department') {
      payload.departments = this.selectedDepartmentNames;
    }

    this.trainingService.assignTraining(this.trainingId, payload).subscribe({
      next: (res) => {
        this.isAssigning = false;
        alert(`Successfully assigned training to ${res.assigned_count} employees.`);
        this.loadAssignments();
        this.loadTraining();
      },
      error: (err) => {
        this.isAssigning = false;
        alert('Assignment failed: ' + (err.error?.detail || err.message));
      }
    });
  }
}
