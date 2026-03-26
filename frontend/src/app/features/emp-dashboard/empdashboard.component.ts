import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

@Component({
  selector: 'app-emp-dashboard',
  standalone: true,
  imports: [CommonModule, MatFormFieldModule, MatSelectModule],
  templateUrl: './empdashboard.component.html',
  styleUrls: ['./empdashboard.component.css'],
})
export class EmpDashboardComponent {
  selectedLang = 'en';
  currentDate: Date = new Date();
  status: string = 'work';

  ngOnInit() {
    setInterval(() => {
      this.currentDate = new Date();
    }, 1000);
  }

  isPunchedIn: boolean = false;

  togglePunch() {
    this.isPunchedIn = !this.isPunchedIn;
  }
}
