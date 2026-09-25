import { Injectable, signal, computed } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, BehaviorSubject, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { AuthRequest, AuthResponse, User } from '../models/ocr.model';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private currentUserSubject = new BehaviorSubject<User | null>(this.getStoredUser());
  public currentUser$ = this.currentUserSubject.asObservable();

  // Angular Signals for reactive UI state
  public currentUser = signal<User | null>(this.getStoredUser());
  public isLoggedIn = computed(() => !!this.currentUser());

  constructor(private http: HttpClient) {
    const baseUrl = this.getSanitizedBaseUrl();
    console.log(`[AuthService] Initialized with API Base URL: ${baseUrl}`);
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

  private getStoredUser(): User | null {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        return JSON.parse(userStr);
      } catch {
        return null;
      }
    }
    return null;
  }

  public getToken(): string | null {
    return localStorage.getItem('token');
  }

  public get currentUserValue(): User | null {
    return this.currentUser();
  }

  register(credentials: AuthRequest): Observable<any> {
    const targetUrl = `${this.getSanitizedBaseUrl()}/auth/register`;
    return this.http.post<any>(targetUrl, credentials).pipe(
      catchError((err) => this.handleError('register', targetUrl, err))
    );
  }

  login(credentials: AuthRequest): Observable<AuthResponse> {
    const targetUrl = `${this.getSanitizedBaseUrl()}/auth/login`;
    return this.http.post<AuthResponse>(targetUrl, credentials).pipe(
      tap((res) => {
        if (res && res.access_token) {
          localStorage.setItem('token', res.access_token);
          localStorage.setItem('user', JSON.stringify(res.user));
          this.currentUser.set(res.user);
          this.currentUserSubject.next(res.user);
        }
      }),
      catchError((err) => this.handleError('login', targetUrl, err))
    );
  }

  logout(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    this.currentUser.set(null);
    this.currentUserSubject.next(null);
  }

  private handleError(operation: string, url: string, error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'An unknown error occurred!';
    if (error.error instanceof ErrorEvent) {
      errorMessage = `Client Error: ${error.error.message}`;
    } else {
      errorMessage = error.error?.detail || `Server Error [Status ${error.status}]: ${error.message}`;
    }

    console.error(`[AuthService Failed] ${operation} -> ${url}`, {
      status: error.status,
      statusText: error.statusText,
      message: errorMessage,
      rawError: error
    });

    return throwError(() => new Error(errorMessage));
  }
}
