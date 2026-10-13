/** Today's date as YYYY-MM-DD in the browser's local time. */
export function todayIso(): string {
  const d = new Date();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${month}-${day}`;
}
/** Adds days to a YYYY-MM-DD date string, with no timezone shifting. */
export function addDays(iso: string, days: number): string {
  const [y, m, d] = iso.split('-').map(Number);
  const result = new Date(Date.UTC(y, m - 1, d + days));
  return isNaN(result.getTime()) ? '' : result.toISOString().slice(0, 10);
}
