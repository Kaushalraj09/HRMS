import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-quick-actions',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './quick-actions.html',
  styleUrls: ['./quick-actions.css']
})
export class QuickActionsComponent {
  @Input() attendanceRoute = '/emp-dashboard/team-attendance';
  @Input() timeOffRoute = '/emp-dashboard/leave-approvals';
  @Output() actionClick = new EventEmitter<string>();

  onAction(actionType: string): void {
    this.actionClick.emit(actionType);
  }
}
