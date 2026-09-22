import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { PayrollService } from '../../../../core/services/payroll.service';
import { EmployeeService } from '../../../../core/services/employee.service';
import { MasterDataService } from '../../../../core/services/master-data.service';
import { AuthService } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select/custom-select';
import { CustomDatepickerComponent } from '../../../../shared/components/custom-datepicker/custom-datepicker';
import {
  PayrollDashboardSummary,
  EmployeeSalaryOverviewItem,
  SalaryStructure,
  SalaryComponent,
  StructureComponentItem,
  SalaryCalculationPreview,
  EmployeeSalaryAssignment,
  EmployeeSalaryAssignmentCreate,
  SalaryRevision,
  SalaryRevisionCreate,
  PayrollRunSummary,
  PayrollRunCreate,
  PayrollRecord,
  PayrollAdjustmentCreate,
  PayrollException,
  Payslip,
  StatutoryConfiguration
} from '../../../../core/models/payroll.model';

@Component({
  selector: 'app-payroll',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent, CustomDatepickerComponent],
  templateUrl: './payroll.html',
  styleUrls: ['./payroll.css']
})
export class PayrollComponent implements OnInit, OnDestroy {
  activeTab: 'dashboard' | 'salaries' | 'structures' | 'runs' | 'revisions' | 'payslips' | 'statutory' = 'dashboard';
  isLoading = false;
  isAdmin = false;
  canApprove = false;
  currentUserId: number | null = null;
  private subs: Subscription = new Subscription();

  // ----------------------------------------------------
  // Dashboard State
  // ----------------------------------------------------
  dashboardSummary: PayrollDashboardSummary | null = null;

  // ----------------------------------------------------
  // Employee Salaries State
  // ----------------------------------------------------
  salaryOverviewItems: EmployeeSalaryOverviewItem[] = [];
  salaryOverviewTotal = 0;
  salariesPage = 1;
  salariesPageSize = 15;
  searchSalary = '';
  selectedDepartment = '';
  departmentOptions: SelectOption[] = [{ label: 'All Departments', value: '' }];

  // Modals: Assign Salary
  isAssignModalOpen = false;
  isAssigning = false;
  assignEmployeeId: number | null = null;
  assignEmployeeName: string = '';
  assignEmployeeCode: string = '';
  assignStructureId: number | null = null;
  assignMode: 'ctc_based' | 'gross_based' = 'ctc_based';
  assignBaseAmount: number = 0;
  assignEffectiveDate: string = '';
  salaryPreview: SalaryCalculationPreview | null = null;
  isPreviewLoading = false;

  structureOptions: SelectOption[] = [];
  modeOptions: SelectOption[] = [
    { label: 'CTC Based (Annual to Monthly Breakdown)', value: 'ctc_based' },
    { label: 'Gross Based (Direct Monthly Salary)', value: 'gross_based' }
  ];

  // Modals: View Employee Salary Breakdown
  isBreakdownModalOpen = false;
  selectedEmployeeSalary: EmployeeSalaryAssignment | null = null;

  // ----------------------------------------------------
  // Salary Structures State
  // ----------------------------------------------------
  structures: SalaryStructure[] = [];
  componentsList: SalaryComponent[] = [];
  componentSelectOptions: SelectOption[] = [];
  isStructureModalOpen = false;
  isSavingStructure = false;
  editingStructureId: number | null = null;
  deleteModalOpen = false;
  structureToDelete: SalaryStructure | null = null;
  isDeletingStructure = false;
  newStructureCode = '';
  newStructureName = '';
  newStructureDescription = '';
  newStructureCalculationMode: 'ctc_based' | 'gross_based' = 'ctc_based';
  newStructureIsActive = true;
  newStructureComponents: {
    component_id: number;
    component_code: string;
    calculation_type: string;
    value: number;
    is_taxable: boolean;
  }[] = [];

  structurePreviewCtc: number = 216007;
  structurePreview: SalaryCalculationPreview | null = null;
  isStructurePreviewLoading: boolean = false;

  calcTypeOptions: SelectOption[] = [
    { label: 'Percentage of Basic', value: 'percentage_of_basic' },
    { label: 'Percentage of Gross', value: 'percentage_of_gross' },
    { label: 'Percentage of CTC', value: 'percentage_of_ctc' },
    { label: 'Flat Amount', value: 'flat_amount' },
    { label: 'Balancing Component', value: 'formula' }
  ];

  // ----------------------------------------------------
  // Payroll Runs State
  // ----------------------------------------------------
  payrollRuns: PayrollRunSummary[] = [];
  selectedRunYear: number = new Date().getFullYear();
  selectedRunMonth: number = new Date().getMonth() + 1;
  selectedRunStatus: string = '';

  yearOptions: SelectOption[] = [
    { label: '2025', value: 2025 },
    { label: '2026', value: 2026 },
    { label: '2027', value: 2027 }
  ];

  monthOptions: SelectOption[] = [
    { label: 'January', value: 1 },
    { label: 'February', value: 2 },
    { label: 'March', value: 3 },
    { label: 'April', value: 4 },
    { label: 'May', value: 5 },
    { label: 'June', value: 6 },
    { label: 'July', value: 7 },
    { label: 'August', value: 8 },
    { label: 'September', value: 9 },
    { label: 'October', value: 10 },
    { label: 'November', value: 11 },
    { label: 'December', value: 12 }
  ];

  runStatusFilterOptions: SelectOption[] = [
    { label: 'All Statuses', value: '' },
    { label: 'Draft', value: 'DRAFT' },
    { label: 'Pending Approval', value: 'PENDING_APPROVAL' },
    { label: 'Approved', value: 'APPROVED' },
    { label: 'Locked', value: 'LOCKED' },
    { label: 'Paid', value: 'PAID' }
  ];

  // New Run Execution Modal
  isExecuteRunModalOpen = false;
  executingRun = false;
  newRunYear: number = new Date().getFullYear();
  newRunMonth: number = new Date().getMonth() + 1;
  newRunRemarks = '';

