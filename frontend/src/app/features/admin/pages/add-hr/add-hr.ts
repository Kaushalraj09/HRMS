import { ChangeDetectionStrategy, Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BehaviorSubject } from 'rxjs';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';

import { CreateHrPayload } from '../../../../core/models/hr.model';
import { HrService } from '../../../../core/services/hr.service';
import { CustomSelectComponent } from '../../../../shared/components/custom-select/custom-select';

@Component({
  selector: 'app-add-hr',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule, CustomSelectComponent],
  templateUrl: './add-hr.html',
  styleUrl: './add-hr.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AddHrComponent {
  isSubmitting$ = new BehaviorSubject<boolean>(false);
  successMessage$ = new BehaviorSubject<string>('');
  form;

  statusOptions = [
    { label: 'Active', value: 'Active' },
    { label: 'Inactive', value: 'Inactive' }
  ];

  departmentOptions = [
    { label: 'Human Resources', value: 'Human Resources' },
    { label: 'Operations', value: 'Operations' },
    { label: 'People Success', value: 'People Success' }
  ];

  constructor(
    private readonly fb: FormBuilder,
    private readonly hrService: HrService,
    private readonly router: Router
  ) {
    this.form = this.fb.group({
      fullName: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      phone: ['', [Validators.required, Validators.pattern('^[0-9]{10}$')]],
      designation: ['', Validators.required],
      department: ['Human Resources', Validators.required],
      temporaryPassword: ['Hr@12345', [Validators.required, Validators.minLength(8)]],
      status: ['Active', Validators.required]
    });
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const payload = this.form.getRawValue() as CreateHrPayload;

    this.isSubmitting$.next(true);
    this.hrService.createHr(payload).subscribe((result: { success: boolean; message: string }) => {
      this.isSubmitting$.next(false);
      this.successMessage$.next(result.message);
      setTimeout(() => this.router.navigate(['/master-dashboard/hr-users']), 900);
    });
  }

  isInvalid(fieldName: string): boolean {
    const control = this.form.get(fieldName);
    return !!(control && control.invalid && (control.touched || control.dirty));
  }
}
