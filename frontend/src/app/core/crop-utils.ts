import { Crop } from './models/crop.model';

export function ageLabel(days: number): string {
  if (days < 60) {
    return `${days} day${days === 1 ? '' : 's'}`;
  }
  const months = Math.floor(days / 30.4375);
  if (months < 24) {
    return `${months} months`;
  }
  const years = Math.floor(months / 12);
  const rest = months % 12;
  return rest ? `${years} yr ${rest} mo` : `${years} yr`;
}

export function harvestCountdown(crop: Crop): { text: string; overdue: boolean } | null {
  const g = crop.growth;
  if (crop.status !== 'growing') {
    return null;
  }
  if (g.stage === 'Planned') {
    return { text: 'Planting date is in the future', overdue: false };
  }
  if (g.days_to_harvest === null) {
    return { text: `Age: ${ageLabel(g.age_days)}`, overdue: false };
  }
  if (g.is_overdue) {
    const late = Math.abs(g.days_to_harvest);
    return { text: `Overdue by ${late} day${late === 1 ? '' : 's'}`, overdue: true };
  }
  if (g.days_to_harvest === 0) {
    return { text: 'Harvest due today', overdue: false };
  }
  if (g.days_to_harvest === 1) {
    return { text: 'Harvest tomorrow', overdue: false };
  }
  return { text: `${g.days_to_harvest} days to harvest`, overdue: false };
}
