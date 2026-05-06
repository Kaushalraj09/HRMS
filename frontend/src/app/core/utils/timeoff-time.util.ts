/** Shift window and helpers for inline time-off (must match backend: 09:00–18:00, 9h total). */
export const SHIFT_TOTAL_HOURS = 9;
export const SHIFT_START = '09:00';
export const SHIFT_END = '18:00';

export interface TimeSlotOption {
  value: string;
  label: string;
}

/** Build 30-minute slot values from 09:00 through 18:00 inclusive. */
export function buildHalfHourSlots(): TimeSlotOption[] {
  const slots: TimeSlotOption[] = [];
  for (let h = 9; h <= 18; h++) {
    for (const m of [0, 30]) {
      if (h === 18 && m > 0) {
        break;
      }
      const value = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
      slots.push({ value, label: formatTimeLabel(value) });
    }
  }
  return slots;
}

export function formatTimeLabel(hhmm: string): string {
  const parsed = parseTimeToMinutes(hhmm);
  if (parsed === null) {
    return hhmm;
  }
  const h = Math.floor(parsed / 60);
  const m = parsed % 60;
  const hour12 = ((h + 11) % 12) + 1;
  const ampm = h >= 12 ? 'PM' : 'AM';
  return `${hour12}:${String(m).padStart(2, '0')} ${ampm}`;
}

export function parseTimeToMinutes(hhmm: string): number | null {
  const parts = hhmm.trim().split(':');
  if (parts.length < 2) {
    return null;
  }
  const h = Number(parts[0]);
  const mi = Number(parts[1]);
  if (!Number.isFinite(h) || !Number.isFinite(mi)) {
    return null;
  }
  return h * 60 + mi;
}

/** Hours between two same-day HH:mm strings. */
export function hoursBetweenSameDay(start: string, end: string): number {
  const a = parseTimeToMinutes(start);
  const b = parseTimeToMinutes(end);
  if (a === null || b === null) {
    return NaN;
  }
  return (b - a) / 60;
}

export function safeNumber(value: unknown, fallback = 0): number {
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export function toIsoDateLocal(d: Date): string {
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${mo}-${day}`;
}

/** For “today”, only show slots at or after the next 30-minute boundary from now. */
export function filterSlotsNotBeforeNow(slots: TimeSlotOption[], dateIso: string, now: Date = new Date()): TimeSlotOption[] {
  if (dateIso !== toIsoDateLocal(now)) {
    return slots;
  }
  const cur = now.getHours() * 60 + now.getMinutes();
  const boundary = Math.ceil(cur / 30) * 30;
  return slots.filter(s => {
    const m = parseTimeToMinutes(s.value);
    return m !== null && m >= boundary;
  });
}