  // Run Details View
  selectedRun: PayrollRunSummary | null = null;
  runRecords: PayrollRecord[] = [];
  runRecordsTotal = 0;
  runRecordsPage = 1;
  runRecordsPageSize = 15;
  searchRecord = '';
  selectedRecordDepartment = '';
  selectedRecordStatus = '';

  // Delete Run Modal
  deleteRunModalOpen = false;
  runToDelete: PayrollRunSummary | null = null;
  isDeletingRun = false;

  // Manual Adjustment Modal
  isAdjustmentModalOpen = false;
  isSavingAdjustment = false;
  selectedRecordForAdjustment: PayrollRecord | null = null;
  adjustmentType: string = 'BONUS';
  adjustmentAmount: number = 0;
  adjustmentReason: string = '';

  adjustmentTypeOptions: SelectOption[] = [
    { label: 'Bonus (Earning)', value: 'BONUS' },
    { label: 'Incentive (Earning)', value: 'INCENTIVE' },
    { label: 'Arrears (Earning)', value: 'ARREARS' },
    { label: 'Other Deduction (Deduction)', value: 'OTHER_DEDUCTION' },
    { label: 'Penalty (Deduction)', value: 'PENALTY' }
  ];

  // Exceptions
  runExceptions: PayrollException[] = [];
  isExceptionModalOpen = false;
  resolvingException: PayrollException | null = null;
  exceptionResolutionNotes = '';

  // ----------------------------------------------------
  // Salary Revisions State
  // ----------------------------------------------------
  revisions: SalaryRevision[] = [];
  revisionsTotal = 0;
  selectedRevisionStatus = '';
  revisionStatusOptions: SelectOption[] = [
    { label: 'All Statuses', value: '' },
    { label: 'Pending', value: 'PENDING' },
    { label: 'Approved', value: 'APPROVED' },
    { label: 'Rejected', value: 'REJECTED' }
  ];

  // Create Revision Modal
  isRevisionModalOpen = false;
  isSavingRevision = false;
  revisionEmployeeId: number | null = null;
  revisionEmployeeOptions: SelectOption[] = [];
  revisionProposedAnnualCtc: number = 0;
  revisionProposedGross: number = 0;
  revisionIncrementPercent: number = 0;
  revisionEffectiveDate: string = '';
  revisionReason: string = '';

  // ----------------------------------------------------
  // Payslips State
  // ----------------------------------------------------
  allPayslips: Payslip[] = [];
  payslipsTotal = 0;
  payslipsPage = 1;
  payslipsMonth = '';
  payslipsSearch = '';

  // ----------------------------------------------------
  // Statutory Compliance State
  // ----------------------------------------------------
  statutoryConfigs: StatutoryConfiguration[] = [];
  isEditStatutoryModalOpen = false;
  editingStatutoryConfig: StatutoryConfiguration | null = null;
  editStatutoryValue: number = 0;
  editStatutoryEffectiveFrom: string = '';
  editStatutoryNotes: string = '';

  constructor(
    private payrollService: PayrollService,
    private employeeService: EmployeeService,
    private masterDataService: MasterDataService,
    private authService: AuthService,
    private toast: ToastService,
    private cdr: ChangeDetectorRef,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    const user = this.authService.getCurrentUser();
    const role = (user?.role || '').toLowerCase();
    this.isAdmin = role === 'admin';
    this.canApprove = role === 'admin' || role === 'hr';
    this.currentUserId = user?.id ? Number(user.id) : null;

    const today = new Date();
    this.assignEffectiveDate = today.toISOString().split('T')[0];
    this.revisionEffectiveDate = today.toISOString().split('T')[0];

    this.loadDepartments();
    this.loadStructures();
    this.loadComponents();

    const initialTab = this.route.snapshot.params['tab'] || this.route.snapshot.queryParams['tab'];
    if (initialTab && this.isValidTab(initialTab)) {
      this.switchTab(initialTab, false);
    } else {
      this.loadDashboard();
    }

    this.subs.add(
      this.route.params.subscribe(params => {
        const tabParam = params['tab'];
        if (tabParam && this.isValidTab(tabParam) && tabParam !== this.activeTab) {
          this.switchTab(tabParam, false);
        }
      })
    );

    this.subs.add(
      this.route.queryParams.subscribe(qParams => {
        const tabParam = qParams['tab'];
        if (tabParam && this.isValidTab(tabParam) && tabParam !== this.activeTab) {
          this.switchTab(tabParam, false);
        }
      })
    );
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
  }

  isValidTab(tab: string): tab is 'dashboard' | 'salaries' | 'structures' | 'runs' | 'revisions' | 'payslips' | 'statutory' {
    return ['dashboard', 'salaries', 'structures', 'runs', 'revisions', 'payslips', 'statutory'].includes(tab);
  }

  switchTab(tab: 'dashboard' | 'salaries' | 'structures' | 'runs' | 'revisions' | 'payslips' | 'statutory', updateUrl = true): void {
    this.activeTab = tab;
    this.selectedRun = null;

    if (updateUrl) {
      const currentUrl = this.router.url.split('?')[0];
      const base = currentUrl.includes('/master-dashboard') ? '/master-dashboard/payroll' : '/hr-dashboard/payroll';
      this.router.navigate([base, tab], { replaceUrl: true });
    }

    switch (tab) {
      case 'dashboard':
        this.loadDashboard();
        break;
      case 'salaries':
        this.loadSalaries();
        break;
      case 'structures':
        this.loadStructures();
        break;
      case 'runs':
        this.loadRuns();
        break;
      case 'revisions':
        this.loadRevisions();
        break;
      case 'payslips':
        this.loadPayslips();
        break;
      case 'statutory':
        this.loadStatutoryConfigs();
        break;
    }
  }

