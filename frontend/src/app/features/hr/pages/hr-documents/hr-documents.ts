import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { Subscription } from 'rxjs';
import { DocumentService } from '../../../../core/services/document.service';
import {
  HrDocumentOverviewKPI,
  HrPendingReviewItem,
  DocumentVersion,
  EmployeeDocumentsPageResponse
} from '../../../../core/models/document.model';

@Component({
  selector: 'app-hr-documents',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './hr-documents.html',
  styleUrls: ['./hr-documents.css']
})
export class HrDocumentsComponent implements OnInit, OnDestroy {
  isLoadingKpi = true;
  isLoadingTable = true;
  errorMessage = '';
  successMessage = '';

  // KPI Overview Data
  kpiData: HrDocumentOverviewKPI = {
    total_employees: 0,
    documents_pending: 0,
    documents_verified: 0,
    documents_rejected: 0,
    incomplete_employees: 0,
    complete_employees: 0,
    overall_compliance_rate: 0,
    categories_breakdown: []
  };

  // Table Data & Filters
  pendingReviews: HrPendingReviewItem[] = [];
  totalItems = 0;
  currentPage = 1;
  pageSize = 10;
  searchQuery = '';
  selectedDepartment = '';
  selectedStatus = '';

  // Departments for filter
  departments: string[] = ['All', 'Engineering', 'Human Resources', 'Design', 'Marketing', 'Sales', 'Finance', 'Operations'];

  // Verify Modal State
  isVerifyModalOpen = false;
  selectedDocForVerify: HrPendingReviewItem | null = null;
  verifyRemarks = '';
  isVerifying = false;

  // Reject Modal State
  isRejectModalOpen = false;
  selectedDocForReject: HrPendingReviewItem | null = null;
  rejectionReason = '';
  rejectRemarks = '';
  isRejecting = false;
  rejectionError = '';

  // Quick rejection templates for HR efficiency
  quickReasons: string[] = [
    'Document image is blurry or illegible',
    'Document has expired or validity date is unclear',
    'Incorrect document type submitted',
    'Missing authorized signature or official stamp',
    'Both front and back sides are required',
    'Name or details do not match employee profile'
  ];

  // Preview Modal State
  isPreviewModalOpen = false;
  previewDocTitle = '';
  previewBlobUrl: SafeResourceUrl | null = null;
  rawBlobUrl: string | null = null;
  previewMimeType = '';
  isPreviewLoading = false;
  activePreviewDocId: number | null = null;

  // History Modal State
  isHistoryModalOpen = false;
  historyDocTitle = '';
  versionHistory: DocumentVersion[] = [];
  isHistoryLoading = false;

  private readonly subscriptions = new Subscription();

