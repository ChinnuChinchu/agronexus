import { SignalLabel } from '../../core/models/market.model';

const rupeeFormat = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });
const perKgFormat = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 1 });
const shortDate = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric',
  month: 'short',
  year: '2-digit',
  timeZone: 'UTC',
});
const longDate = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
});

/** 7400 -> '₹7,400' (Indian digit grouping). */
export function inr(value: number): string {
  return `₹${rupeeFormat.format(value)}`;
}

/** Price per quintal (100 kg) -> price per kg, e.g. 7400 -> '₹74/kg'. */
export function perKg(pricePerQuintal: number): string {
  return `₹${perKgFormat.format(pricePerQuintal / 100)}/kg`;
}

/** 'YYYY-MM-DD' -> '30 Oct 25' (no timezone shifting). */
export function chartDate(isoDate: string): string {
  return shortDate.format(new Date(`${isoDate.slice(0, 10)}T12:00:00Z`));
}

/** 'YYYY-MM-DD' -> '30 Oct 2025'. */
export function fullDate(isoDate: string): string {
  return longDate.format(new Date(`${isoDate.slice(0, 10)}T12:00:00Z`));
}

/** 330 -> 'about 11 months ago'. */
export function agoLabel(days: number): string {
  if (days <= 0) {
    return 'today';
  }
  if (days === 1) {
    return 'yesterday';
  }
  if (days < 45) {
    return `${days} days ago`;
  }
  const months = Math.round(days / 30.4375);
  if (months < 18) {
    return `about ${months} months ago`;
  }
  const years = Math.round((days / 365) * 10) / 10;
  return `about ${years} years ago`;
}

export function signalTitle(label: SignalLabel): string {
  switch (label) {
    case 'above_average':
      return 'Above average';
    case 'below_average':
      return 'Below average';
    case 'stable':
      return 'Stable';
    default:
      return 'Not enough data';
  }
}

export function signalIcon(label: SignalLabel): string {
  switch (label) {
    case 'above_average':
      return 'trending_up';
    case 'below_average':
      return 'trending_down';
    case 'stable':
      return 'trending_flat';
    default:
      return 'help_outline';
  }
}

export function changeText(pct: number | null): string {
  if (pct === null) {
    return 'Not enough data';
  }
  return `${pct > 0 ? '+' : ''}${pct}%`;
}

export function changeIcon(pct: number | null): string {
  if (pct === null || Math.abs(pct) < 0.5) {
    return 'trending_flat';
  }
  return pct > 0 ? 'trending_up' : 'trending_down';
}

export function changeClass(pct: number | null): 'up' | 'down' | 'flat' {
  if (pct === null || Math.abs(pct) < 0.5) {
    return 'flat';
  }
  return pct > 0 ? 'up' : 'down';
}