  // ==========================================
  // Master Data & Dropdowns
  // ==========================================
  loadDepartments(): void {
    this.subs.add(
      this.masterDataService.getDepartments().subscribe({
        next: (deps) => {
          this.departmentOptions = [
            { label: 'All Departments', value: '' },
            ...deps.map(d => ({ label: d.name, value: d.name }))
          ];
        },
        error: () => {}
      })
    );
  }

  loadComponents(): void {
    this.subs.add(
      this.payrollService.getComponents().subscribe({
        next: (comps) => {
          this.componentsList = comps;
          this.componentSelectOptions = (comps || []).map(c => ({
            label: `${c.name} (${c.code})`,
            value: c.id
          }));
        },
        error: (err) => console.error('Failed to load components', err)
      })
    );
  }

  loadStructures(): void {
    this.subs.add(
      this.payrollService.getStructures().subscribe({
        next: (structs) => {
          this.structures = structs;
          this.structureOptions = structs.map(s => ({
            label: `${s.name} (${s.code}) - ${s.salary_basis || 'CTC'}`,
            value: s.id
          }));
          if (this.structureOptions.length > 0 && !this.assignStructureId) {
            this.assignStructureId = this.structureOptions[0].value;
          }
        },
        error: (err) => console.error('Failed to load structures', err)
      })
    );
  }

  // ==========================================
  // 1. Dashboard
  // ==========================================
  loadDashboard(): void {
    this.isLoading = true;
    this.subs.add(
      this.payrollService.getDashboardSummary().subscribe({
        next: (res) => {
          if (res) {
            res.last_net_payout = res.current_month_net || res.previous_month_net || 0;
            res.monthly_variance = res.net_variance_pct || 0;
            res.configured_salaries = res.assigned_salary_count;
            res.missing_salaries = res.missing_salary_count;
            const deptList = res.department_costs?.map(d => ({
              department: d.department,
              total_cost: d.monthly_cost || d.total_cost || 0,
              employee_count: d.employee_count || 1,
              percentage: 0
            })) || [];
            const sumCost = deptList.reduce((acc, curr) => acc + curr.total_cost, 0);
            deptList.forEach(d => {
              d.percentage = sumCost > 0 ? Math.round((d.total_cost / sumCost) * 100) : 0;
            });
            res.department_cost_breakdown = deptList;
            res.total_department_cost = sumCost;
          }
          this.dashboardSummary = res;
          this.isLoading = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.isLoading = false;
          this.toast.showError(err?.error?.detail || 'Failed to load payroll dashboard', 'Error');
        }
      })
    );
  }

  // ==========================================
  // 2. Employee Salaries
  // ==========================================
  loadSalaries(): void {
    this.isLoading = true;
    const skip = (this.salariesPage - 1) * this.salariesPageSize;
    this.subs.add(
      this.payrollService.getAllEmployeeSalaries(
        this.searchSalary,
        this.selectedDepartment,
        skip,
        this.salariesPageSize
      ).subscribe({
        next: (res) => {
          res.items.forEach(item => {
            item.has_salary_configured = item.has_salary;
            item.monthly_gross = item.gross_monthly;
            item.monthly_net = item.net_monthly;
          });
          this.salaryOverviewItems = res.items;
          this.salaryOverviewTotal = res.total;
          this.isLoading = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.isLoading = false;
          this.toast.showError(err?.error?.detail || 'Failed to load employee salaries', 'Error');
        }
      })
    );
  }

  onSalariesFilterChange(): void {
    this.salariesPage = 1;
    this.loadSalaries();
  }

  openAssignModal(item: EmployeeSalaryOverviewItem): void {
    this.assignEmployeeId = item.employee_id;
    this.assignEmployeeName = item.employee_name;
    this.assignEmployeeCode = item.employee_code;
    this.assignBaseAmount = item.annual_ctc ? Number(item.annual_ctc) : (item.gross_monthly ? Number(item.gross_monthly) * 12 : 600000);
    this.assignMode = (item.salary_basis === 'GROSS') ? 'gross_based' : 'ctc_based';
    this.salaryPreview = null;
    this.isAssignModalOpen = true;

    if (item.structure_id && this.structureOptions.some(o => o.value === item.structure_id)) {
      this.assignStructureId = item.structure_id;
    } else if (this.structureOptions.length > 0) {
      this.assignStructureId = this.structureOptions[0].value;
    }
    this.calculateSalaryPreview();
  }

  closeAssignModal(): void {
    this.isAssignModalOpen = false;
    this.salaryPreview = null;
  }

  calculateSalaryPreview(): void {
    if (!this.assignStructureId || !this.assignBaseAmount || this.assignBaseAmount <= 0) {
      this.salaryPreview = null;
      return;
    }

    this.isPreviewLoading = true;
    this.payrollService.calculatePreview({
      structure_id: this.assignStructureId,
      salary_basis: this.assignMode === 'ctc_based' ? 'CTC' : 'GROSS',
      ctc_amount: this.assignBaseAmount,
      salary_type: this.assignMode === 'ctc_based' ? 'Annual' : 'Monthly'
    }).subscribe({
      next: (preview) => {
        preview.monthly_gross = preview.gross_monthly;
        preview.monthly_net = preview.net_monthly;
        preview.monthly_deductions = preview.total_deductions_monthly;
        preview.components = [
          ...(preview.earnings || []),
          ...(preview.deductions || []),
          ...(preview.employer_contributions || [])
        ];
        this.salaryPreview = preview;
        this.isPreviewLoading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.isPreviewLoading = false;
        this.toast.showError(err?.error?.detail || 'Calculation failed', 'Preview Error');
      }
    });
  }

