import { Component, EventEmitter, Input, OnInit, Output, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { Observable } from 'rxjs';
import { EmployeeService } from '../../../../../../core/services/employee.service';
import { DocumentService } from '../../../../../../core/services/document.service';
import { EmployeeDetailView } from '../../../../../../core/models/employee.model';
import {
  EmployeeDocumentsPageResponse,
  EmployeeDocumentItem,
  DocumentVersion
} from '../../../../../../core/models/document.model';

@Component({
  selector: 'app-employee-view-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './employee-view-modal.html',
  styleUrls: ['./employee-view-modal.css']
})
export class EmployeeViewModalComponent implements OnInit {
  @Input() employeeId!: string;
  @Input() initialTab: 'details' | 'documents' = 'details';
  @Output() closed = new EventEmitter<void>();
  employeeDetail$!: Observable<EmployeeDetailView | null>;

  activeTab: 'details' | 'documents' = 'details';

  // Documents tab state
  docData: EmployeeDocumentsPageResponse | null = null;
  isLoadingDocs = false;
  docsError = '';
  docsSuccess = '';

  // HR Upload Modal state
  isHrUploadOpen = false;
  selectedDocTypeForUpload: EmployeeDocumentItem | null = null;
  uploadFile: File | null = null;
  uploadRemarks = '';
  isUploading = false;
  uploadError = '';

  // Verify Modal
  isVerifyOpen = false;
  selectedDocForVerify: EmployeeDocumentItem | null = null;
  verifyRemarks = '';
  isVerifying = false;

  // Reject Modal
  isRejectOpen = false;
  selectedDocForReject: EmployeeDocumentItem | null = null;
  rejectionReason = '';
  rejectRemarks = '';
  isRejecting = false;
  rejectionError = '';

  // Preview Modal
  isPreviewOpen = false;
  previewTitle = '';
  previewBlobUrl: SafeResourceUrl | null = null;
  rawBlobUrl: string | null = null;
  previewMimeType = '';
  isPreviewLoading = false;

  // History Modal
  isHistoryOpen = false;
  historyTitle = '';
  versionHistory: DocumentVersion[] = [];
  isHistoryLoading = false;

  constructor(
    private readonly employeeService: EmployeeService,
    private readonly documentService: DocumentService,
    private readonly sanitizer: DomSanitizer,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    if (this.initialTab) {
      this.activeTab = this.initialTab;
    }
    if (this.employeeId) {
      this.employeeDetail$ = this.employeeService.getEmployeeById(this.employeeId);
      if (this.activeTab === 'documents') {
        this.loadDocuments();
      }
    } else {
      console.warn('EmployeeViewModal: No employeeId provided');
    }
  }

  setTab(tab: 'details' | 'documents'): void {
    this.activeTab = tab;
    if (tab === 'documents' && !this.docData) {
      this.loadDocuments();
    }
  }

  loadDocuments(): void {
    if (!this.employeeId) return;
    this.isLoadingDocs = true;
    this.docsError = '';

    this.documentService.getEmployeeDocumentsForHr(this.employeeId).subscribe({
      next: (res) => {
        this.docData = res;
        this.isLoadingDocs = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.docsError = err?.error?.detail || 'Failed to load employee documents';
        this.isLoadingDocs = false;
        this.cdr.markForCheck();
      }
    });
  }

  toggleRequirement(item: EmployeeDocumentItem): void {
    const newRequired = !item.is_required;
    item.is_required = newRequired;

    this.documentService.updateEmployeeRequirement(
      this.employeeId,
      item.document_type_id,
      newRequired
    ).subscribe({
      next: () => {
        this.loadDocuments();
      },
      error: (err) => {
        item.is_required = !newRequired; // rollback
        alert('Failed to update requirement: ' + (err?.error?.detail || 'Error'));
      }
    });
  }

  // ─── HR Upload on behalf of employee ────────────────────────────────────────

  openHrUpload(item: EmployeeDocumentItem): void {
    this.selectedDocTypeForUpload = item;
    this.uploadFile = null;
    this.uploadRemarks = '';
    this.uploadError = '';
    this.isHrUploadOpen = true;
  }

  closeHrUpload(): void {
    this.isHrUploadOpen = false;
    this.selectedDocTypeForUpload = null;
    this.uploadFile = null;
  }

  onFilePicked(event: any): void {
    const file: File = event.target?.files?.[0];
    if (file) {
      this.uploadFile = file;
      this.uploadError = '';
    }
  }

  submitHrUpload(): void {
    if (!this.selectedDocTypeForUpload || !this.uploadFile || this.isUploading) return;

    this.isUploading = true;
    this.uploadError = '';

    this.documentService.hrUploadDocument(
      this.employeeId,
      this.selectedDocTypeForUpload.document_type_id,
      this.uploadFile,
      this.uploadRemarks
    ).subscribe({
      next: () => {
        this.isUploading = false;
        this.closeHrUpload();
        this.showDocsToast('Document uploaded successfully on behalf of employee.');
        this.loadDocuments();
      },
      error: (err) => {
        this.isUploading = false;
        this.uploadError = err?.error?.detail || 'Failed to upload document';
        this.cdr.markForCheck();
      }
    });
  }

  // ─── Verify & Reject ─────────────────────────────────────────────────────────

  openVerify(item: EmployeeDocumentItem): void {
    this.selectedDocForVerify = item;
    this.verifyRemarks = '';
    this.isVerifyOpen = true;
  }

  closeVerify(): void {
    this.isVerifyOpen = false;
    this.selectedDocForVerify = null;
  }

  submitVerify(): void {
    if (!this.selectedDocForVerify || !this.selectedDocForVerify.document_id || this.isVerifying) return;

    this.isVerifying = true;
    this.documentService.verifyDocument(
      this.selectedDocForVerify.document_id,
      this.verifyRemarks
    ).subscribe({
      next: () => {
        this.isVerifying = false;
        this.closeVerify();
        this.showDocsToast('Document verified successfully.');
        this.loadDocuments();
      },
      error: (err) => {
        this.isVerifying = false;
        alert(err?.error?.detail || 'Failed to verify');
      }
    });
  }

  openReject(item: EmployeeDocumentItem): void {
    this.selectedDocForReject = item;
    this.rejectionReason = '';
    this.rejectRemarks = '';
    this.rejectionError = '';
    this.isRejectOpen = true;
  }

  closeReject(): void {
    this.isRejectOpen = false;
    this.selectedDocForReject = null;
  }

  submitReject(): void {
    if (!this.selectedDocForReject || !this.selectedDocForReject.document_id || this.isRejecting) return;

    if (!this.rejectionReason.trim()) {
      this.rejectionError = 'Rejection reason is required.';
      return;
    }

    this.isRejecting = true;
    this.rejectionError = '';

    this.documentService.rejectDocument(
      this.selectedDocForReject.document_id,
      this.rejectionReason,
      this.rejectRemarks
    ).subscribe({
      next: () => {
        this.isRejecting = false;
        this.closeReject();
        this.showDocsToast('Document rejected.');
        this.loadDocuments();
      },
      error: (err) => {
        this.isRejecting = false;
        this.rejectionError = err?.error?.detail || 'Failed to reject';
        this.cdr.markForCheck();
      }
    });
  }

  // ─── Preview & Download ──────────────────────────────────────────────────────

  openPreview(item: EmployeeDocumentItem): void {
    if (!item.document_id) return;
    this.cleanupBlobs();
    this.previewTitle = `${item.document_type_name} (${item.file_name || 'Document'})`;
    this.isPreviewLoading = true;
    this.isPreviewOpen = true;

    this.documentService.previewDocument(item.document_id).subscribe({
      next: (blob) => {
        this.rawBlobUrl = URL.createObjectURL(blob);
        this.previewMimeType = blob.type || item.mime_type || 'application/pdf';
        this.previewBlobUrl = this.sanitizer.bypassSecurityTrustResourceUrl(this.rawBlobUrl);
        this.isPreviewLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.isPreviewLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  closePreview(): void {
    this.isPreviewOpen = false;
    this.cleanupBlobs();
  }

  downloadDoc(item: EmployeeDocumentItem): void {
    if (!item.document_id) return;
    this.documentService.downloadDocument(item.document_id).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = item.file_name || 'document.pdf';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    });
  }

  openHistory(item: EmployeeDocumentItem): void {
    if (!item.document_id) return;
    this.historyTitle = item.document_type_name;
    this.versionHistory = [];
    this.isHistoryLoading = true;
    this.isHistoryOpen = true;

    this.documentService.getDocumentHistory(item.document_id).subscribe({
      next: (h) => {
        this.versionHistory = h || [];
        this.isHistoryLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.isHistoryLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  closeHistory(): void {
    this.isHistoryOpen = false;
  }

  downloadVersion(v: DocumentVersion): void {
    const obs = (v.is_current && v.document_id)
      ? this.documentService.downloadDocument(v.document_id)
      : this.documentService.downloadVersion(v.version_id || v.id);

    obs.subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = v.file_name || `version_${v.version_number}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }

    });
  }

  private cleanupBlobs(): void {
    if (this.rawBlobUrl) {
      URL.revokeObjectURL(this.rawBlobUrl);
      this.rawBlobUrl = null;
      this.previewBlobUrl = null;
    }
  }

  showDocsToast(msg: string): void {
    this.docsSuccess = msg;
    setTimeout(() => {
      this.docsSuccess = '';
      this.cdr.markForCheck();
    }, 4000);
  }

  formatSize(b?: number | null): string {
    return this.documentService.formatFileSize(b);
  }

  formatDate(d?: string | null): string {
    if (!d) return '-';
    try {
      const dt = new Date(d);
      return isNaN(dt.getTime()) ? d : dt.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return d;
    }
  }

  getStatusBadgeClass(status: string): string {
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
      case 'RESUBMISSION_REQUIRED': return 'Re-upload Req';
      default: return 'Not Uploaded';
    }
  }

  isImageMime(mime?: string | null): boolean {
    return !!mime && (mime.startsWith('image/') || mime.includes('png') || mime.includes('jpeg') || mime.includes('jpg'));
  }

  close(): void {
    this.closed.emit();
  }
}
