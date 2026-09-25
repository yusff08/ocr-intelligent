import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';
import {
  HealthResponse,
  OCRResponse,
  AnalyzeResponse,
  HistoryListResponse
} from '../models/ocr.model';

@Injectable({
  providedIn: 'root'
})
export class OcrService {
  constructor(
    private http: HttpClient,
    private authService: AuthService
  ) {
    const baseUrl = this.getSanitizedBaseUrl();
    console.log(`[OcrService] Initialized with API Base URL: ${baseUrl}`);
  }

  private getSanitizedBaseUrl(): string {
    let url = environment.apiUrl || 'http://localhost:8080/api';
    if (typeof window !== 'undefined' && window.location && window.location.hostname) {
      const currentHost = window.location.hostname;
      if (currentHost !== 'localhost' && currentHost !== '127.0.0.1') {
        url = url.replace('localhost', currentHost).replace('127.0.0.1', currentHost);
      }
    }
    return url.replace(/\/+$/, '');
  }

  private getAuthHeaders(): HttpHeaders {
    const token = this.authService.getToken();
    if (token) {
      return new HttpHeaders({
        Authorization: `Bearer ${token}`
      });
    }
    return new HttpHeaders();
  }

  checkHealth(): Observable<HealthResponse> {
    const targetUrl = `${this.getSanitizedBaseUrl()}/health`;
    return this.http.get<HealthResponse>(targetUrl).pipe(
      catchError((err) => this.handleError('checkHealth', targetUrl, err))
    );
  }

  extractRawText(file: File): Observable<OCRResponse> {
    const targetUrl = `${this.getSanitizedBaseUrl()}/ocr`;
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<OCRResponse>(targetUrl, formData, { headers: this.getAuthHeaders() }).pipe(
      catchError((err) => this.handleError('extractRawText', targetUrl, err))
    );
  }

  analyzeDocument(file: File): Observable<AnalyzeResponse> {
    const targetUrl = `${this.getSanitizedBaseUrl()}/ocr/analyze`;
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<AnalyzeResponse>(targetUrl, formData, { headers: this.getAuthHeaders() }).pipe(
      catchError((err) => this.handleError('analyzeDocument', targetUrl, err))
    );
  }

  uploadMultiDocument(files: File[]): Observable<AnalyzeResponse> {
    const targetUrl = `${this.getSanitizedBaseUrl()}/ocr/upload-multi`;
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    return this.http.post<AnalyzeResponse>(targetUrl, formData, { headers: this.getAuthHeaders() }).pipe(
      catchError((err) => this.handleError('uploadMultiDocument', targetUrl, err))
    );
  }


  getHistory(): Observable<HistoryListResponse> {
    const targetUrl = `${this.getSanitizedBaseUrl()}/documents/history`;
    return this.http.get<HistoryListResponse>(targetUrl, { headers: this.getAuthHeaders() }).pipe(
      catchError((err) => this.handleError('getHistory', targetUrl, err))
    );
  }

  deleteHistory(docId: number): Observable<any> {
    const targetUrl = `${this.getSanitizedBaseUrl()}/documents/history/${docId}`;
    return this.http.delete<any>(targetUrl, { headers: this.getAuthHeaders() }).pipe(
      catchError((err) => this.handleError('deleteHistory', targetUrl, err))
    );
  }

  private handleError(operation: string, url: string, error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'An unknown error occurred!';
    if (error.error instanceof ErrorEvent) {
      errorMessage = `Client Error: ${error.error.message}`;
    } else {
      errorMessage = error.error?.detail || `Server Error [Status ${error.status}]: ${error.message}`;
    }

    console.error(`[OcrService Failed] ${operation} -> ${url}`, {
      status: error.status,
      statusText: error.statusText,
      message: errorMessage,
      rawError: error
    });

    return throwError(() => new Error(errorMessage));
  }
}
