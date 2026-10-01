import { Component, OnInit, ChangeDetectorRef, NgZone } from '@angular/core';
import { CommonModule, Location } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterModule, Router } from '@angular/router';
import { TrainingService } from '../../../../../core/services/training.service';
import { Training, TrainingMaterial, TrainingAssignment } from '../../../../../core/models/training.model';
import { MasterDataService } from '../../../../../core/services/master-data.service';
import { EmployeeService } from '../../../../../core/services/employee.service';
import { Employee } from '../../../../../core/models/employee.model';
import { ToastService } from '../../../../../core/services/toast.service';

import { CustomDatepickerComponent } from '../../../../../shared/components/custom-datepicker/custom-datepicker';
import { CustomSelectComponent } from '../../../../../shared/components/custom-select/custom-select';

@Component({
  selector: 'app-training-manage',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, CustomDatepickerComponent, CustomSelectComponent],
  templateUrl: './training-manage.html',
  styleUrls: ['./training-manage.css']
})
export class TrainingManageComponent implements OnInit {
  trainingId!: number;
  training: Training | null = null;
  activeTab: 'content' | 'assignments' = 'content';
  isLoading = true;

  readonly assignmentTypeSelectOptions = [
    { label: 'All Active Employees', value: 'All' },
    { label: 'Selected Employees', value: 'Selected' },
    { label: 'By Department', value: 'Department' }
  ];

  // Material upload state
  selectedFiles: File[] = [];
  materialDescription = '';
  isRequiredMaterial = true;
  isUploading = false;
  isDragging = false;

  // Assignments state
  assignmentType: 'All' | 'Selected' | 'Department' | 'Designation' = 'All';
  dueDate = '';
  assignments: TrainingAssignment[] = [];
  isAssigning = false;

  // Employee & Master data selection lists
  allEmployees: Employee[] = [];
  selectedEmployeeIds: number[] = [];
  employeeSearchTerm = '';

  departments: any[] = [];
  selectedDepartmentNames: string[] = [];

  designations: any[] = [];
  selectedDesignationNames: string[] = [];

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

  // Deprecated local toast state kept for backwards compatibility
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
    private route: ActivatedRoute,
    private router: Router,
    private trainingService: TrainingService,
    private masterDataService: MasterDataService,
    private employeeService: EmployeeService,
    private cdr: ChangeDetectorRef,
    private ngZone: NgZone,
    private location: Location,
    private toastService: ToastService
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

  getBasePrefix(): string {
    return this.router.url.includes('/master-dashboard') ? '/master-dashboard' : (this.router.url.includes('/emp-dashboard') ? '/emp-dashboard' : '/hr-dashboard');
  }

  getAssessmentRoute(): string[] {
    return [this.getBasePrefix(), 'trainings', this.trainingId.toString(), 'assessment'];
  }

  getLearnerRoute(): string[] {
    return [this.getBasePrefix(), 'trainings', this.trainingId.toString(), 'view'];
  }

  getTrainingsListRoute(): string {
    return `${this.getBasePrefix()}/trainings`;
  }

  restoreTraining(): void {
    this.openConfirm({
      title: 'Restore Training Program',
      message: 'Restore this training program to Published status and make it active again?',
      confirmBtnText: 'Restore Program',
      confirmBtnClass: 'btn-success',
      iconClass: 'fas fa-trash-restore',
      onConfirm: () => {
        this.trainingService.restoreTraining(this.trainingId).subscribe({
          next: () => {
            this.showToast('Training program restored to Published.', 'success');
            this.loadTraining();
          },
          error: (err) => this.showToast('Failed to restore training: ' + (err.error?.detail || err.message), 'error')
        });
      }
    });
  }

  publishTraining(): void {
    this.openConfirm({
      title: 'Publish Training Program',
      message: 'Publish this training program to make it active for all assigned employees?',
      confirmBtnText: 'Publish Program',
      confirmBtnClass: 'btn-success',
      iconClass: 'fas fa-globe',
      onConfirm: () => {
        this.trainingService.publishTraining(this.trainingId).subscribe({
          next: () => {
            this.showToast('Training program published successfully.', 'success');
            this.loadTraining();
          },
          error: (err) => this.showToast('Failed to publish training: ' + (err.error?.detail || err.message), 'error')
        });
      }
    });
  }

  archiveTraining(): void {
    this.openConfirm({
      title: 'Archive Training Program',
      message: 'Are you sure you want to archive this training program? It will be deactivated and moved to archive.',
      confirmBtnText: 'Archive Program',
      confirmBtnClass: 'btn-danger',
      iconClass: 'fas fa-archive',
      onConfirm: () => {
        this.trainingService.archiveTraining(this.trainingId).subscribe({
          next: () => {
            this.showToast('Training program archived successfully.', 'success');
            this.loadTraining();
          },
          error: (err) => this.showToast('Failed to archive training: ' + (err.error?.detail || err.message), 'error')
        });
      }
    });
  }

