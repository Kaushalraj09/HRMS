import { ChangeDetectionStrategy, Component } from '@angular/core';

import { Employees } from '../../../hr/pages/employees/employees';

@Component({
  selector: 'app-admin-employees',
  standalone: true,
  imports: [Employees],
  template: '<app-employees></app-employees>',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AdminEmployeesComponent {}
