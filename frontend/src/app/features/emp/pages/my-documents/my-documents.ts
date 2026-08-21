import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { Subscription } from 'rxjs';
import { DocumentService } from '../../../../core/services/document.service';
import {
  EmployeeDocumentItem,
  DocumentSummaryStats,
  EmployeeDocumentsPageResponse,
  DocumentVersion
} from '../../../../core/models/document.model';

@Component({
  selector: 'app-my-documents',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './my-documents.html',
  styleUrls: ['./my-documents.css']
})
export class MyDocumentsComponent implements OnInit, OnDestroy {
  isLoading = true;
  errorMessage = '';
  successMessage = '';

  employeeId: number = 0;
  employeeName: string = '';
  employeeCode: string = '';
  department: string = '';
  designation: string = '';

  summary: DocumentSummaryStats = {
    total_required: 0,
    total_optional: 0,
    uploaded: 0,
    pending_review: 0,
    verified: 0,
    rejected: 0,
    missing: 0,
    completion_percentage: 0
  };

  allDocuments: EmployeeDocumentItem[] = [];
  filteredDocuments: EmployeeDocumentItem[] = [];

  // Filter and search state
  searchQuery = '';
  selectedCategory = 'ALL';
  selectedStatusFilter = 'ALL';
  categories: string[] = ['ALL'];

  // Upload Modal State
  isUploadModalOpen = false;
  selectedDocForUpload: EmployeeDocumentItem | null = null;
  selectedFile: File | null = null;
  filePreviewUrl: string | null = null;
  fileError = '';
  uploadRemarks = '';
  isUploading = false;
  isDragOver = false;

  // Document Preview Modal State
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
    this.loadDocuments();

