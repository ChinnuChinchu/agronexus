export interface User {
  id: number;
  username: string;
  email: string | null;
  full_name: string | null;
  phone: string | null;
  village: string | null;
  district: string | null;
  state: string | null;
  farm_size_acres: number | null;
  is_active: boolean;
  created_at: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  email?: string | null;
  full_name?: string | null;
}

export interface UpdateProfileRequest {
  email?: string | null;
  full_name?: string | null;
  phone?: string | null;
  village?: string | null;
  district?: string | null;
  state?: string | null;
  farm_size_acres?: number | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}
