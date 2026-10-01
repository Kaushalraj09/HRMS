import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-dashboard-kpi-card',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard-kpi-card.html',
  styleUrls: ['./dashboard-kpi-card.css']
})
export class DashboardKpiCardComponent {
  @Input() title: string = '';
  @Input() value: string | number = '0';
  @Input() subtitle: string = '';
  @Input() icon: string = 'fas fa-info';
  @Input() colorTheme: 'blue' | 'green' | 'amber' | 'red' | 'orange' | 'indigo' | 'sky' | 'teal' = 'blue';
  @Input() route?: string;
  @Input() clickable: boolean = true;
}
