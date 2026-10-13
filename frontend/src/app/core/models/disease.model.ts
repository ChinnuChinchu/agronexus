export type ScanStatus = 'ok' | 'uncertain' | 'crop_mismatch';
export type ScanLevel = 'strong' | 'possible' | 'uncertain';

export interface SupportedCrop {
  crop_type_id: number;
  name: string;
}

export interface Candidate {
  key: string;
  name: string;
  healthy: boolean;
  confidence_pct: number;
}

export interface SimilarCondition {
  key: string;
  name: string;
}

export interface DiseaseGuide {
  key: string;
  name: string;
  healthy: boolean;
  urgent: boolean;
  summary: string;
  symptoms: string[];
  actions: string[];
  prevention: string[];
  similar: SimilarCondition[];
}

export interface PredictionResult {
  scan_id: number;
  crop: string;
  status: ScanStatus;
  level: ScanLevel;
  headline: string;
  message: string;
  top: Candidate | null;
  alternatives: Candidate[];
  guide: DiseaseGuide | null;
  tips: string[];
  disclaimer: string;
}

export interface ScanRead {
  id: number;
  crop_name: string;
  status: ScanStatus;
  level: ScanLevel;
  result_key: string | null;
  result_name: string | null;
  confidence_pct: number | null;
  healthy: boolean;
  created_at: string;
}
