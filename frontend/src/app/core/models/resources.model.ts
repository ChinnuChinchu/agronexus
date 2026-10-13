import { LocationInfo } from './weather.model';

export type IrrigationStatus =
  | 'irrigate_soon'
  | 'plan_irrigation'
  | 'not_needed'
  | 'flooded'
  | 'not_planted'
  | 'no_guidance';

export type FertilizerWeather = 'ok' | 'caution' | 'hold';

export interface WaterDay {
  date: string;
  et0_mm: number;
  kc: number;
  crop_need_mm: number;
  rain_mm: number;
  effective_rain_mm: number;
  soil_water_mm: number;
}

export interface IrrigationAdvice {
  status: IrrigationStatus;
  headline: string;
  detail: string;
  irrigate_by: string | null;
  days: WaterDay[];
  total_need_mm: number;
  total_effective_rain_mm: number;
  suggested_depth_mm: number | null;
  litres_per_acre: number | null;
  total_litres: number | null;
  approximate: boolean;
}

export interface FertilizerStepInfo {
  title: string;
  nutrients: string;
  note: string;
}

export interface FertilizerAdvice {
  summary: string;
  current: FertilizerStepInfo | null;
  upcoming: FertilizerStepInfo | null;
  days_until_upcoming: number | null;
  weather: FertilizerWeather;
  weather_message: string | null;
  approximate_timing: boolean;
  disclaimer: string;
}

export interface CropPlan {
  crop_id: number;
  crop_name: string;
  crop_type: string;
  stage: string;
  progress_pct: number;
  area_acres: number | null;
  irrigation: IrrigationAdvice;
  fertilizer: FertilizerAdvice | null;
}

export interface PlanAction {
  crop_id: number;
  crop_name: string;
  kind: 'irrigation' | 'fertilizer';
  priority: 'high' | 'medium';
  text: string;
}

export interface PlanSummary {
  crops: number;
  need_water_soon: number;
  fertilizer_due: number;
  fertilizer_on_hold: number;
  litres_needed: number;
  litres_crops_counted: number;
}

export interface ResourcePlan {
  location: LocationInfo | null;
  as_of: string | null;
  summary: PlanSummary;
  actions: PlanAction[];
  crops: CropPlan[];
  note: string;
}
