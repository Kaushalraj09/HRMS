import { Component, OnInit, ChangeDetectorRef, NgZone } from '@angular/core';
import { CommonModule, Location } from '@angular/common';
import { ActivatedRoute, RouterModule, Router } from '@angular/router';
import { TrainingService } from '../../../../core/services/training.service';
import { ToastService } from '../../../../core/services/toast.service';
import { EmployeeTrainingView, TrainingMaterial } from '../../../../core/models/training.model';

@Component({
  selector: 'app-training-view',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './training-view.html',
  styleUrls: ['./training-view.css']
})
export class TrainingViewComponent implements OnInit {
  trainingId!: number;
  data: EmployeeTrainingView | null = null;
  selectedMaterial: TrainingMaterial | null = null;
  isLoading = true;

  // In-App Toast Popup State
  toast = {
    show: false,
    message: '',
    type: 'success' as 'success' | 'error' | 'info',
    timeout: null as any
  };

  showToast(message: string, type: 'success' | 'error' | 'info' = 'success', duration = 5000): void {
    this.toastService.show(type, message, { duration });
  }

  closeToast(): void {}

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private location: Location,
    private trainingService: TrainingService,
    private cdr: ChangeDetectorRef,
    private ngZone: NgZone,
    private toastService: ToastService
  ) {}

  goBack(): void {
    this.location.back();
  }

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      this.trainingId = +idParam;
      this.loadDetail();
    }
  }

  loadDetail(): void {
    this.isLoading = true;
    this.cdr.detectChanges();
    this.trainingService.getMyTrainingDetail(this.trainingId).subscribe({
      next: (res) => {
        this.ngZone.run(() => {
          this.data = res;
          if (res.materials && res.materials.length > 0) {
            const firstIncomplete = res.materials.find((m) => !m.is_completed);
            this.selectedMaterial = firstIncomplete || res.materials[0];
          }
          this.isLoading = false;
          this.cdr.detectChanges();
        });
      },
      error: (err) => {
        this.ngZone.run(() => {
          this.showToast('Failed to load training details: ' + (err.error?.detail || err.message), 'error');
          this.isLoading = false;
          this.cdr.detectChanges();
        });
      }
    });
  }

  selectMaterial(mat: TrainingMaterial): void {
    this.selectedMaterial = mat;
    this.cdr.detectChanges();
  }

  markMaterialCompleted(mat: TrainingMaterial): void {
    this.trainingService.recordMaterialProgress(this.trainingId, mat.id, 100, true).subscribe({
      next: () => {
        this.ngZone.run(() => {
          mat.is_completed = true;
          this.showToast('Material marked as completed!', 'success');
          this.loadDetail();
        });
      },
      error: (err) => {
        this.ngZone.run(() => {
          this.showToast('Failed to record progress: ' + (err.error?.detail || err.message), 'error');
        });
      }
    });
  }

  getMaterialUrl(mat: TrainingMaterial | null): string {
    if (!mat) return '';
    return this.trainingService.getDownloadUrl(this.trainingId, mat.id);
  }

  startAssessment(): void {
    if (!this.data?.assessment?.id) return;
    this.router.navigate(['/emp-dashboard/assessment', this.data.assessment.id]);
  }

  getMaterialIcon(mat: TrainingMaterial | any): string {
    if (!mat) return 'fas fa-file-alt';
    const type = (mat.file_type || '').toLowerCase();
    const name = (mat.file_name || '').toLowerCase();
    if (type === 'video' || name.endsWith('.mp4') || name.endsWith('.mov') || name.endsWith('.webm')) {
      return 'fas fa-video';
    }
    if (type === 'audio' || name.endsWith('.mp3') || name.endsWith('.wav') || name.endsWith('.ogg')) {
      return 'fas fa-volume-up';
    }
    if (type === 'image' || name.endsWith('.jpg') || name.endsWith('.jpeg') || name.endsWith('.png') || name.endsWith('.webp') || name.endsWith('.svg')) {
      return 'fas fa-image';
    }
    if (name.endsWith('.pdf')) {
      return 'fas fa-file-pdf';
    }
    if (name.endsWith('.doc') || name.endsWith('.docx')) {
      return 'fas fa-file-word';
    }
    if (name.endsWith('.xls') || name.endsWith('.xlsx')) {
      return 'fas fa-file-excel';
    }
    if (name.endsWith('.ppt') || name.endsWith('.pptx')) {
      return 'fas fa-file-powerpoint';
    }
    return 'fas fa-file-alt';
  }
}
