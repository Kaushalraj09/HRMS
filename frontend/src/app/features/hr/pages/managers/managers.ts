import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { Subscription } from 'rxjs';

import { Employee } from '../../../../core/models/employee.model';
import { EmployeeService } from '../../../../core/services/employee.service';
import { AuthService } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';
import { MasterDataService } from '../../../../core/services/master-data.service';
import { CustomSelectComponent } from '../../../../shared/components/custom-select/custom-select';
import { ManagerAssignmentModalComponent } from '../employees/modals/manager-assignment-modal/manager-assignment-modal';
import { EmployeeAddModalComponent } from '../employees/modals/employee-add-modal/employee-add-modal';
import { EmployeeEditModalComponent } from '../employees/modals/employee-edit-modal/employee-edit-modal';

@Component({
  selector: 'app-managers-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    RouterModule,
    CustomSelectComponent,
    ManagerAssignmentModalComponent,
    EmployeeAddModalComponent,
    EmployeeEditModalComponent
  ],
  templateUrl: './managers.html',
  styleUrls: ['./managers.css']
})
export class ManagersComponent implements OnInit, OnDestroy {
  currentUser: any = null;
  userRoleLabel = 'Admin';
  isLoading = false;

  // Data
  managers: Employee[] = [];
  filteredManagers: Employee[] = [];
  allEmployees: Employee[] = [];
  eligibleEmployeesToPromote: Array<{ label: string; value: string }> = [];

  // Filters
  searchControl = new FormControl('');
  departmentControl = new FormControl('');
  statusControl = new FormControl('');

  departmentsOptions: Array<{ label: string; value: string }> = [
    { label: 'All Departments', value: '' }
  ];
  statusOptions = [
    { label: 'All Statuses', value: '' },
    { label: 'Active', value: 'Active' },
    { label: 'Inactive', value: 'Inactive' }
  ];

  // Stats
  stats = {
    total: 0,
    totalTeamMembers: 0,
    departmentsCount: 0,
    active: 0
  };

  // Modals state
  teamModalOpen = false;
  selectedManagerForTeam: Employee | null = null;

  addManagerModalOpen = false;
  editManagerModalOpen = false;
  selectedManagerForEdit: Employee | null = null;

  assignPickerModalOpen = false;
  selectedEmployeeIdToPromote: string = '';
  isPromoting = false;

  // Subscriptions
  private subscriptions = new Subscription();

  constructor(
    private readonly employeeService: EmployeeService,
    private readonly authService: AuthService,
    private readonly masterDataService: MasterDataService,
    private readonly toastService: ToastService,
    private readonly cdr: ChangeDetectorRef,
    private readonly router: Router
  ) {}

