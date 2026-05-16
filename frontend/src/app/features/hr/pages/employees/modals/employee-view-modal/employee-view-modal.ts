import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { EmployeeService } from '../../../../../../core/services/employee.service';
import { EmployeeDetailView } from '../../../../../../core/models/employee.model';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-employee-view-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './employee-view-modal.html',
  styleUrls: ['./employee-view-modal.css']
})
export class EmployeeViewModalComponent implements OnInit {
  @Input() employeeId!: string;
  @Output() closed = new EventEmitter<void>();
  employeeDetail$!: Observable<EmployeeDetailView | null>;

  constructor(private employeeService: EmployeeService) {}

  ngOnInit(): void {
    if (this.employeeId) {
      this.employeeDetail$ = this.employeeService.getEmployeeById(this.employeeId);
    } else {
      console.warn('EmployeeViewModal: No employeeId provided');
    }
  }

  close(): void {
    this.closed.emit();
  }
}
