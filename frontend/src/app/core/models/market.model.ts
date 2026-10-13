export type SignalLabel = 'above_average' | 'below_average' | 'stable' | 'insufficient_data';

export interface AvailableCrop {
  crop_type_id: number;
  name: string;
  category: string;
  latest_date: string;
  days_old: number;
  stale: boolean;
}

export interface MarketPriceRow {
  market: string;
  district: string;
  variety: string;
  date: string;
  min_price: number;
  max_price: number;
  modal_price: number;
  in_my_district: boolean;
}

export interface PriceSummary {
  average_modal: number;
  highest_modal: number;
  lowest_modal: number;
  markets: number;
}

export interface PriceBoard {
  crop_type_id: number;
  crop_name: string;
  state: string;
  commodity_names: string[];
  has_data: boolean;
  as_of: string | null;
  days_old: number | null;
  stale: boolean;
  variety: string | null;
  varieties: string[];
  summary: PriceSummary | null;
  markets: MarketPriceRow[];
  unit: string;
  source: string;
}

export interface TrendPoint {
  date: string;
  median_modal: number;
  markets: number;
}

export interface Signal {
  label: SignalLabel;
  pct_vs_average: number | null;
  average_modal: number | null;
  message: string;
}

export interface PriceTrend {
  crop_type_id: number;
  crop_name: string;
  state: string;
  has_data: boolean;
  as_of: string | null;
  days_old: number | null;
  stale: boolean;
  days: number;
  variety: string | null;
  points: TrendPoint[];
  latest_modal: number | null;
  change_7d_pct: number | null;
  change_30d_pct: number | null;
  signal: Signal | null;
  unit: string;
  source: string;
}
