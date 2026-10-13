export type ConditionIcon =
  | 'clear'
  | 'partly_cloudy'
  | 'cloudy'
  | 'drizzle'
  | 'rain'
  | 'thunderstorm'
  | 'fog'
  | 'snow';

export type AdvisorySeverity = 'info' | 'caution' | 'warning';

export interface Condition {
  label: string;
  icon: ConditionIcon;
}

export interface LocationInfo {
  name: string;
  state: string | null;
  country: string;
  lat: number;
  lon: number;
}

export interface CurrentWeather {
  temp_c: number;
  feels_like_c: number;
  humidity_pct: number;
  wind_kmh: number;
  rain_mm: number;
  condition: Condition;
  observed_at: string;
}

export interface HourlySlot {
  time: string;
  temp_c: number;
  humidity_pct: number;
  rain_chance_pct: number;
  rain_mm: number;
  wind_kmh: number;
  condition: Condition;
}

export interface DailyForecast {
  date: string;
  temp_min_c: number;
  temp_max_c: number;
  rain_chance_pct: number;
  rain_mm: number;
  wind_max_kmh: number;
  humidity_pct: number;
  condition: Condition;
}

export interface Advisory {
  code: string;
  severity: AdvisorySeverity;
  title: string;
  message: string;
  date: string | null;
}

export interface WeatherReport {
  location: LocationInfo;
  current: CurrentWeather;
  hourly: HourlySlot[];
  daily: DailyForecast[];
  advisories: Advisory[];
}