  saveEmployeeSalaryAssignment(): void {
    if (!this.assignEmployeeId || !this.assignStructureId || !this.assignBaseAmount) {
      this.toast.showWarning('Please fill in all required fields.', 'Validation');
      return;
    }

    const payload: EmployeeSalaryAssignmentCreate = {
      employee_id: this.assignEmployeeId,
      salary_structure_id: this.assignStructureId,
      salary_basis: this.assignMode === 'ctc_based' ? 'CTC' : 'GROSS',
      salary_type: this.assignMode === 'ctc_based' ? 'Annual' : 'Monthly',
      ctc_amount: this.assignBaseAmount,
      effective_from: this.assignEffectiveDate
    };

    this.isAssigning = true;
    this.payrollService.assignEmployeeSalary(payload).subscribe({
      next: () => {
        this.isAssigning = false;
        this.isAssignModalOpen = false;
        this.toast.showSuccess(`Salary structure assigned to ${this.assignEmployeeName}`, 'Success');
        this.loadSalaries();
      },
      error: (err) => {
        this.isAssigning = false;
        this.toast.showError(err?.error?.detail || 'Assignment failed', 'Error');
      }
    });
  }

  viewEmployeeBreakdown(employeeId: number): void {
    this.isLoading = true;
    this.payrollService.getEmployeeSalary(employeeId).subscribe({
      next: (salary) => {
        salary.monthly_gross = salary.gross_monthly;
        salary.monthly_net = salary.net_monthly;
        salary.components = [
          ...(salary.breakdown?.earnings || []),
          ...(salary.breakdown?.deductions || []),
          ...(salary.breakdown?.employer_contributions || [])
        ];
        this.selectedEmployeeSalary = salary;
        this.isBreakdownModalOpen = true;
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.isLoading = false;
        this.toast.showError(err?.error?.detail || 'No salary structure configured for this employee.', 'Not Found');
      }
    });
  }

  closeBreakdownModal(): void {
    this.isBreakdownModalOpen = false;
    this.selectedEmployeeSalary = null;
  }

  // ==========================================
  // 3. Salary Structures
  // ==========================================
  openCreateStructureModal(): void {
    this.editingStructureId = null;
    this.newStructureCode = '';
    this.newStructureName = '';
    this.newStructureDescription = '';
    this.newStructureCalculationMode = 'ctc_based';
    this.newStructureIsActive = true;
    this.newStructureComponents = [];

    const basic = this.componentsList.find(c => c.code === 'BASIC');
    const hra = this.componentsList.find(c => c.code === 'HRA');
    const sa = this.componentsList.find(c => c.code === 'SPECIAL_ALLOWANCE');

    if (basic) {
      this.newStructureComponents.push({
        component_id: basic.id,
        component_code: basic.code,
        calculation_type: 'percentage_of_gross',
        value: 50,
        is_taxable: true
      });
    }
    if (hra) {
      this.newStructureComponents.push({
        component_id: hra.id,
        component_code: hra.code,
        calculation_type: 'percentage_of_basic',
        value: 40,
        is_taxable: true
      });
    }
    if (sa) {
      this.newStructureComponents.push({
        component_id: sa.id,
        component_code: sa.code,
        calculation_type: 'formula',
        value: 0,
        is_taxable: true
      });
    }

    this.isStructureModalOpen = true;
  }

  openEditStructureModal(structure: SalaryStructure): void {
    this.editingStructureId = structure.id;
    this.newStructureCode = structure.code;
    this.newStructureName = structure.name;
    this.newStructureDescription = structure.description || '';
    this.newStructureCalculationMode = structure.salary_basis === 'CTC' ? 'ctc_based' : 'gross_based';
    this.newStructureIsActive = structure.is_active !== undefined ? structure.is_active : true;

    this.newStructureComponents = (structure.components || []).map(c => {
      let calcType = 'percentage_of_basic';
      const ct = (c.calculation_type || '').toUpperCase();
      const cb = (c.calculation_basis || '').toUpperCase();

      if (ct === 'BALANCE' || ct === 'FORMULA') {
        calcType = 'formula';
      } else if (ct === 'FIXED' || ct === 'FLAT_AMOUNT') {
        calcType = 'flat_amount';
      } else if (ct === 'PERCENTAGE' || ct.includes('PERCENTAGE')) {
        if (cb === 'BASIC' || ct.includes('BASIC')) {
          calcType = 'percentage_of_basic';
        } else if (cb === 'GROSS' || ct.includes('GROSS')) {
          calcType = 'percentage_of_gross';
        } else {
          calcType = 'percentage_of_ctc';
        }
      }

      return {
        component_id: c.component_id,
        component_code: c.component_code || '',
        calculation_type: calcType,
        value: c.percentage_or_value || 0,
        is_taxable: true
      };
    });

    this.isStructureModalOpen = true;
    this.calculateStructureTestPreview();
  }

  closeCreateStructureModal(): void {
    this.isStructureModalOpen = false;
    this.editingStructureId = null;
    this.structurePreview = null;
  }

  calculateStructureTestPreview(): void {
    if (!this.editingStructureId || !this.structurePreviewCtc || this.structurePreviewCtc <= 0) {
      this.structurePreview = null;
      return;
    }

    this.isStructurePreviewLoading = true;
    this.payrollService.calculatePreview({
      structure_id: this.editingStructureId,
      salary_basis: this.newStructureCalculationMode === 'ctc_based' ? 'CTC' : 'GROSS',
      ctc_amount: this.structurePreviewCtc,
      salary_type: this.newStructureCalculationMode === 'ctc_based' ? 'Annual' : 'Monthly'
    }).subscribe({
      next: (preview) => {
        preview.monthly_gross = preview.gross_monthly;
        preview.monthly_net = preview.net_monthly;
        preview.monthly_deductions = preview.total_deductions_monthly;
        preview.components = [
          ...(preview.earnings || []),
          ...(preview.deductions || []),
          ...(preview.employer_contributions || [])
        ];
        this.structurePreview = preview;
        this.isStructurePreviewLoading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.isStructurePreviewLoading = false;
        this.toast.showError(err?.error?.detail || 'Structure preview calculation failed', 'Preview Error');
        this.cdr.markForCheck();
      }
    });
  }

