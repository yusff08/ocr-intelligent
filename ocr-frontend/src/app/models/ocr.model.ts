export interface HealthResponse {
  status: string;
}

export interface BoundingBox {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
  text: string;
  confidence: number;
}

export interface PageData {
  page_number: number;
  raw_text: string;
  boxes?: BoundingBox[];
  confidence?: number;
  preview_url?: string;
}

export interface OCRResponse {
  success: boolean;
  text: string;
  confidence: number;
  document_id?: number;
}

export interface LineItem {
  description: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

export interface DocumentMetadata {
  document_type: string;
  vendor_name: string;
  invoice_number: string;
  issue_date: string;
  due_date: string;
  currency: string;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  items: LineItem[];
}

export interface AnalyzeResponse {
  success: boolean;
  document_id?: number;
  page_count?: number;
  document_type: string;
  metadata: DocumentMetadata;
  raw_text: string;
  pages_data?: PageData[];
  processing_time: number;
}

export interface AuthRequest {
  email: string;
  password: string;
}

export interface User {
  id: number;
  email: string;
  created_at?: string;
}

export interface AuthResponse {
  success?: boolean;
  access_token: string;
  token_type: string;
  user: User;
}

export interface DocumentHistoryItem {
  id: number;
  user_id?: number;
  filename: string;
  document_type: string;
  raw_text?: string;
  metadata?: DocumentMetadata | any;
  metadata_json?: any;
  page_count?: number;
  pages_data?: PageData[] | any;
  created_at: string;
}

export interface HistoryListResponse {
  success: boolean;
  count: number;
  documents: DocumentHistoryItem[];
}
