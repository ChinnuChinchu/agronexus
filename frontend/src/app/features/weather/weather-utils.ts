import { AdvisorySeverity, ConditionIcon } from '../../core/models/weather.model';

const CONDITION_ICONS: Record<ConditionIcon, string> = {
  clear: 'wb_sunny',
  partly_cloudy: 'filter_drama',
  cloudy: 'cloud',
  drizzle: 'grain',
  rain: 'water_drop',
  thunderstorm: 'flash_on',
  fog: 'blur_on',
  snow: 'ac_unit',
};

const SEVERITY_ICONS: Record<AdvisorySeverity, string> = {
  warning: 'warning',
  caution: 'info',
  info: 'lightbulb',
};

export function conditionIcon(key: ConditionIcon): string {
  return CONDITION_ICONS[key] ?? 'cloud';
}

export function severityIcon(severity: AdvisorySeverity): string {
  return SEVERITY_ICONS[severity] ?? 'info';
}

const weekdayFormat = new Intl.DateTimeFormat('en-IN', { weekday: 'short', timeZone: 'UTC' });
const dateFormat = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric',
  month: 'short',
  timeZone: 'UTC',
});

/** 'YYYY-MM-DD' -> 'Fri' (no timezone shifting). */
export function weekdayLabel(isoDate: string): string {
  return weekdayFormat.format(new Date(`${isoDate.slice(0, 10)}T12:00:00Z`));
}

/** 'YYYY-MM-DD' -> '9 Oct'. */
export function shortDateLabel(isoDate: string): string {
  return dateFormat.format(new Date(`${isoDate.slice(0, 10)}T12:00:00Z`));
}

/** '2026-10-08T14:30:00+05:30' -> '2026-10-08' (the date in the location's own time). */
export function datePart(iso: string): string {
  return iso.slice(0, 10);
}

/** '2026-10-08T14:30:00+05:30' -> '2:30 PM' (the clock time in the location's own time). */
export function clockLabel(iso: string): string {
  const hours = Number(iso.slice(11, 13));
  const minutes = iso.slice(14, 16);
  const suffix = hours >= 12 ? 'PM' : 'AM';
  return `${hours % 12 || 12}:${minutes} ${suffix}`;
}