  addStructureComponent(): void {
    if (this.componentsList.length === 0) return;
    const comp = this.componentsList[0];
    this.newStructureComponents.push({
      component_id: comp.id,
      component_code: comp.code,
      calculation_type: 'percentage_of_basic',
      value: 10,
      is_taxable: true
    });
  }

  removeStructureComponent(index: number): void {
    this.newStructureComponents.splice(index, 1);
  }

  onComponentSelectionChange(index: number, componentId: any): void {
    const numId = Number(componentId);
    this.newStructureComponents[index].component_id = numId;
    const comp = this.componentsList.find(c => c.id === numId);
    if (comp) {
      this.newStructureComponents[index].component_code = comp.code;
      if (comp.code === 'SPECIAL_ALLOWANCE' || comp.calculation_type?.toUpperCase() === 'BALANCE') {
        this.newStructureComponents[index].calculation_type = 'formula';
        this.newStructureComponents[index].value = 0;
      }
    }
  }

  openDeleteStructureModal(structure: SalaryStructure): void {
    this.structureToDelete = structure;
    this.deleteModalOpen = true;
    this.cdr.markForCheck();
  }

  closeDeleteStructureModal(): void {
    if (this.isDeletingStructure) return;
    this.deleteModalOpen = false;
    this.structureToDelete = null;
    this.cdr.markForCheck();
  }

  confirmDeleteStructure(): void {
    if (!this.structureToDelete) return;
    this.isDeletingStructure = true;
    const structure = this.structureToDelete;

    this.payrollService.deleteStructure(structure.id).subscribe({
      next: (res) => {
        this.isDeletingStructure = false;
        this.deleteModalOpen = false;
        this.structureToDelete = null;
        this.toast.showSuccess(res.message || `Salary structure '${structure.name}' deleted successfully`, 'Success');
        this.loadStructures();
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.isDeletingStructure = false;
        this.toast.showError(err?.error?.detail || 'Failed to delete salary structure', 'Error');
        this.cdr.markForCheck();
      }
    });
  }

  deleteStructure(structure: SalaryStructure): void {
    this.openDeleteStructureModal(structure);
  }

  saveStructure(): void {
    if (!this.newStructureCode.trim() || !this.newStructureName.trim()) {
      this.toast.showWarning('Code and Name are required.', 'Validation');
      return;
    }

    const componentsToSave: StructureComponentItem[] = this.newStructureComponents.map((c, idx) => {
      let calcType = 'PERCENTAGE';
      let calcBasis: string | null = 'CTC';

      if (c.calculation_type === 'formula' || c.calculation_type === 'balance') {
        calcType = 'BALANCE';
        calcBasis = null;
      } else if (c.calculation_type === 'flat_amount' || c.calculation_type === 'fixed') {
        calcType = 'FIXED';
        calcBasis = null;
      } else if (c.calculation_type === 'percentage_of_basic') {
        calcType = 'PERCENTAGE';
        calcBasis = 'BASIC';
      } else if (c.calculation_type === 'percentage_of_gross') {
        calcType = 'PERCENTAGE';
        calcBasis = 'GROSS';
      } else if (c.calculation_type === 'percentage_of_ctc') {
        calcType = 'PERCENTAGE';
        calcBasis = 'CTC';
      }

      return {
        component_id: c.component_id,
        calculation_type: calcType,
        calculation_basis: calcBasis,
        percentage_or_value: c.value || 0,
        sequence_order: idx + 1
      };
    });

    this.isSavingStructure = true;
    const payload = {
      code: this.newStructureCode.trim().toUpperCase(),
      name: this.newStructureName.trim(),
      description: this.newStructureDescription.trim(),
      salary_basis: (this.newStructureCalculationMode === 'ctc_based' ? 'CTC' : 'GROSS') as 'CTC' | 'GROSS',
      is_active: this.newStructureIsActive,
      components: componentsToSave
    };

    if (this.editingStructureId) {
      this.payrollService.updateStructure(this.editingStructureId, payload).subscribe({
        next: () => {
          this.isSavingStructure = false;
          this.isStructureModalOpen = false;
          this.editingStructureId = null;
          this.toast.showSuccess('Salary structure updated successfully', 'Success');
          this.loadStructures();
        },
        error: (err) => {
          this.isSavingStructure = false;
          this.toast.showError(err?.error?.detail || 'Failed to update structure', 'Error');
        }
      });
    } else {
      this.payrollService.createStructure(payload).subscribe({
        next: () => {
          this.isSavingStructure = false;
          this.isStructureModalOpen = false;
          this.toast.showSuccess('Salary structure created successfully', 'Success');
          this.loadStructures();
        },
        error: (err) => {
          this.isSavingStructure = false;
          this.toast.showError(err?.error?.detail || 'Failed to create structure', 'Error');
        }
      });
    }
  }

  // ==========================================
  // 4. Payroll Runs
  // ==========================================
  loadRuns(): void {
    this.isLoading = true;
    this.subs.add(
      this.payrollService.getRuns(
        this.selectedRunYear,
        undefined,
        this.selectedRunStatus || undefined
      ).subscribe({
        next: (runs) => {
          this.payrollRuns = runs;
          this.isLoading = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.isLoading = false;
          this.toast.showError(err?.error?.detail || 'Failed to load payroll runs', 'Error');
        }
      })
    );
  }

  openExecuteRunModal(): void {
    this.newRunYear = new Date().getFullYear();
    this.newRunMonth = new Date().getMonth() + 1;
    this.newRunRemarks = '';
    this.isExecuteRunModalOpen = true;
  }

  closeExecuteRunModal(): void {
    this.isExecuteRunModalOpen = false;
  }

