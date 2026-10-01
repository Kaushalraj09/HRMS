import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-dashboard-alert-bar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard-alert-bar.html',
  styleUrls: ['./dashboard-alert-bar.css']
})
export class DashboardAlertBarComponent {
  @Input() pendingLeaves: number = 3;
  @Input() overdueTasks: number = 7;
  @Input() compliancePct: string = '87%';

  @Output() viewDetailsClick = new EventEmitter<void>();

  onViewDetails(): void {
    this.viewDetailsClick.emit();
  }
}
