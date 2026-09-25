import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { OcrService } from '../../services/ocr.service';
import { OCRResponse, AnalyzeResponse } from '../../models/ocr.model';

@Component({
  selector: 'app-document-upload',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './document-upload.component.html',
  styleUrls: ['./document-upload.component.css']
})
export class DocumentUploadComponent {
  @Output() textExtracted = new EventEmitter<OCRResponse>();
  @Output() documentAnalyzed = new EventEmitter<AnalyzeResponse>();
  @Output() processingStateChange = new EventEmitter<boolean>();
  @Output() errorOccurred = new EventEmitter<string>();

  selectedFiles: File[] = [];
  previewUrls: string[] = [];
  isDragging: boolean = false;
  isLoading: boolean = false;
  loadingMessage: string = 'Processing document...';
  showActionSheet: boolean = false;

  constructor(private ocrService: OcrService) {}

  toggleActionSheet(): void {
    if (this.previewUrls.length === 0) {
      this.showActionSheet = !this.showActionSheet;
    }
  }

  onFileSelected(event: Event): void {
    this.showActionSheet = false;
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFiles(Array.from(input.files));
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;
    if (event.dataTransfer && event.dataTransfer.files.length > 0) {
      this.handleFiles(Array.from(event.dataTransfer.files));
    }
  }

  triggerFileInput(fileInput: HTMLInputElement): void {
    this.showActionSheet = false;
    fileInput.click();
  }

  triggerCameraInput(cameraInput: HTMLInputElement): void {
    this.showActionSheet = false;
    cameraInput.click();
  }

  private handleFiles(files: File[]): void {
    const validFiles: File[] = [];

    for (const file of files) {
      const lowerName = file.name.toLowerCase();
      const isImg = file.type.startsWith('image/');
      const isPdf = file.type === 'application/pdf' || lowerName.endsWith('.pdf');

      if (!isImg && !isPdf) {
        this.errorOccurred.emit(`Invalid file '${file.name}'. Please upload image or PDF files.`);
        continue;
      }
      validFiles.push(file);
    }

    if (validFiles.length === 0) return;

    this.selectedFiles = [...this.selectedFiles, ...validFiles];

    validFiles.forEach((file) => {
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = () => {
          this.previewUrls.push(reader.result as string);
        };
        reader.readAsDataURL(file);
      } else {
        // PDF placeholder thumbnail
        this.previewUrls.push('assets/pdf-placeholder.png');
      }
    });
  }

  removeFile(index: number): void {
    this.selectedFiles.splice(index, 1);
    this.previewUrls.splice(index, 1);
  }

  clearSelection(): void {
    this.selectedFiles = [];
    this.previewUrls = [];
  }

  onExtractText(): void {
    if (this.selectedFiles.length === 0) return;

    this.setLoading(true, 'Extracting raw OCR text...');
    this.ocrService.extractRawText(this.selectedFiles[0]).subscribe({
      next: (res) => {
        this.setLoading(false);
        this.textExtracted.emit(res);
      },
      error: (err) => {
        this.setLoading(false);
        this.errorOccurred.emit(err.message || 'OCR text extraction failed.');
      }
    });
  }

  onAnalyzeDocument(): void {
    if (this.selectedFiles.length === 0) return;

    if (this.selectedFiles.length > 1 || this.isPdfSelected()) {
      this.setLoading(true, `Running Multi-Page AI Analysis (${this.selectedFiles.length} file(s))...`);
      this.ocrService.uploadMultiDocument(this.selectedFiles).subscribe({
        next: (res) => {
          this.setLoading(false);
          this.documentAnalyzed.emit(res);
        },
        error: (err) => {
          this.setLoading(false);
          this.errorOccurred.emit(err.message || 'Multi-page document analysis failed.');
        }
      });
    } else {
      this.setLoading(true, 'Running AI Document Analysis & Structuring...');
      this.ocrService.analyzeDocument(this.selectedFiles[0]).subscribe({
        next: (res) => {
          this.setLoading(false);
          this.documentAnalyzed.emit(res);
        },
        error: (err) => {
          this.setLoading(false);
          this.errorOccurred.emit(err.message || 'Document analysis failed.');
        }
      });
    }
  }

  private isPdfSelected(): boolean {
    return this.selectedFiles.some(f => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf'));
  }

  private setLoading(loading: boolean, message: string = 'Processing...'): void {
    this.isLoading = loading;
    this.loadingMessage = message;
    this.processingStateChange.emit(loading);
  }
}