  executePayrollRun(): void {
    this.executingRun = true;
    const payload: PayrollRunCreate = {
      year: this.newRunYear,
      month: this.newRunMonth
    };

    this.payrollService.executeRun(payload).subscribe({
      next: (run) => {
        this.executingRun = false;
        this.isExecuteRunModalOpen = false;
        this.toast.showSuccess(`Payroll Run executed for ${run.period_name || (this.getMonthName(run.month || 1) + ' ' + (run.year || ''))}`, 'Batch Complete');
        this.loadRuns();
        this.viewRunDetails(run);
      },
      error: (err) => {
        this.executingRun = false;
        this.toast.showError(err?.error?.detail || 'Execution failed', 'Payroll Run Error');
      }
    });
  }

  viewRunDetails(run: PayrollRunSummary): void {
    this.selectedRun = run;
    this.runRecordsPage = 1;
    this.loadRunRecords();
    this.loadRunExceptions(run.id);
  }

  backToRunsList(): void {
    this.selectedRun = null;
    this.runRecords = [];
    this.runExceptions = [];
    this.loadRuns();
  }

  loadRunRecords(): void {
    if (!this.selectedRun) return;
    this.isLoading = true;
    const skip = (this.runRecordsPage - 1) * this.runRecordsPageSize;
    this.payrollService.getPayrollRecords(
      this.selectedRun.id,
      this.searchRecord || undefined,
      this.selectedRecordDepartment || undefined,
      this.selectedRecordStatus || undefined,
      skip,
      this.runRecordsPageSize
    ).subscribe({
      next: (res) => {
        this.runRecords = res.items;
        this.runRecordsTotal = res.total;
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.isLoading = false;
        this.toast.showError(err?.error?.detail || 'Failed to load records', 'Error');
      }
    });
  }

  loadRunExceptions(runId: number): void {
    this.payrollService.getExceptions(runId).subscribe({
      next: (exceptions) => {
        this.runExceptions = exceptions;
        this.cdr.markForCheck();
      },
      error: () => {}
    });
  }

  submitSelectedRunForApproval(): void {
    if (!this.selectedRun) return;
    this.isLoading = true;
    this.payrollService.submitRunForApproval(this.selectedRun.id).subscribe({
      next: () => {
        this.isLoading = false;
        this.toast.showSuccess('Run submitted for administrative approval', 'Submitted');
        this.reloadCurrentRun();
      },
      error: (err) => {
        this.isLoading = false;
        this.toast.showError(err?.error?.detail || 'Failed to submit run', 'Error');
      }
    });
  }

  approveSelectedRun(): void {
    if (!this.selectedRun) return;
    this.isLoading = true;
    this.payrollService.approveOrRejectRun(this.selectedRun.id, true).subscribe({
      next: () => {
        this.isLoading = false;
        this.toast.showSuccess('Payroll Run approved!', 'Approved');
        this.reloadCurrentRun();
      },
      error: (err) => {
        this.isLoading = false;
        this.toast.showError(err?.error?.detail || 'Approval failed', 'Error');
      }
    });
  }

  approveRunFromList(run: PayrollRunSummary, event: Event): void {
    event.stopPropagation();
    if (!confirm(`Are you sure you want to approve Payroll Run #${run.run_number}?`)) return;
    this.isLoading = true;
    this.payrollService.approveOrRejectRun(run.id, true).subscribe({
      next: () => {
        this.isLoading = false;
        this.toast.showSuccess(`Payroll Run #${run.run_number} approved!`, 'Approved');
        this.loadRuns();
      },
      error: (err) => {
        this.isLoading = false;
        this.toast.showError(err?.error?.detail || 'Approval failed', 'Error');
      }
    });
  }

  submitRunFromList(run: PayrollRunSummary, event: Event): void {
    event.stopPropagation();
    this.isLoading = true;
    this.payrollService.submitRunForApproval(run.id).subscribe({
      next: () => {
        this.isLoading = false;
        this.toast.showSuccess(`Payroll Run #${run.run_number} submitted for approval`, 'Submitted');
        this.loadRuns();
      },
      error: (err) => {
        this.isLoading = false;
        this.toast.showError(err?.error?.detail || 'Failed to submit run', 'Error');
      }
    });
  }

  rejectSelectedRun(): void {
    if (!this.selectedRun) return;
    const reason = prompt('Please enter reason for rejection:');
    if (reason === null) return;

    this.isLoading = true;
    this.payrollService.approveOrRejectRun(this.selectedRun.id, false, reason).subscribe({
      next: () => {
        this.isLoading = false;
        this.toast.showWarning('Payroll Run rejected back to draft', 'Rejected');
        this.reloadCurrentRun();
      },
      error: (err) => {
        this.isLoading = false;
        this.toast.showError(err?.error?.detail || 'Rejection failed', 'Error');
      }
    });
  }

  lockSelectedRun(): void {
    if (!this.selectedRun) return;
    if (!confirm('Locking this payroll run will generate immutable frozen payslips and publish them to employees. Proceed?')) {
      return;
    }

    this.isLoading = true;
    this.payrollService.lockRun(this.selectedRun.id).subscribe({
      next: () => {
        this.isLoading = false;
        this.toast.showSuccess('Payroll Run locked! Payslips are published.', 'Locked & Published');
        this.reloadCurrentRun();
      },
      error: (err) => {
        this.isLoading = false;
        this.toast.showError(err?.error?.detail || 'Failed to lock run', 'Error');
      }
    });
  }

  markSelectedRunPaid(): void {
    if (!this.selectedRun) return;
    this.isLoading = true;
    this.payrollService.markRunPaid(this.selectedRun.id).subscribe({
      next: () => {
        this.isLoading = false;
        this.toast.showSuccess('Payroll marked as disbursed / paid.', 'Disbursed');
        this.reloadCurrentRun();
      },
      error: (err) => {
        this.isLoading = false;
        this.toast.showError(err?.error?.detail || 'Failed to mark as paid', 'Error');
      }
    });
  }

  promptDeleteRun(run: PayrollRunSummary, event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    this.runToDelete = run;
    this.deleteRunModalOpen = true;
  }

  closeDeleteRunModal(): void {
    this.deleteRunModalOpen = false;
    this.runToDelete = null;
    this.isDeletingRun = false;
  }

