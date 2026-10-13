export type CropStatus = 'growing' | 'harvested' | 'failed';
export type CropCycle = 'seasonal' | 'perennial';

export interface CropType {
  id: number;
  name: string;
  category: string;
  cycle: CropCycle;
  duration_days: number | null;
  bearing_age_months: number | null;
}

export interface GrowthInfo {
  stage: string;
  stage_index: number | null;
  stages: string[];
  progress_pct: number;
  age_days: number;
  days_to_harvest: number | null;
  is_overdue: boolean;
}

export interface Crop {
  id: number;
  name: string;
  crop_type: CropType;
  variety: string | null;
  area_acres: number | null;
  planting_date: string;
  expected_harvest_date: string | null;
  status: CropStatus;
  actual_harvest_date: string | null;
  yield_quantity: number | null;
  yield_unit: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  growth: GrowthInfo;
}

export interface CropCreateRequest {
  name: string;
  crop_type_id: number;
  variety?: string | null;
  area_acres?: number | null;
  planting_date: string;
  expected_harvest_date?: string | null;
  notes?: string | null;
}

export interface CropUpdateRequest {
  name?: string;
  crop_type_id?: number;
  variety?: string | null;
  area_acres?: number | null;
  planting_date?: string;
  expected_harvest_date?: string | null;
  status?: 'growing' | 'failed';
  notes?: string | null;
}

export interface HarvestRequest {
  actual_harvest_date?: string | null;
  yield_quantity?: number | null;
  yield_unit?: string | null;
}
