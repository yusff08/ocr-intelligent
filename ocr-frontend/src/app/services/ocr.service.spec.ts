import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { OcrService } from './ocr.service';
import { AuthService } from './auth.service';
import { environment } from '../../environments/environment';

describe('OcrService', () => {
  let service: OcrService;
  let httpMock: HttpTestingController;
  let authServiceSpy: jasmine.SpyObj<AuthService>;

  const baseUrl = environment.apiUrl.replace(/\/+$/, '');

  beforeEach(() => {
    authServiceSpy = jasmine.createSpyObj('AuthService', ['getToken']);
    authServiceSpy.getToken.and.returnValue('mock-token-123');

    TestBed.configureTestingModule({
      providers: [
        OcrService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authServiceSpy }
      ]
    });

    service = TestBed.inject(OcrService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should call health endpoint via checkHealth()', () => {
    const mockHealth = { status: 'UP' };

    service.checkHealth().subscribe((response) => {
      expect(response).toEqual(mockHealth);
    });

    const req = httpMock.expectOne(`${baseUrl}/health`);
    expect(req.request.method).toBe('GET');
    req.flush(mockHealth);
  });

  it('should post file to extractRawText() with Authorization header', () => {
    const mockFile = new File(['dummy content'], 'invoice.png', { type: 'image/png' });
    const mockResponse = { success: true, text: 'Sample OCR Text', confidence: 0.98, document_id: 1 };

    service.extractRawText(mockFile).subscribe((res) => {
      expect(res.success).toBeTrue();
      expect(res.text).toBe('Sample OCR Text');
    });

    const req = httpMock.expectOne(`${baseUrl}/ocr`);
    expect(req.request.method).toBe('POST');
    expect(req.request.headers.get('Authorization')).toBe('Bearer mock-token-123');
    expect(req.request.body instanceof FormData).toBeTrue();
    req.flush(mockResponse);
  });

  it('should post file to analyzeDocument()', () => {
    const mockFile = new File(['dummy content'], 'invoice.pdf', { type: 'application/pdf' });
    const mockResponse = {
      success: true,
      document_id: 2,
      document_type: 'invoice',
      metadata: { vendor_name: 'Test Corp' },
      raw_text: 'FACTUR 100',
      processing_time: 0.45
    };

    service.analyzeDocument(mockFile).subscribe((res) => {
      expect(res.success).toBeTrue();
      expect(res.document_type).toBe('invoice');
    });

    const req = httpMock.expectOne(`${baseUrl}/ocr/analyze`);
    expect(req.request.method).toBe('POST');
    expect(req.request.headers.get('Authorization')).toBe('Bearer mock-token-123');
    req.flush(mockResponse);
  });

  it('should fetch history via getHistory()', () => {
    const mockHistory = {
      success: true,
      count: 1,
      documents: [
        { id: 10, user_id: 1, filename: 'test.png', document_type: 'generic', raw_text: 'Text', metadata: {}, created_at: '2026-08-07T10:00:00Z' }
      ]
    };

    service.getHistory().subscribe((res) => {
      expect(res.success).toBeTrue();
      expect(res.count).toBe(1);
      expect(res.documents.length).toBe(1);
    });

    const req = httpMock.expectOne(`${baseUrl}/documents/history`);
    expect(req.request.method).toBe('GET');
    expect(req.request.headers.get('Authorization')).toBe('Bearer mock-token-123');
    req.flush(mockHistory);
  });

  it('should post files to uploadMultiDocument()', () => {
    const mockFiles = [
      new File(['content 1'], 'page1.png', { type: 'image/png' }),
      new File(['content 2'], 'page2.png', { type: 'image/png' })
    ];
    const mockResponse = {
      success: true,
      document_id: 5,
      page_count: 2,
      document_type: 'invoice',
      metadata: { vendor_name: 'Multi Corp' } as any,
      raw_text: 'Text 1\nText 2',
      pages_data: [
        { page_number: 1, raw_text: 'Text 1' },
        { page_number: 2, raw_text: 'Text 2' }
      ],
      processing_time: 1.2
    };

    service.uploadMultiDocument(mockFiles).subscribe((res) => {
      expect(res.success).toBeTrue();
      expect(res.page_count).toBe(2);
      expect(res.pages_data?.length).toBe(2);
    });

    const req = httpMock.expectOne(`${baseUrl}/ocr/upload-multi`);
    expect(req.request.method).toBe('POST');
    expect(req.request.headers.get('Authorization')).toBe('Bearer mock-token-123');
    expect(req.request.body instanceof FormData).toBeTrue();
    req.flush(mockResponse);
  });
});