  confirmDeleteRun(): void {
    if (!this.runToDelete) return;
    this.isDeletingRun = true;
    const runNumber = this.runToDelete.run_number;
    const wasInDrilldown = this.selectedRun?.id === this.runToDelete.id;

    this.payrollService.deleteRun(this.runToDelete.id).subscribe({
      next: (res) => {
        this.isDeletingRun = false;
        this.toast.showSuccess(res?.message || `Payroll Run #${runNumber} deleted successfully`, 'Deleted');
        this.closeDeleteRunModal();
        if (wasInDrilldown) {
          this.backToRunsList();
        } else {
          this.loadRuns();
        }
      },
      error: (err) => {
        this.isDeletingRun = false;
        this.toast.showError(err?.error?.detail || 'Failed to delete payroll run', 'Error');
      }
    });
  }

  reloadCurrentRun(): void {
    if (!this.selectedRun) return;
    this.payrollService.getRunDetail(this.selectedRun.id).subscribe({
      next: (detail) => {
        this.selectedRun = detail;
        this.loadRunRecords();
        this.loadRunExceptions(detail.id);
      }
    });
  }

  exportPayrollPdf(): void {
    if (!this.selectedRun) return;
    this.payrollService.exportPayrollPdf(this.selectedRun.id).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Payroll_Run_${this.selectedRun?.run_number}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
        this.toast.showSuccess('Payroll Summary PDF exported successfully', 'Downloaded');
      },
      error: () => this.toast.showError('PDF export failed', 'Error')
    });
  }

  exportPayrollCsv(): void {
    this.exportPayrollPdf();
  }

  exportBankPdf(): void {
    if (!this.selectedRun) return;
    this.payrollService.exportBankPdf(this.selectedRun.id).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Bank_Payout_${this.selectedRun?.run_number}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
        this.toast.showSuccess('Bank Disbursement PDF exported successfully', 'Downloaded');
      },
      error: () => this.toast.showError('PDF export failed', 'Error')
    });
  }

  exportBankCsv(): void {
    this.exportBankPdf();
  }

  // Adjust record modal
  openAdjustmentModal(record: PayrollRecord): void {
    this.selectedRecordForAdjustment = record;
    this.adjustmentType = 'BONUS';
    this.adjustmentAmount = 0;
    this.adjustmentReason = '';
    this.isAdjustmentModalOpen = true;
  }

  closeAdjustmentModal(): void {
    this.isAdjustmentModalOpen = false;
    this.selectedRecordForAdjustment = null;
  }

  saveAdjustment(): void {
    if (!this.selectedRecordForAdjustment || !this.adjustmentAmount || this.adjustmentAmount <= 0) {
      this.toast.showWarning('Please provide a valid adjustment amount.', 'Validation');
      return;
    }

    const payload: PayrollAdjustmentCreate = {
      payroll_record_id: this.selectedRecordForAdjustment.id,
      component_code: this.adjustmentType,
      new_amount: this.adjustmentAmount,
      reason: this.adjustmentReason.trim() || 'Manual adjustment by HR'
    };

    this.isSavingAdjustment = true;
    this.payrollService.adjustPayrollRecord(this.selectedRecordForAdjustment.id, payload).subscribe({
      next: () => {
        this.isSavingAdjustment = false;
        this.isAdjustmentModalOpen = false;
        this.toast.showSuccess('Adjustment applied successfully', 'Record Updated');
        this.loadRunRecords();
      },
      error: (err) => {
        this.isSavingAdjustment = false;
        this.toast.showError(err?.error?.detail || 'Adjustment failed', 'Error');
      }
    });
  }

  openResolveExceptionModal(exc: PayrollException): void {
    this.resolvingException = exc;
    this.exceptionResolutionNotes = '';
    this.isExceptionModalOpen = true;
  }

  closeResolveExceptionModal(): void {
    this.isExceptionModalOpen = false;
    this.resolvingException = null;
  }

  resolveException(): void {
    if (!this.resolvingException) return;
    this.payrollService.resolveException(
      this.resolvingException.id,
      this.exceptionResolutionNotes.trim() || 'Resolved by HR'
    ).subscribe({
      next: () => {
        this.toast.showSuccess('Exception resolved', 'Resolved');
        this.closeResolveExceptionModal();
        if (this.selectedRun) this.loadRunExceptions(this.selectedRun.id);
      },
      error: (err) => this.toast.showError(err?.error?.detail || 'Failed to resolve', 'Error')
    });
  }

  hasUnresolvedExceptions(): boolean {
    return this.runExceptions.some(e => !e.is_resolved);
  }

  resolveAllExceptions(): void {
    if (!this.selectedRun) return;
    const runId = this.selectedRun.id;
    this.payrollService.resolveAllExceptions(runId, 'Bulk resolved by HR (Offline / Cheque payout authorized)').subscribe({
      next: (res) => {
        this.toast.showSuccess(res.message || 'All exceptions resolved', 'Success');
        this.loadRunExceptions(runId);
      },
      error: (err) => this.toast.showError(err?.error?.detail || 'Failed to resolve all exceptions', 'Error')
    });
  }

  // ==========================================
  // 5. Salary Revisions
  // ==========================================
  loadRevisions(): void {
    this.isLoading = true;
    this.subs.add(
      this.payrollService.getRevisions(this.selectedRevisionStatus || undefined).subscribe({
        next: (res) => {
          this.revisions = res.items;
          this.revisionsTotal = res.total;
          this.isLoading = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.isLoading = false;
          this.toast.showError(err?.error?.detail || 'Failed to load revisions', 'Error');
        }
      })
    );
  }

  openCreateRevisionModal(): void {
    this.revisionEmployeeId = null;
    this.revisionProposedAnnualCtc = 0;
    this.revisionProposedGross = 0;
    this.revisionIncrementPercent = 10;
    this.revisionReason = '';
    this.isRevisionModalOpen = true;

    this.employeeService.getEmployees(1, 100, '', '', '', 'Active').subscribe({
      next: (res) => {
        this.revisionEmployeeOptions = res.data.map(e => ({
          label: `${e.firstName} ${e.lastName} (${e.employeeCode})`,
          value: e.id
        }));
        if (this.revisionEmployeeOptions.length > 0) {
          this.revisionEmployeeId = this.revisionEmployeeOptions[0].value;
        }
      }
    });
  }

  closeCreateRevisionModal(): void {
    this.isRevisionModalOpen = false;
  }

  saveRevision(): void {
    if (!this.revisionEmployeeId || !this.revisionProposedAnnualCtc) {
      this.toast.showWarning('Employee and Proposed CTC are required.', 'Validation');
      return;
    }

    const payload: SalaryRevisionCreate = {
      employee_id: this.revisionEmployeeId,
      new_salary_structure_id: this.structures[0]?.id || 1,
      new_ctc_amount: this.revisionProposedAnnualCtc,
      salary_type: 'Annual',
      effective_from: this.revisionEffectiveDate,
      reason: this.revisionReason.trim() || 'Annual Appraisal'
    };

    this.isSavingRevision = true;
    this.payrollService.createRevision(payload).subscribe({
      next: () => {
        this.isSavingRevision = false;
        this.isRevisionModalOpen = false;
        this.toast.showSuccess('Salary revision requested successfully', 'Success');
        this.loadRevisions();
      },
      error: (err) => {
        this.isSavingRevision = false;
        this.toast.showError(err?.error?.detail || 'Revision creation failed', 'Error');
      }
    });
  }

  actionRevision(revisionId: number, approved: boolean): void {
    const actionName = approved ? 'Approve' : 'Reject';
    if (!confirm(`Are you sure you want to ${actionName} this revision?`)) return;

    this.payrollService.actionRevision(revisionId, approved).subscribe({
      next: () => {
        this.toast.showSuccess(`Revision ${actionName}d successfully`, 'Success');
        this.loadRevisions();
      },
      error: (err) => this.toast.showError(err?.error?.detail || 'Action failed', 'Error')
    });
  }

  // ==========================================
  // 6. Payslips
  // ==========================================
  loadPayslips(): void {
    this.isLoading = true;
    const skip = (this.payslipsPage - 1) * 20;
    this.subs.add(
      this.payrollService.getPayslips(undefined, this.payslipsMonth || undefined, skip, 20).subscribe({
        next: (res) => {
          this.allPayslips = res.items;
          this.payslipsTotal = res.total;
          this.isLoading = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.isLoading = false;
          this.toast.showError(err?.error?.detail || 'Failed to load payslips', 'Error');
        }
      })
    );
  }

  downloadPayslipPdf(payslip: Payslip): void {
    this.payrollService.downloadPayslipPdf(payslip.id).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Payslip_${payslip.payslip_number || payslip.id}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: () => this.toast.showError('Could not download payslip PDF', 'Download Error')
    });
  }

  // ==========================================
  // 7. Statutory Configurations
  // ==========================================
  loadStatutoryConfigs(): void {
    this.isLoading = true;
    this.subs.add(
      this.payrollService.getStatutoryConfigs().subscribe({
        next: (configs) => {
          this.statutoryConfigs = configs;
          this.isLoading = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.isLoading = false;
          this.toast.showError(err?.error?.detail || 'Failed to load statutory configs', 'Error');
        }
      })
    );
  }

  openEditStatutoryModal(cfg: StatutoryConfiguration): void {
    this.editingStatutoryConfig = cfg;
    this.editStatutoryValue = cfg.employee_rate_pct;
    this.editStatutoryEffectiveFrom = new Date().toISOString().split('T')[0];
    this.editStatutoryNotes = cfg.description || '';
    this.isEditStatutoryModalOpen = true;
  }

  closeEditStatutoryModal(): void {
    this.isEditStatutoryModalOpen = false;
    this.editingStatutoryConfig = null;
  }

  saveStatutoryConfig(): void {
    if (!this.editingStatutoryConfig) return;

    this.payrollService.updateStatutoryConfig(this.editingStatutoryConfig.id, {
      employee_rate_pct: this.editStatutoryValue,
      description: this.editStatutoryNotes.trim()
    }).subscribe({
      next: () => {
        this.toast.showSuccess('Statutory configuration updated', 'Success');
        this.closeEditStatutoryModal();
        this.loadStatutoryConfigs();
      },
      error: (err) => this.toast.showError(err?.error?.detail || 'Failed to update', 'Error')
    });
  }

  // ==========================================
  // Utilities & Helpers
  // ==========================================
  getMonthName(monthNum: number): string {
    const months = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    return months[monthNum - 1] || `${monthNum}`;
  }

  formatPayrollMonth(monthStr?: string | null): string {
    if (!monthStr) return '—';
    const parts = String(monthStr).trim().split('-');
    if (parts.length === 2 && parts[0].length === 4) {
      const year = parts[0];
      const mNum = parseInt(parts[1], 10);
      if (!isNaN(mNum) && mNum >= 1 && mNum <= 12) {
        return `${this.getMonthName(mNum)} ${year}`;
      }
    }
    return monthStr;
  }

  formatCurrency(val: number | null | undefined): string {
    if (val === null || val === undefined || isNaN(val)) return '₹0.00';
    return '₹' + Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  getStatusBadgeClass(status: string): string {
    switch (status?.toUpperCase()) {
      case 'ACTIVE':
      case 'APPROVED':
      case 'LOCKED':
      case 'PAID':
        return 'badge-success';
      case 'DRAFT':
      case 'PENDING':
      case 'PENDING_APPROVAL':
      case 'UNDER REVIEW':
        return 'badge-warning';
      case 'REJECTED':
      case 'INACTIVE':
        return 'badge-danger';
      default:
        return 'badge-secondary';
    }
  }
}
