import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { AuthService } from './auth.service';
import { environment } from '../../environments/environment';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  const baseUrl = environment.apiUrl.replace(/\/+$/, '');

  beforeEach(() => {
    localStorage.clear();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });

    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    localStorage.clear();
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should register a new user', () => {
    const credentials = { email: 'newuser@example.com', password: 'Password123!' };
    const mockResponse = { success: true, message: 'User registered', user_id: 1, email: 'newuser@example.com' };

    service.register(credentials).subscribe((res) => {
      expect(res.success).toBeTrue();
    });

    const req = httpMock.expectOne(`${baseUrl}/auth/register`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(credentials);
    req.flush(mockResponse);
  });

  it('should handle login and update localStorage and signals', () => {
    const credentials = { email: 'authuser@example.com', password: 'Password123!' };
    const mockAuthResponse = {
      access_token: 'jwt-test-token-xyz',
      token_type: 'bearer',
      user: { id: 1, email: 'authuser@example.com' }
    };

    expect(service.isLoggedIn()).toBeFalse();
    expect(service.getToken()).toBeNull();

    service.login(credentials).subscribe((res) => {
      expect(res.access_token).toBe('jwt-test-token-xyz');
      expect(service.getToken()).toBe('jwt-test-token-xyz');
      expect(service.currentUserValue).toEqual({ id: 1, email: 'authuser@example.com' });
      expect(service.isLoggedIn()).toBeTrue();
      expect(localStorage.getItem('token')).toBe('jwt-test-token-xyz');
    });

    const req = httpMock.expectOne(`${baseUrl}/auth/login`);
    expect(req.request.method).toBe('POST');
    req.flush(mockAuthResponse);
  });

  it('should clear storage and reset state on logout', () => {
    localStorage.setItem('token', 'stored-token');
    localStorage.setItem('user', JSON.stringify({ id: 9, email: 'logout@example.com' }));

    service.logout();

    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
    expect(service.currentUserValue).toBeNull();
    expect(service.isLoggedIn()).toBeFalse();
    expect(service.getToken()).toBeNull();
  });
});