  goBack(): void {
    this.location.back();
  }

  loadTraining(): void {
    this.isLoading = true;
    this.cdr.detectChanges();
    this.trainingService.getTrainingById(this.trainingId).subscribe({
      next: (data) => {
        this.training = data;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.showToast('Failed to load training details: ' + (err.error?.detail || err.message), 'error');
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  loadAssignments(): void {
    this.trainingService.getAssignments(this.trainingId).subscribe({
      next: (data) => {
        this.ngZone.run(() => {
          this.assignments = data || [];
          this.cdr.detectChanges();
        });
      },
      error: (err) => {
        this.ngZone.run(() => {
          console.error('Error loading assignments:', err);
          this.cdr.detectChanges();
        });
      }
    });
  }

  loadMasterData(): void {
    this.masterDataService.getDepartments().subscribe({
      next: (res) => {
        this.departments = res || [];
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error loading departments:', err)
    });

    this.masterDataService.getDesignations().subscribe({
      next: (res) => {
        this.designations = res || [];
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error loading designations:', err)
    });

    this.employeeService.getEmployees(1, 1000, '', '', '', '').subscribe({
      next: (res: any) => {
        this.allEmployees = res.data || res.items || res || [];
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error loading employees:', err)
    });
  }

  // ─── Material Upload Methods ────────────────────────────────────────────

  onFilesSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      this.addFiles(Array.from(input.files));
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;
    if (event.dataTransfer?.files) {
      this.addFiles(Array.from(event.dataTransfer.files));
    }
  }

  onFileDrop(event: DragEvent): void {
    this.onDrop(event);
  }

  readonly ALLOWED_EXTENSIONS = [
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt',
    'mp4', 'webm', 'mov',
    'mp3', 'wav', 'm4a', 'ogg',
    'jpg', 'jpeg', 'png', 'webp', 'svg'
  ];

  private addFiles(files: File[]): void {
    for (const f of files) {
      const ext = f.name?.split('.').pop()?.toLowerCase() || '';
      if (!this.ALLOWED_EXTENSIONS.includes(ext)) {
        this.showToast(`"${f.name}" format (.${ext}) is not supported. Supported: PDF, Office, Videos, Audio, Images.`, 'error');
        continue;
      }
      if (f.size > 100 * 1024 * 1024) {
        this.showToast(`"${f.name}" (${(f.size / (1024 * 1024)).toFixed(1)} MB) exceeds maximum 100 MB limit.`, 'error');
        continue;
      }
      if (!this.selectedFiles.some(existing => existing.name === f.name && existing.size === f.size)) {
        this.selectedFiles.push(f);
      }
    }
  }

  removeSelectedFile(index: number): void {
    this.selectedFiles.splice(index, 1);
  }

  clearSelectedFiles(): void {
    this.selectedFiles = [];
  }

  formatFileSize(bytes: number): string {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  getTotalSelectedSize(): string {
    const totalBytes = this.selectedFiles.reduce((acc, file) => acc + file.size, 0);
    return (totalBytes / (1024 * 1024)).toFixed(2) + ' MB';
  }

  getFileMeta(fileName: string): { icon: string; bgClass: string; textClass: string } {
    const ext = fileName?.split('.').pop()?.toLowerCase() || '';
    if (['mp4', 'webm', 'ogg', 'mov', 'mkv', 'avi'].includes(ext)) {
      return { icon: 'fas fa-video', bgClass: 'bg-primary-subtle', textClass: 'text-primary' };
    }
    if (['mp3', 'wav', 'aac', 'flac', 'm4a'].includes(ext)) {
      return { icon: 'fas fa-volume-up', bgClass: 'bg-warning-subtle', textClass: 'text-warning' };
    }
    if (ext === 'pdf') {
      return { icon: 'fas fa-file-pdf', bgClass: 'bg-danger-subtle', textClass: 'text-danger' };
    }
    if (['doc', 'docx'].includes(ext)) {
      return { icon: 'fas fa-file-word', bgClass: 'bg-primary-subtle', textClass: 'text-primary' };
    }
    if (['xls', 'xlsx', 'csv'].includes(ext)) {
      return { icon: 'fas fa-file-excel', bgClass: 'bg-success-subtle', textClass: 'text-success' };
    }
    if (['ppt', 'pptx'].includes(ext)) {
      return { icon: 'fas fa-file-powerpoint', bgClass: 'bg-warning-subtle', textClass: 'text-warning' };
    }
    if (['jpg', 'jpeg', 'png', 'webp', 'gif', 'svg', 'bmp'].includes(ext)) {
      return { icon: 'fas fa-image', bgClass: 'bg-info-subtle', textClass: 'text-info' };
    }
    return { icon: 'fas fa-file-alt', bgClass: 'bg-secondary-subtle', textClass: 'text-secondary' };
  }

  getFileIconInfo(fileName: string): { icon: string; bgClass: string; textClass: string } {
    return this.getFileMeta(fileName);
  }

  uploadMaterials(): void {
    if (this.selectedFiles.length === 0) {
      this.showToast('Please select at least one file to upload.', 'error');
      return;
    }

    this.isUploading = true;
    this.cdr.detectChanges();

    this.trainingService
      .uploadMaterialsBulk(
        this.trainingId,
        this.selectedFiles,
        this.materialDescription,
        this.isRequiredMaterial
      )
      .subscribe({
        next: (res) => {
          this.selectedFiles = [];
          this.materialDescription = '';
          this.isUploading = false;
          this.showToast('Materials uploaded successfully.', 'success');
          this.loadTraining();
        },
        error: (err) => {
          this.isUploading = false;
          let detail = err.error?.detail;
          if (err.status === 413) {
            detail = 'File size exceeds server upload limit (maximum 100 MB per file).';
          } else if (!detail) {
            detail = err.status === 0 ? 'Network or connection timeout.' : (err.message || 'Upload failed.');
          }
          this.showToast('Upload failed: ' + detail, 'error');
          this.cdr.detectChanges();
        }
      });
  }

  deleteMaterial(matId: number): void {
    this.openConfirm({
      title: 'Delete Learning Material',
      message: 'Are you sure you want to delete this material file? Employees will no longer have access to it.',
      confirmBtnText: 'Delete Material',
      confirmBtnClass: 'btn-danger',
      iconClass: 'fas fa-trash',
      onConfirm: () => {
        this.trainingService.deleteMaterial(this.trainingId, matId).subscribe({
          next: () => {
            this.showToast('Material deleted successfully.', 'success');
            this.loadTraining();
          },
          error: (err) => this.showToast('Delete failed: ' + (err.error?.detail || err.message), 'error')
        });
      }
    });
  }

  getDownloadUrl(matId: number): string {
    return this.trainingService.getDownloadUrl(this.trainingId, matId);
  }

  // ─── Assignment Methods ─────────────────────────────────────────────────

  toggleEmployeeSelection(empId: number | string): void {
    const numericId = Number(empId);
    if (!numericId) return;
    const idx = this.selectedEmployeeIds.indexOf(numericId);
    if (idx > -1) {
      this.selectedEmployeeIds.splice(idx, 1);
    } else {
      this.selectedEmployeeIds.push(numericId);
    }
  }

  isEmployeeSelected(empId: number | string): boolean {
    const numericId = Number(empId);
    return this.selectedEmployeeIds.includes(numericId);
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

  get filteredEmployees(): Employee[] {
    if (!this.employeeSearchTerm) return this.allEmployees;
    const s = this.employeeSearchTerm.trim().toLowerCase();
    return this.allEmployees.filter((e) => {
      const fullName = (e.name || `${e.firstName || ''} ${e.lastName || ''}`).toLowerCase();
      const code = (e.employeeCode || e.legacyEmployeeCode || '').toLowerCase();
      const dept = (e.department || '').toLowerCase();
      return fullName.includes(s) || code.includes(s) || dept.includes(s);
    });
  }

  selectAllDepartments(): void {
    this.selectedDepartmentNames = this.departments.map(d => d.name);
  }

  deselectAllDepartments(): void {
    this.selectedDepartmentNames = [];
  }

  selectAllEmployees(): void {
    const currentFiltered = this.filteredEmployees.map(e => Number(e.id)).filter(id => !isNaN(id));
    this.selectedEmployeeIds = Array.from(new Set([...this.selectedEmployeeIds, ...currentFiltered]));
  }

  deselectAllEmployees(): void {
    this.selectedEmployeeIds = [];
  }

  submitAssignment(): void {
    if (this.assignmentType === 'Selected' && this.selectedEmployeeIds.length === 0) {
      this.showToast('Please select at least one employee to assign.', 'error');
      return;
    }
    if (this.assignmentType === 'Department' && this.selectedDepartmentNames.length === 0) {
      this.showToast('Please select at least one department to assign.', 'error');
      return;
    }

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
        this.showToast(`Successfully assigned training to ${res.assigned_count} employee(s).`, 'success');
        this.selectedEmployeeIds = [];
        this.selectedDepartmentNames = [];
        this.loadAssignments();
        this.loadTraining();
      },
      error: (err) => {
        this.isAssigning = false;
        this.showToast('Assignment failed: ' + (err.error?.detail || err.message), 'error');
      }
    });
  }
}
