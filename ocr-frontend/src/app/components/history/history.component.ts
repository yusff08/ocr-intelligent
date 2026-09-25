import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { OcrService } from '../../services/ocr.service';
import { DocumentHistoryItem } from '../../models/ocr.model';

@Component({
  selector: 'app-history',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './history.component.html',
  styleUrls: ['./history.component.css']
})
export class HistoryComponent implements OnInit {
  documents: DocumentHistoryItem[] = [];
  isLoading = true;
  errorMessage = '';

  // iOS Search & Segmented Filter State
  searchQuery = '';
  selectedType: 'ALL' | 'invoice' | 'receipt' | 'generic' = 'ALL';

  // Native iOS Bottom Sheet State
  selectedDoc: DocumentHistoryItem | null = null;
  isBottomSheetOpen = false;
  sheetTab: 'details' | 'items' | 'raw' | 'json' = 'details';
  copiedDocId: number | null = null;

  constructor(private ocrService: OcrService) {}

  ngOnInit(): void {
    this.loadHistory();
  }

  loadHistory(): void {
    this.isLoading = true;
    this.errorMessage = '';
    this.ocrService.getHistory().subscribe({
      next: (res) => {
        this.isLoading = false;
        this.documents = res.documents || [];
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage = err.message || 'Failed to load document history.';
      }
    });
  }

  get filteredHistory(): DocumentHistoryItem[] {
    return this.documents.filter(doc => {
      const typeMatches = this.selectedType === 'ALL' || 
        (doc.document_type || '').toLowerCase() === this.selectedType.toLowerCase();

      if (!typeMatches) return false;

      if (!this.searchQuery.trim()) return true;

      const q = this.searchQuery.toLowerCase();
      const filename = (doc.filename || '').toLowerCase();
      const docType = (doc.document_type || '').toLowerCase();
      const vendor = (this.getVendorName(doc)).toLowerCase();
      const invNum = (this.getInvoiceNumber(doc)).toLowerCase();

      return filename.includes(q) || docType.includes(q) || vendor.includes(q) || invNum.includes(q);
    });
  }

  setSelectedType(type: 'ALL' | 'invoice' | 'receipt' | 'generic'): void {
    this.selectedType = type;
  }

  openBottomSheet(doc: DocumentHistoryItem, event?: Event): void {
    if (event) event.stopPropagation();
    this.selectedDoc = doc;
    this.sheetTab = 'details';
    this.isBottomSheetOpen = true;
  }

  closeBottomSheet(): void {
    this.isBottomSheetOpen = false;
    this.selectedDoc = null;
  }

  deleteDoc(docId: number, event?: Event): void {
    if (event) event.stopPropagation();
    if (confirm('Are you sure you want to delete this scan from your history?')) {
      this.ocrService.deleteHistory(docId).subscribe({
        next: () => {
          this.documents = this.documents.filter(d => d.id !== docId);
          if (this.selectedDoc && this.selectedDoc.id === docId) {
            this.closeBottomSheet();
          }
        },
        error: (err) => {
          alert('Failed to delete document record: ' + err.message);
        }
      });
    }
  }

  copyJson(doc: DocumentHistoryItem, event?: Event): void {
    if (event) event.stopPropagation();
    const metadata = doc.metadata || doc.metadata_json || {};
    const textToCopy = typeof metadata === 'string' ? metadata : JSON.stringify(metadata, null, 2);

    navigator.clipboard.writeText(textToCopy).then(() => {
      this.copiedDocId = doc.id;
      setTimeout(() => {
        this.copiedDocId = null;
      }, 2000);
    });
  }

  downloadJson(doc: DocumentHistoryItem, event?: Event): void {
    if (event) event.stopPropagation();
    const metadata = doc.metadata || doc.metadata_json || {};
    const jsonStr = typeof metadata === 'string' ? metadata : JSON.stringify(metadata, null, 2);
    
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ocr_${doc.filename || doc.id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // --- Metadata Helper Extractors ---

  getVendorName(doc: DocumentHistoryItem): string {
    const meta = doc.metadata || doc.metadata_json;
    if (meta && typeof meta === 'object') {
      return meta.vendor_name || meta.vendor || 'Unknown Vendor';
    }
    return 'Unknown Vendor';
  }

  getInvoiceNumber(doc: DocumentHistoryItem): string {
    const meta = doc.metadata || doc.metadata_json;
    if (meta && typeof meta === 'object') {
      return meta.invoice_number || meta.inv_no || 'N/A';
    }
    return 'N/A';
  }

  getTotalAmount(doc: DocumentHistoryItem): string {
    const meta = doc.metadata || doc.metadata_json;
    if (meta && typeof meta === 'object' && meta.total_amount !== undefined) {
      return Number(meta.total_amount).toFixed(2);
    }
    return '0.00';
  }

  getCurrency(doc: DocumentHistoryItem): string {
    const meta = doc.metadata || doc.metadata_json;
    if (meta && typeof meta === 'object') {
      return meta.currency || 'EUR';
    }
    return 'EUR';
  }

  getIssueDate(doc: DocumentHistoryItem): string {
    const meta = doc.metadata || doc.metadata_json;
    if (meta && typeof meta === 'object') {
      return meta.issue_date || 'N/A';
    }
    return 'N/A';
  }

  getDueDate(doc: DocumentHistoryItem): string {
    const meta = doc.metadata || doc.metadata_json;
    if (meta && typeof meta === 'object') {
      return meta.due_date || 'N/A';
    }
    return 'N/A';
  }

  getSubtotal(doc: DocumentHistoryItem): string {
    const meta = doc.metadata || doc.metadata_json;
    if (meta && typeof meta === 'object' && meta.subtotal !== undefined) {
      return Number(meta.subtotal).toFixed(2);
    }
    return '0.00';
  }

  getTaxAmount(doc: DocumentHistoryItem): string {
    const meta = doc.metadata || doc.metadata_json;
    if (meta && typeof meta === 'object' && meta.tax_amount !== undefined) {
      return Number(meta.tax_amount).toFixed(2);
    }
    return '0.00';
  }

  getLineItems(doc: DocumentHistoryItem): any[] {
    const meta = doc.metadata || doc.metadata_json;
    if (meta && typeof meta === 'object' && Array.isArray(meta.items)) {
      return meta.items;
    }
    return [];
  }

  formatJsonString(doc: DocumentHistoryItem): string {
    const meta = doc.metadata || doc.metadata_json;
    if (!meta) return '{}';
    if (typeof meta === 'string') return meta;
    return JSON.stringify(meta, null, 2);
  }
}
