import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { MasterDataService } from '../../../../core/services/master-data.service';
import { 
  Department, 
  Designation, 
  Shift, 
  WorkLocation, 
  LeaveType, 
  Holiday 
} from '../../../../core/models/master-data.model';

@Component({
  selector: 'app-admin-master-data',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './master-data.html',
  styleUrls: ['./master-data.css']
})
export class MasterDataComponent implements OnInit, OnDestroy {
  activeTab: 'departments' | 'designations' | 'shifts' | 'locations' | 'leaves' | 'holidays' = 'departments';
  
  // Data lists
  departments: Department[] = [];
  designations: Designation[] = [];
  shifts: Shift[] = [];
  workLocations: WorkLocation[] = [];
  leaveTypes: LeaveType[] = [];
  holidays: Holiday[] = [];
  
  // Filtering & Search
  searchTerm = '';
  isDataLoading = false;

  // Add/Edit Modal State
  isModalOpen = false;
  modalMode: 'add' | 'edit' = 'add';
  selectedItemId: number | null = null;
  
  // Shared Form Model
  formModel: any = {};
  toastMessage: string | null = null;
  isErrorToast: boolean = false;

  private subscriptions = new Subscription();

  constructor(
    private readonly masterDataService: MasterDataService,
    private readonly cdr: ChangeDetectorRef
  ) {
  }

