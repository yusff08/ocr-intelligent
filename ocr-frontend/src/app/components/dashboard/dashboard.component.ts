import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DocumentUploadComponent } from '../document-upload/document-upload.component';
import { ResultViewerComponent } from '../result-viewer/result-viewer.component';
import { OCRResponse, AnalyzeResponse } from '../../models/ocr.model';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, DocumentUploadComponent, ResultViewerComponent],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent {
  rawTextResult: OCRResponse | null = null;
  analyzeResult: AnalyzeResponse | null = null;
  errorMessage: string | null = null;

  onTextExtracted(result: OCRResponse): void {
    this.errorMessage = null;
    this.rawTextResult = result;
  }

  onDocumentAnalyzed(result: AnalyzeResponse): void {
    this.errorMessage = null;
    this.analyzeResult = result;
    if (!this.rawTextResult) {
      this.rawTextResult = {
        success: result.success,
        text: result.raw_text,
        confidence: 0.95
      };
    }
  }

  onErrorOccurred(message: string): void {
    this.errorMessage = message;
  }

  dismissError(): void {
    this.errorMessage = null;
  }
}
