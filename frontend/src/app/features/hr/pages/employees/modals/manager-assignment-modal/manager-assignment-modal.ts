import { Component, EventEmitter, Input, OnInit, Output, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Employee } from '../../../../../../core/models/employee.model';
import { EmployeeService } from '../../../../../../core/services/employee.service';
import { ToastService } from '../../../../../../core/services/toast.service';

@Component({
  selector: 'app-manager-assignment-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './manager-assignment-modal.html',
  styleUrls: ['./manager-assignment-modal.css']
})
export class ManagerAssignmentModalComponent implements OnInit, OnChanges {
  @Input() employee: Employee | null = null;
  @Input() isOpen = false;
  @Output() close = new EventEmitter<void>();
  @Output() updated = new EventEmitter<void>();

  allEmployees: Employee[] = [];
  selectedEmployeeIds = new Set<number>();
  searchTerm = '';
  isLoading = false;
  isSaving = false;

  constructor(
    private readonly employeeService: EmployeeService,
    private readonly toastService: ToastService
  ) {}

  ngOnInit(): void {
    if (this.isOpen) {
      this.loadData();
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['isOpen'] && this.isOpen) {
      this.loadData();
    }
  }

  loadData(): void {
    if (!this.employee) return;
    this.isLoading = true;
    this.selectedEmployeeIds.clear();

    // Fetch all active employees to choose from
    this.employeeService.getEmployees(1, 500, '', '', '', 'Active').subscribe({
      next: res => {
        this.allEmployees = (res.data || []).filter(e => e.id !== this.employee?.id);
        
        // If employee is already manager, load their existing team
        if (this.isManagerRole()) {
          this.employeeService.getManagerTeam(this.employee!.id).subscribe({
            next: team => {
              team.forEach(t => this.selectedEmployeeIds.add(Number(t.id)));
              this.isLoading = false;
            },
            error: () => {
              this.isLoading = false;
            }
          });
        } else {
          this.isLoading = false;
        }
      },
      error: () => {
        this.isLoading = false;
        this.toastService.showError('Failed to load employees');
      }
    });
  }

  isManagerRole(): boolean {
    return !!(this.employee?.isManager || this.employee?.userRole?.toLowerCase() === 'manager');
  }

  assignManagerRole(): void {
    if (!this.employee) return;
    this.isSaving = true;
    this.employeeService.assignManagerRole(this.employee.id).subscribe({
      next: updatedEmp => {
        this.employee = updatedEmp;
        this.isSaving = false;
        this.toastService.showSuccess(`${updatedEmp.name} assigned as Manager successfully`);
        this.updated.emit();
        this.loadData();
      },
      error: err => {
        this.isSaving = false;
        this.toastService.showError(err?.error?.detail || 'Failed to assign manager role');
      }
    });
  }

  revokeManagerRole(): void {
    if (!this.employee) return;
    if (!confirm(`Are you sure you want to remove the Manager role from ${this.employee.name}?`)) return;
    this.isSaving = true;
    this.employeeService.revokeManagerRole(this.employee.id).subscribe({
      next: updatedEmp => {
        this.employee = updatedEmp;
        this.isSaving = false;
        this.toastService.showInfo(`Manager role removed from ${updatedEmp.name}`);
        this.updated.emit();
        this.closeModal();
      },
      error: err => {
        this.isSaving = false;
        this.toastService.showError(err?.error?.detail || 'Failed to revoke manager role');
      }
    });
  }

  toggleEmployee(empId: string | number): void {
    const id = Number(empId);
    if (this.selectedEmployeeIds.has(id)) {
      this.selectedEmployeeIds.delete(id);
    } else {
      this.selectedEmployeeIds.add(id);
    }
  }

  selectAllFiltered(): void {
    this.filteredEmployees.forEach(e => this.selectedEmployeeIds.add(Number(e.id)));
  }

  deselectAll(): void {
    this.selectedEmployeeIds.clear();
  }

  saveTeamAssignment(): void {
    if (!this.employee) return;
    this.isSaving = true;
    const ids = Array.from(this.selectedEmployeeIds);
    this.employeeService.assignTeam(this.employee.id, ids).subscribe({
      next: () => {
        this.isSaving = false;
        this.toastService.showSuccess(`Team assignment saved: ${ids.length} employee(s) assigned to ${this.employee?.name}`);
        this.updated.emit();
        this.closeModal();
      },
      error: err => {
        this.isSaving = false;
        this.toastService.showError(err?.error?.detail || 'Failed to save team assignment');
      }
    });
  }

  get filteredEmployees(): Employee[] {
    if (!this.searchTerm.trim()) {
      return this.allEmployees;
    }
    const term = this.searchTerm.toLowerCase().trim();
    return this.allEmployees.filter(e =>
      e.name.toLowerCase().includes(term) ||
      e.employeeCode.toLowerCase().includes(term) ||
      (e.legacyEmployeeCode && e.legacyEmployeeCode.toLowerCase().includes(term)) ||
      (e.department && e.department.toLowerCase().includes(term))
    );
  }

  closeModal(): void {
    this.close.emit();
  }
}