    this.subscriptions.add(
      this.documentService.documentUpdated$.subscribe(() => {
        this.loadDocuments(false);
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
    this.cleanupBlobUrls();
  }

  loadDocuments(showSpinner: boolean = true): void {
    if (showSpinner) {
      this.isLoading = true;
    }
    this.errorMessage = '';

    this.documentService.getMyDocuments().subscribe({
      next: (res: EmployeeDocumentsPageResponse) => {
        this.employeeId = res.employee_id;
        this.employeeName = res.employee_name;
        this.employeeCode = res.employee_code;
        this.department = res.department || '';
        this.designation = res.designation || '';
        this.summary = res.summary;
        this.allDocuments = res.documents || [];

        // Extract unique categories
        const catSet = new Set<string>();
        catSet.add('ALL');
        this.allDocuments.forEach(d => {
          if (d.category) catSet.add(d.category);
        });
        this.categories = Array.from(catSet);

        this.applyFilters();
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to load employee documents:', err);
        this.errorMessage = err?.error?.detail || 'Unable to load your documents. Please try again.';
        this.isLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  applyFilters(): void {
    let result = [...this.allDocuments];

    // Search query filter
    if (this.searchQuery.trim()) {
      const q = this.searchQuery.trim().toLowerCase();
      result = result.filter(d =>
        d.document_type_name.toLowerCase().includes(q) ||
        (d.description && d.description.toLowerCase().includes(q)) ||
        d.category.toLowerCase().includes(q) ||
        (d.file_name && d.file_name.toLowerCase().includes(q))
      );
    }

    // Category filter
    if (this.selectedCategory !== 'ALL') {
      result = result.filter(d => d.category === this.selectedCategory);
    }

    // Status filter
    if (this.selectedStatusFilter !== 'ALL') {
      if (this.selectedStatusFilter === 'MISSING') {
        result = result.filter(d => d.status === 'NOT_UPLOADED' || d.status === 'REJECTED' || d.status === 'RESUBMISSION_REQUIRED');
      } else {
        result = result.filter(d => d.status === this.selectedStatusFilter);
      }
    }

    this.filteredDocuments = result;
  }

  onSearchChange(): void {
    this.applyFilters();
  }

  setCategory(cat: string): void {
    this.selectedCategory = cat;
    this.applyFilters();
  }

  setStatusFilter(status: string): void {
    this.selectedStatusFilter = status;
    this.applyFilters();
  }

  // ─── Upload Flow ─────────────────────────────────────────────────────────────

  openUploadModal(doc: EmployeeDocumentItem): void {
    this.selectedDocForUpload = doc;
    this.selectedFile = null;
    this.filePreviewUrl = null;
    this.fileError = '';
    this.uploadRemarks = '';
    this.isUploadModalOpen = true;
  }

  closeUploadModal(): void {
    this.isUploadModalOpen = false;
    this.selectedDocForUpload = null;
    this.selectedFile = null;
    this.filePreviewUrl = null;
    this.fileError = '';
  }

  onFileSelected(event: any): void {
    const file: File = event.target?.files?.[0];
    if (file) {
      this.validateAndSetFile(file);
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
    const file = event.dataTransfer?.files?.[0];
    if (file) {
      this.validateAndSetFile(file);
    }
  }

  validateAndSetFile(file: File): void {
    this.fileError = '';
    if (!this.selectedDocForUpload) return;

    const doc = this.selectedDocForUpload;
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    const allowed = doc.allowed_file_types.split(',').map(e => e.trim().toLowerCase());

    if (!allowed.includes(ext)) {
      this.fileError = `Invalid file format (.${ext}). Allowed formats: ${doc.allowed_file_types.toUpperCase()}`;
      return;
    }

    const maxBytes = doc.max_file_size_mb * 1024 * 1024;
    if (file.size > maxBytes) {
      this.fileError = `File exceeds maximum allowed size of ${doc.max_file_size_mb} MB.`;
      return;
    }

    this.selectedFile = file;

    // Create local image preview if applicable
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e: any) => {
        this.filePreviewUrl = e.target.result;
        this.cdr.markForCheck();
      };
      reader.readAsDataURL(file);
    } else {
      this.filePreviewUrl = null;
    }
  }

  submitUpload(): void {
    if (!this.selectedDocForUpload || !this.selectedFile || this.isUploading) {
      return;
    }

    this.isUploading = true;
    this.fileError = '';

    this.documentService.uploadMyDocument(
      this.selectedDocForUpload.document_type_id,
      this.selectedFile,
      this.uploadRemarks
    ).subscribe({
      next: (res) => {
        this.isUploading = false;
        this.closeUploadModal();
        this.successMessage = 'Document uploaded successfully! Status is now Pending Review.';
        setTimeout(() => {
          this.successMessage = '';
          this.cdr.markForCheck();
        }, 5000);
        this.loadDocuments(false);
      },
      error: (err) => {
        this.isUploading = false;
        this.fileError = err?.error?.detail || 'Failed to upload document. Please try again.';
        this.cdr.markForCheck();
      }
    });
  }

  // ─── Preview & Download Flow ─────────────────────────────────────────────────

  openPreview(doc: EmployeeDocumentItem): void {
    if (!doc.document_id) return;

    this.cleanupBlobUrls();
    this.activePreviewDocId = doc.document_id;
    this.previewDocTitle = `${doc.document_type_name} (${doc.file_name || 'Document'})`;
    this.isPreviewLoading = true;
    this.isPreviewModalOpen = true;

    this.documentService.previewDocument(doc.document_id).subscribe({
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

  downloadDocument(doc: EmployeeDocumentItem): void {
    if (!doc.document_id) return;

    this.documentService.downloadDocument(doc.document_id).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = doc.file_name || `${doc.document_type_code.toLowerCase()}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      },
      error: (err) => {
        console.error('Failed to download document:', err);
        alert('Failed to download document. Please try again.');
      }
    });
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
      },
      error: (err) => {
        console.error('Failed to download version:', err);
        alert('Failed to download version.');
      }
    });
  }


  // ─── Version History Flow ───────────────────────────────────────────────────

  openHistoryModal(doc: EmployeeDocumentItem): void {
    if (!doc.document_id) return;

    this.historyDocTitle = doc.document_type_name;
    this.versionHistory = [];
    this.isHistoryLoading = true;
    this.isHistoryModalOpen = true;

    this.documentService.getDocumentHistory(doc.document_id).subscribe({
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

  private cleanupBlobUrls(): void {
    if (this.rawBlobUrl) {
      URL.revokeObjectURL(this.rawBlobUrl);
      this.rawBlobUrl = null;
      this.previewBlobUrl = null;
    }
  }

  // ─── Helper Formatters ───────────────────────────────────────────────────────

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
      case 'VERIFIED':
        return 'status-verified';
      case 'PENDING_REVIEW':
        return 'status-pending';
      case 'REJECTED':
      case 'RESUBMISSION_REQUIRED':
        return 'status-rejected';
      case 'NOT_UPLOADED':
      default:
        return 'status-missing';
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'VERIFIED':
        return 'Verified';
      case 'PENDING_REVIEW':
        return 'Pending Review';
      case 'REJECTED':
        return 'Rejected';
      case 'RESUBMISSION_REQUIRED':
        return 'Re-upload Required';
      case 'NOT_UPLOADED':
      default:
        return 'Not Uploaded';
    }
  }

  getStatusIcon(status: string): string {
    switch (status) {
      case 'VERIFIED':
        return 'fas fa-check-circle';
      case 'PENDING_REVIEW':
        return 'fas fa-clock';
      case 'REJECTED':
        return 'fas fa-exclamation-circle';
      case 'RESUBMISSION_REQUIRED':
        return 'fas fa-redo-alt';
      case 'NOT_UPLOADED':
      default:
        return 'fas fa-cloud-upload-alt';
    }
  }

  isImageMime(mime?: string | null): boolean {
    return !!mime && (mime.startsWith('image/') || mime.includes('png') || mime.includes('jpeg') || mime.includes('jpg'));
  }
}