  constructor(
    private readonly documentService: DocumentService,
    private readonly sanitizer: DomSanitizer,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadKpiOverview();
    this.loadPendingReviews();

    this.subscriptions.add(
      this.documentService.documentUpdated$.subscribe(() => {
        this.loadKpiOverview();
        this.loadPendingReviews(false);
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
    this.cleanupBlobUrls();
  }

  loadKpiOverview(): void {
    this.isLoadingKpi = true;
    this.documentService.getHrOverview().subscribe({
      next: (kpi) => {
        this.kpiData = kpi;
        this.isLoadingKpi = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to load HR KPI overview:', err);
        this.isLoadingKpi = false;
        this.cdr.markForCheck();
      }
    });
  }

  loadPendingReviews(showSpinner: boolean = true): void {
    if (showSpinner) {
      this.isLoadingTable = true;
    }
    this.errorMessage = '';

    const dept = this.selectedDepartment === 'All' ? '' : this.selectedDepartment;

    this.documentService.getHrPendingReviews(
      this.currentPage,
      this.pageSize,
      this.searchQuery,
      dept,
      this.selectedStatus
    ).subscribe({
      next: (res) => {
        this.pendingReviews = res.data || [];
        this.totalItems = res.total || 0;
        this.isLoadingTable = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to load pending reviews:', err);
        this.errorMessage = err?.error?.detail || 'Failed to load document reviews';
        this.isLoadingTable = false;
        this.cdr.markForCheck();
      }
    });
  }

  onSearchChange(): void {
    this.currentPage = 1;
    this.loadPendingReviews(false);
  }

  clearSearch(): void {
    this.searchQuery = '';
    this.currentPage = 1;
    this.loadPendingReviews(false);
  }

  onDepartmentChange(): void {
    this.currentPage = 1;
    this.loadPendingReviews(false);
  }

  onStatusFilterChange(status: string): void {
    this.selectedStatus = status;
    this.currentPage = 1;
    this.loadPendingReviews(false);
  }

  resetFilters(): void {
    this.searchQuery = '';
    this.selectedDepartment = 'All';
    this.selectedStatus = '';
    this.currentPage = 1;
    this.loadPendingReviews();
  }

  setQuickRejectionReason(reason: string): void {
    this.rejectionReason = reason;
    this.rejectionError = '';
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
      this.loadPendingReviews();
    }
  }

  get totalPages(): number {
    return Math.ceil(this.totalItems / this.pageSize) || 1;
  }

  // ─── Verification Flow ───────────────────────────────────────────────────────

  openVerifyModal(doc: HrPendingReviewItem): void {
    this.selectedDocForVerify = doc;
    this.verifyRemarks = '';
    this.isVerifyModalOpen = true;
  }

  closeVerifyModal(): void {
    this.isVerifyModalOpen = false;
    this.selectedDocForVerify = null;
    this.verifyRemarks = '';
  }

  submitVerify(): void {
    if (!this.selectedDocForVerify || this.isVerifying) return;

    this.isVerifying = true;
    this.documentService.verifyDocument(
      this.selectedDocForVerify.id,
      this.verifyRemarks
    ).subscribe({
      next: () => {
        this.isVerifying = false;
        this.closeVerifyModal();
        this.showToast('Document verified successfully!');
        this.loadKpiOverview();
        this.loadPendingReviews(false);
      },
      error: (err) => {
        this.isVerifying = false;
        alert(err?.error?.detail || 'Failed to verify document.');
      }
    });
  }

  // ─── Rejection Flow ─────────────────────────────────────────────────────────

  openRejectModal(doc: HrPendingReviewItem): void {
    this.selectedDocForReject = doc;
    this.rejectionReason = '';
    this.rejectRemarks = '';
    this.rejectionError = '';
    this.isRejectModalOpen = true;
  }

  closeRejectModal(): void {
    this.isRejectModalOpen = false;
    this.selectedDocForReject = null;
    this.rejectionReason = '';
    this.rejectionError = '';
  }

  submitReject(): void {
    if (!this.selectedDocForReject || this.isRejecting) return;

    if (!this.rejectionReason.trim()) {
      this.rejectionError = 'Please provide a clear reason for rejecting the document.';
      return;
    }

    this.isRejecting = true;
    this.rejectionError = '';

    this.documentService.rejectDocument(
      this.selectedDocForReject.id,
      this.rejectionReason,
      this.rejectRemarks
    ).subscribe({
      next: () => {
        this.isRejecting = false;
        this.closeRejectModal();
        this.showToast('Document rejected. Re-upload request sent to employee.');
        this.loadKpiOverview();
        this.loadPendingReviews(false);
      },
      error: (err) => {
        this.isRejecting = false;
        this.rejectionError = err?.error?.detail || 'Failed to reject document.';
        this.cdr.markForCheck();
      }
    });
  }

  // ─── Preview & Download Flow ─────────────────────────────────────────────────

  openPreview(doc: HrPendingReviewItem): void {
    this.cleanupBlobUrls();
    this.activePreviewDocId = doc.id;
    this.previewDocTitle = `${doc.employee_name} — ${doc.document_type_name}`;
    this.isPreviewLoading = true;
    this.isPreviewModalOpen = true;

    this.documentService.previewDocument(doc.id).subscribe({
      next: (blob) => {
        this.rawBlobUrl = URL.createObjectURL(blob);
        this.previewMimeType = blob.type || doc.mime_type || 'application/pdf';
        this.previewBlobUrl = this.sanitizer.bypassSecurityTrustResourceUrl(this.rawBlobUrl);
        this.isPreviewLoading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to preview document:', err);
        this.isPreviewLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  closePreviewModal(): void {
    this.isPreviewModalOpen = false;
    this.cleanupBlobUrls();
    this.activePreviewDocId = null;
  }

  downloadDoc(doc: HrPendingReviewItem): void {
    this.documentService.downloadDocument(doc.id).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = doc.file_name || `${doc.document_type_name.toLowerCase()}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      },
      error: (err) => {
        console.error('Failed to download document:', err);
        alert('Failed to download document.');
      }
    });
  }

  // ─── History Flow ───────────────────────────────────────────────────────────

  openHistory(doc: HrPendingReviewItem): void {
    this.historyDocTitle = `${doc.employee_name} — ${doc.document_type_name}`;
    this.versionHistory = [];
    this.isHistoryLoading = true;
    this.isHistoryModalOpen = true;

    this.documentService.getDocumentHistory(doc.id).subscribe({
      next: (history) => {
        this.versionHistory = history || [];
        this.isHistoryLoading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to load version history:', err);
        this.isHistoryLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  closeHistoryModal(): void {
    this.isHistoryModalOpen = false;
    this.versionHistory = [];
  }

  downloadVersion(v: DocumentVersion): void {
    this.documentService.downloadVersion(v.id).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = v.file_name || `version_${v.version_number}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      },
      error: (err) => {
        console.error('Failed to download version:', err);
        alert('Failed to download version.');
      }
    });
  }

  private cleanupBlobUrls(): void {
    if (this.rawBlobUrl) {
      URL.revokeObjectURL(this.rawBlobUrl);
      this.rawBlobUrl = null;
      this.previewBlobUrl = null;
    }
  }

  showToast(msg: string): void {
    this.successMessage = msg;
    setTimeout(() => {
      this.successMessage = '';
      this.cdr.markForCheck();
    }, 4000);
  }

  // ─── Helpers ────────────────────────────────────────────────────────────────

  formatSize(bytes?: number | null): string {
    return this.documentService.formatFileSize(bytes);
  }

  formatDate(dateStr?: string | null): string {
    if (!dateStr) return '-';
    try {
      const d = new Date(dateStr);
      return isNaN(d.getTime()) ? dateStr : d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return dateStr;
    }
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'VERIFIED': return 'status-verified';
      case 'PENDING_REVIEW': return 'status-pending';
      case 'REJECTED':
      case 'RESUBMISSION_REQUIRED': return 'status-rejected';
      default: return 'status-missing';
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'VERIFIED': return 'Verified';
      case 'PENDING_REVIEW': return 'Pending Review';
      case 'REJECTED': return 'Rejected';
      case 'RESUBMISSION_REQUIRED': return 'Re-upload Required';
      default: return status;
    }
  }

  isImageMime(mime?: string | null): boolean {
    return !!mime && (mime.startsWith('image/') || mime.includes('png') || mime.includes('jpeg') || mime.includes('jpg'));
  }
}
