import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ManagerService } from '../../../../core/services/manager.service';
import { Employee } from '../../../../core/models/employee.model';
import { ToastService } from '../../../../core/services/toast.service';

@Component({
  selector: 'app-manager-team',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './manager-team.html',
  styleUrls: ['./manager-team.css']
})
export class ManagerTeamComponent implements OnInit {
  teamMembers: Employee[] = [];
  isLoading = true;
  searchQuery = '';
  currentPage = 1;
  pageSize = 10;
  totalItems = 0;
  totalPages = 1;

  // Detail Modal
  selectedEmployee: Employee | null = null;
  isDetailModalOpen = false;

  constructor(
    private readonly managerService: ManagerService,
    private readonly toastService: ToastService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadTeam();
  }

  loadTeam(): void {
    this.isLoading = true;
    this.managerService.getTeam(this.currentPage, this.pageSize, this.searchQuery).subscribe({
      next: res => {
        this.teamMembers = res.data || res.items || [];
        this.totalItems = res.total;
        this.totalPages = Math.ceil(this.totalItems / this.pageSize) || 1;
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: err => {
        this.isLoading = false;
        this.toastService.showError(err?.error?.detail || 'Failed to load team members');
        this.cdr.markForCheck();
      }
    });
  }

  onSearch(): void {
    this.currentPage = 1;
    this.loadTeam();
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
      this.loadTeam();
    }
  }

  viewDetails(member: Employee): void {
    this.selectedEmployee = member;
    this.isDetailModalOpen = true;
  }

  closeDetailModal(): void {
    this.isDetailModalOpen = false;
    this.selectedEmployee = null;
  }
}