  ngOnInit(): void {
    this.currentUser = this.authService.getCurrentUser();
    const role = (this.currentUser?.role || '').toLowerCase();
    this.userRoleLabel = role === 'admin' ? 'Master Admin' : 'HR Personnel';

    this.loadDepartmentOptions();
    this.loadManagers();
    this.loadAllEmployees();

    this.subscriptions.add(
      this.searchControl.valueChanges.subscribe(() => this.applyFilters())
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  loadDepartmentOptions(): void {
    this.masterDataService.getDepartments().subscribe({
      next: (depts) => {
        if (depts && depts.length > 0) {
          this.departmentsOptions = [
            { label: 'All Departments', value: '' },
            ...depts.map(d => ({ label: d.name, value: d.name }))
          ];
          this.cdr.markForCheck();
        }
      },
      error: () => {}
    });
  }

  loadManagers(): void {
    this.isLoading = true;
    this.cdr.markForCheck();

    this.employeeService.getAllManagers().subscribe({
      next: (managers) => {
        this.managers = managers || [];
        this.computeStats();
        this.applyFilters();
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.isLoading = false;
        this.toastService.showError(err?.error?.detail || 'Failed to load managers');
        this.cdr.markForCheck();
      }
    });
  }

  loadAllEmployees(): void {
    this.employeeService.getEmployees(1, 1000, '', '', '', 'Active').subscribe({
      next: (res) => {
        this.allEmployees = res.data || [];
        this.updateEligibleEmployees();
        this.cdr.markForCheck();
      },
      error: () => {}
    });
  }

  updateEligibleEmployees(): void {
    const managerUserIds = new Set(this.managers.map(m => String(m.id)));
    const eligible = this.allEmployees.filter(
      emp => !managerUserIds.has(String(emp.id)) && !emp.isManager && emp.userRole?.toLowerCase() !== 'manager'
    );
    this.eligibleEmployeesToPromote = eligible.map(emp => ({
      label: `${emp.employeeCode} - ${emp.name} (${emp.department || 'No Dept'})`,
      value: String(emp.id)
    }));
  }

  computeStats(): void {
    const total = this.managers.length;
    let totalTeam = 0;
    let active = 0;
    const depts = new Set<string>();

    for (const m of this.managers) {
      totalTeam += m.directReportsCount || 0;
      if (m.status === 'Active') active++;
      if (m.department) depts.add(m.department);
    }

    this.stats = {
      total,
      totalTeamMembers: totalTeam,
      departmentsCount: depts.size,
      active
    };
  }

  applyFilters(): void {
    const search = (this.searchControl.value || '').trim().toLowerCase();
    const dept = (this.departmentControl.value || '').trim().toLowerCase();
    const status = (this.statusControl.value || '').trim().toLowerCase();

    this.filteredManagers = this.managers.filter(m => {
      if (dept && (m.department || '').toLowerCase() !== dept) return false;
      if (status && (m.status || '').toLowerCase() !== status) return false;

      if (search) {
        const name = (m.name || '').toLowerCase();
        const code = (m.employeeCode || '').toLowerCase();
        const email = (m.officialEmail || '').toLowerCase();
        const designation = (m.designation || '').toLowerCase();
        return name.includes(search) || code.includes(search) || email.includes(search) || designation.includes(search);
      }
      return true;
    });
    this.cdr.markForCheck();
  }

  onReset(): void {
    this.searchControl.setValue('');
    this.departmentControl.setValue('');
    this.statusControl.setValue('');
    this.applyFilters();
  }

  // --- Modal Open Handlers ---
  openAddManagerModal(): void {
    this.addManagerModalOpen = true;
  }

  closeAddManagerModal(saved?: boolean): void {
    this.addManagerModalOpen = false;
    if (saved) {
      this.toastService.showSuccess('New manager created successfully');
      this.loadManagers();
      this.loadAllEmployees();
    }
  }

  openAssignPickerModal(): void {
    this.selectedEmployeeIdToPromote = '';
    this.updateEligibleEmployees();
    this.assignPickerModalOpen = true;
  }

  closeAssignPickerModal(): void {
    this.assignPickerModalOpen = false;
    this.selectedEmployeeIdToPromote = '';
  }

  confirmPromoteEmployee(): void {
    if (!this.selectedEmployeeIdToPromote) {
      this.toastService.showError('Please select an employee to promote to Manager');
      return;
    }

    this.isPromoting = true;
    const empId = this.selectedEmployeeIdToPromote;
    const targetEmp = this.allEmployees.find(e => String(e.id) === String(empId));

    this.employeeService.assignManagerRole(empId).subscribe({
      next: (updatedEmp) => {
        this.isPromoting = false;
        this.closeAssignPickerModal();
        this.toastService.showSuccess(`${updatedEmp.name} promoted to Manager successfully`);
        this.loadManagers();
        this.loadAllEmployees();

        // Open team allocation modal immediately to allocate direct reports
        this.selectedManagerForTeam = updatedEmp;
        this.teamModalOpen = true;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.isPromoting = false;
        this.toastService.showError(err?.error?.detail || 'Failed to assign manager role');
        this.cdr.markForCheck();
      }
    });
  }

  openTeamModal(manager: Employee): void {
    this.selectedManagerForTeam = manager;
    this.teamModalOpen = true;
  }

  closeTeamModal(): void {
    this.teamModalOpen = false;
    this.selectedManagerForTeam = null;
    this.loadManagers();
  }

  openEditModal(manager: Employee): void {
    this.selectedManagerForEdit = manager;
    this.editManagerModalOpen = true;
  }

  closeEditModal(saved?: boolean): void {
    this.editManagerModalOpen = false;
    this.selectedManagerForEdit = null;
    if (saved) {
      this.loadManagers();
    }
  }

  revokeRole(manager: Employee): void {
    if (!confirm(`Are you sure you want to remove the Manager role from ${manager.name}? They will revert to a regular Employee.`)) {
      return;
    }

    this.employeeService.revokeManagerRole(manager.id).subscribe({
      next: (demotedEmp) => {
        this.toastService.showInfo(`Manager role removed from ${demotedEmp.name}. Reverted to regular employee.`);
        this.loadManagers();
        this.loadAllEmployees();
      },
      error: (err) => {
        this.toastService.showError(err?.error?.detail || 'Failed to revoke manager role');
      }
    });
  }

  getInitials(name: string): string {
    if (!name) return 'M';
    const parts = name.trim().split(' ');
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }

  trackById(index: number, item: Employee): string {
    return item.id;
  }
}
