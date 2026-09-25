import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { OcrService } from '../../services/ocr.service';
import { OCRResponse, AnalyzeResponse, PageData, BoundingBox } from '../../models/ocr.model';

@Component({
  selector: 'app-result-viewer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './result-viewer.component.html',
  styleUrls: ['./result-viewer.component.css']
})
export class ResultViewerComponent implements OnInit {
  @Input() rawTextResult: OCRResponse | null = null;
  @Input() analyzeResult: AnalyzeResponse | null = null;

  healthStatus: 'UP' | 'DOWN' | 'CHECKING' = 'CHECKING';
  activeTab: 'structured' | 'raw' | 'pages' = 'structured';
  selectedPageIndex: number = 0;
  copied: boolean = false;

  constructor(private ocrService: OcrService) {}

  ngOnInit(): void {
    this.checkHealth();
  }

  checkHealth(): void {
    this.healthStatus = 'CHECKING';
    this.ocrService.checkHealth().subscribe({
      next: (res) => {
        this.healthStatus = res.status === 'UP' ? 'UP' : 'DOWN';
      },
      error: () => {
        this.healthStatus = 'DOWN';
      }
    });
  }

  selectTab(tab: 'structured' | 'raw' | 'pages'): void {
    this.activeTab = tab;
  }

  selectPage(index: number): void {
    this.selectedPageIndex = index;
  }

  copyToClipboard(): void {
    const textToCopy = this.rawTextResult?.text || this.analyzeResult?.raw_text || '';
    if (!textToCopy) return;

    navigator.clipboard.writeText(textToCopy).then(() => {
      this.copied = true;
      setTimeout(() => {
        this.copied = false;
      }, 2000);
    });
  }

  get pageCount(): number {
    return this.analyzeResult?.page_count || (this.analyzeResult?.pages_data?.length || 1);
  }

  get pagesData(): PageData[] {
    return this.analyzeResult?.pages_data || [];
  }

  get currentPage(): PageData | null {
    if (this.pagesData.length > 0 && this.selectedPageIndex < this.pagesData.length) {
      return this.pagesData[this.selectedPageIndex];
    }
    return null;
  }

  get currentPageBoxes(): BoundingBox[] {
    return this.currentPage?.boxes || [];
  }

  get processingTime(): string {
    if (this.analyzeResult) {
      return `${this.analyzeResult.processing_time}s`;
    }
    return 'N/A';
  }

  get confidenceScore(): string {
    if (this.rawTextResult) {
      return `${Math.round(this.rawTextResult.confidence * 100)}%`;
    }
    return '95%';
  }

  get documentType(): string {
    if (this.analyzeResult) {
      return this.analyzeResult.document_type.toUpperCase();
    }
    return 'GENERIC';
  }
}
