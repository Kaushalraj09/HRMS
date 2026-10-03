import '@angular/compiler';
import { describe, it, expect, vi } from 'vitest';
import { FormBuilder } from '@angular/forms';
import { ChangeDetectorRef } from '@angular/core';
import { of } from 'rxjs';
import { EmployeeAddModalComponent } from './employee-add-modal';
import { EmployeeService } from '../../../../../../core/services/employee.service';
import { MasterDataService } from '../../../../../../core/services/master-data.service';

describe('EmployeeAddModalComponent - Role & Reporting Manager Validation', () => {
  function createComponent(): EmployeeAddModalComponent {
    const fb = new FormBuilder();
    const mockEmployeeService = {
      getAllManagers: vi.fn().mockReturnValue(of([])),
      getNextEmployeeCode: vi.fn().mockReturnValue(of({ nextCode: 'AIVAN001' })),
      createEmployee: vi.fn().mockReturnValue(of({ message: 'Success' }))
    } as unknown as EmployeeService;

    const mockMasterDataService = {
      getBootstrapData: vi.fn().mockReturnValue(of({ departments: [], designations: [], workLocations: [], shifts: [] }))
    } as unknown as MasterDataService;

    const mockCdr = {
      markForCheck: vi.fn()
    } as unknown as ChangeDetectorRef;

    return new EmployeeAddModalComponent(fb, mockEmployeeService, mockMasterDataService, mockCdr);
  }

  it('should initialize with employee role requiring reportingManagerId', () => {
    const component = createComponent();
    expect(component.form.get('accountAccess.role')?.value).toBe('employee');
    expect(component.isReportingManagerRequired).toBe(true);

    const mgrCtrl = component.form.get('employmentInfo.reportingManagerId');
    expect(mgrCtrl).toBeDefined();
    expect(mgrCtrl?.validator).toBeDefined();

    // With null value, control must be invalid
    mgrCtrl?.setValue(null);
    expect(mgrCtrl?.valid).toBe(false);

    // With a manager selected, control must be valid
    mgrCtrl?.setValue(2);
    expect(mgrCtrl?.valid).toBe(true);
  });

  it('should clear reportingManagerId validation when role is changed to manager', () => {
    const component = createComponent();
    const roleCtrl = component.form.get('accountAccess.role');
    const mgrCtrl = component.form.get('employmentInfo.reportingManagerId');

    roleCtrl?.setValue('manager');
    expect(component.isReportingManagerRequired).toBe(false);

    // Without manager selected, it should now be valid
    mgrCtrl?.setValue(null);
    expect(mgrCtrl?.valid).toBe(true);
  });

  it('should clear reportingManagerId validation when role is changed to hr', () => {
    const component = createComponent();
    const roleCtrl = component.form.get('accountAccess.role');
    const mgrCtrl = component.form.get('employmentInfo.reportingManagerId');

    roleCtrl?.setValue('hr');
    expect(component.isReportingManagerRequired).toBe(false);

    mgrCtrl?.setValue(null);
    expect(mgrCtrl?.valid).toBe(true);
  });

  it('should re-enable reportingManagerId validation when role switches back to employee', () => {
    const component = createComponent();
    const roleCtrl = component.form.get('accountAccess.role');
    const mgrCtrl = component.form.get('employmentInfo.reportingManagerId');

    roleCtrl?.setValue('manager');
    expect(component.isReportingManagerRequired).toBe(false);
    expect(mgrCtrl?.valid).toBe(true);

    roleCtrl?.setValue('employee');
    expect(component.isReportingManagerRequired).toBe(true);
    mgrCtrl?.setValue(null);
    expect(mgrCtrl?.valid).toBe(false);
  });
});