  ngOnInit(): void {
    this.loadBootstrapData();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  loadBootstrapData(): void {
    this.isDataLoading = true;
    this.subscriptions.add(
      this.masterDataService.getBootstrapData().subscribe({
        next: (res) => {
          this.departments = res.departments || [];
          this.designations = res.designations || [];
          this.shifts = res.shifts || [];
          this.workLocations = res.workLocations || [];
          this.leaveTypes = res.leaveTypes || [];
          this.holidays = res.holidays || [];
          this.isDataLoading = false;
          this.cdr.detectChanges();
        },
        error: (err) => {
          console.error('Error loading master data', err);
          this.isDataLoading = false;
          this.cdr.detectChanges();
        }
      })
    );
  }

  setActiveTab(tab: typeof this.activeTab): void {
    this.activeTab = tab;
    this.searchTerm = '';
    this.cdr.detectChanges();
  }

  // Getters for filtered data
  get filteredDepartments(): Department[] {
    const q = this.searchTerm.trim().toLowerCase();
    return this.departments.filter(d => 
      d.name.toLowerCase().includes(q) || (d.code && d.code.toLowerCase().includes(q))
    );
  }

  get filteredDesignations(): Designation[] {
    const q = this.searchTerm.trim().toLowerCase();
    return this.designations.filter(d => 
      d.name.toLowerCase().includes(q) || (d.code && d.code.toLowerCase().includes(q))
    );
  }

  get filteredShifts(): Shift[] {
    const q = this.searchTerm.trim().toLowerCase();
    return this.shifts.filter(s => 
      s.name.toLowerCase().includes(q)
    );
  }

  get filteredLocations(): WorkLocation[] {
    const q = this.searchTerm.trim().toLowerCase();
    return this.workLocations.filter(l => 
      l.name.toLowerCase().includes(q) || (l.address && l.address.toLowerCase().includes(q))
    );
  }

  get filteredLeaves(): LeaveType[] {
    const q = this.searchTerm.trim().toLowerCase();
    return this.leaveTypes.filter(l => 
      l.name.toLowerCase().includes(q) || l.code.toLowerCase().includes(q)
    );
  }

  get filteredHolidays(): Holiday[] {
    const q = this.searchTerm.trim().toLowerCase();
    return this.holidays.filter(h => 
      h.name.toLowerCase().includes(q) || h.date.includes(q)
    );
  }

  // Add/Edit Actions
  showToast(message: string, isError: boolean = false): void {
    this.toastMessage = message;
    this.isErrorToast = isError;
    this.cdr.detectChanges();
    setTimeout(() => {
      this.toastMessage = null;
      this.cdr.detectChanges();
    }, 3000);
  }

  openAddModal(): void {
    this.modalMode = 'add';
    this.selectedItemId = null;
    
    // Initialize default forms based on active tab
    if (this.activeTab === 'departments') {
      this.formModel = { name: '', code: '', is_active: true };
    } else if (this.activeTab === 'designations') {
      this.formModel = { name: '', code: '', is_active: true };
    } else if (this.activeTab === 'shifts') {
      this.formModel = { 
        name: '', 
        code: '', 
        description: '',
        start_time: '09:00', 
        end_time: '18:00',
        working_hours: 8.0,
        required_work_minutes: 480,
        grace_minutes: 30,
        lunch_duration_minutes: 40,
        lunch_start_time: '',
        lunch_end_time: '',
        half_day_hours: 4.0,
        minimum_half_day_minutes: 240,
        present_hours: 8.0,
        minimum_present_minutes: 480,
        overtime_start_time: '',
        overtime_allowed: true,
        max_overtime_minutes: 120,
        late_mark_after_minutes: 30,
        early_exit_before_minutes: 0,
        is_night_shift: false,
        timezone: 'Asia/Kolkata',
        is_active: true 
      };
    } else if (this.activeTab === 'locations') {
      // code will be auto-generated by the service layer
      this.formModel = { name: '', code: '', address: '', is_active: true };
    } else if (this.activeTab === 'leaves') {
      this.formModel = { name: '', code: '', max_days: 12, is_active: true };
    } else if (this.activeTab === 'holidays') {
      this.formModel = { name: '', date: new Date().toISOString().slice(0, 10), is_active: true };
    }
    
    this.isModalOpen = true;
    this.cdr.detectChanges();
  }

  openEditModal(item: any): void {
    this.modalMode = 'edit';
    this.selectedItemId = item.id;
    this.formModel = { ...item };
    // Ensure working hours is auto-calculated when editing a shift
    if (this.activeTab === 'shifts') {
      this.autoCalcWorkingHours();
    }
    this.isModalOpen = true;
    this.cdr.detectChanges();
  }

  closeModal(): void {
    this.isModalOpen = false;
  }

  /**
   * Auto-calculates working_hours from start_time and end_time.
   * Handles night shifts (end < start crosses midnight).
   * Also syncs required_work_minutes, minimum_present_minutes,
   * half_day_hours and minimum_half_day_minutes.
   */
  autoCalcWorkingHours(): void {
    const start = this.formModel.start_time as string;
    const end   = this.formModel.end_time   as string;
    if (!start || !end) return;

    const [sh, sm] = start.split(':').map(Number);
    const [eh, em] = end.split(':').map(Number);
    let startMins = sh * 60 + sm;
    let endMins   = eh * 60 + em;

    // Handle night shift (end crosses midnight)
    if (endMins <= startMins) {
      endMins += 24 * 60;
      this.formModel.is_night_shift = true;
    } else {
      this.formModel.is_night_shift = false;
    }

    const totalMins = endMins - startMins;
    const hours = Math.round((totalMins / 60) * 4) / 4; // round to nearest 0.25

    this.formModel.working_hours         = hours;
    this.formModel.required_work_minutes = totalMins;
    this.formModel.minimum_present_minutes = totalMins;

    // Default half day = half of shift
    const halfHours = Math.round((hours / 2) * 4) / 4;
    this.formModel.half_day_hours              = halfHours;
    this.formModel.minimum_half_day_minutes    = Math.round(totalMins / 2);
    this.formModel.present_hours               = hours;

    this.cdr.detectChanges();
  }

  submitForm(): void {
    if (!this.formModel.name && this.activeTab !== 'holidays') {
      this.showToast('Please fill in the required name field.', true);
      return;
    }

    if (this.activeTab === 'holidays' && (!this.formModel.name || !this.formModel.date)) {
      this.showToast('Name and date are required for holidays.', true);
      return;
    }

    this.isDataLoading = true;
    let request$: any;

    if (this.modalMode === 'add') {
      if (this.activeTab === 'departments') {
        request$ = this.masterDataService.createDepartment(this.formModel);
      } else if (this.activeTab === 'designations') {
        request$ = this.masterDataService.createDesignation(this.formModel);
      } else if (this.activeTab === 'shifts') {
        request$ = this.masterDataService.createShift(this.formModel);
      } else if (this.activeTab === 'locations') {
        request$ = this.masterDataService.createWorkLocation(this.formModel);
      } else if (this.activeTab === 'leaves') {
        request$ = this.masterDataService.createLeaveType(this.formModel);
      } else {
        request$ = this.masterDataService.createHoliday(this.formModel);
      }
    } else {
      const id = this.selectedItemId!;
      if (this.activeTab === 'departments') {
        request$ = this.masterDataService.updateDepartment(id, this.formModel);
      } else if (this.activeTab === 'designations') {
        request$ = this.masterDataService.updateDesignation(id, this.formModel);
      } else if (this.activeTab === 'shifts') {
        request$ = this.masterDataService.updateShift(id, this.formModel);
      } else if (this.activeTab === 'locations') {
        request$ = this.masterDataService.updateWorkLocation(id, this.formModel);
      } else if (this.activeTab === 'leaves') {
        request$ = this.masterDataService.updateLeaveType(id, this.formModel);
      } else {
        request$ = this.masterDataService.updateHoliday(id, this.formModel);
      }
    }

    this.subscriptions.add(
      request$.subscribe({
        next: () => {
          this.isModalOpen = false;
          this.loadBootstrapData();
          this.showToast(`Successfully ${this.modalMode === 'add' ? 'created' : 'updated'} record.`);
        },
        error: (err: any) => {
          this.isDataLoading = false;
          this.showToast('Error updating master data: ' + (err.error?.detail || err.message), true);
          this.cdr.detectChanges();
        }
      })
    );
  }
}
