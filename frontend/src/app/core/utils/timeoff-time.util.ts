export interface TimeSlotOption {
  value: string;
  label: string;
}

/** Build 30-minute slot values from start_time through end_time inclusive. */
export function buildHalfHourSlots(startStr: string = '00:00', endStr: string = '23:59'): TimeSlotOption[] {
  const slots: TimeSlotOption[] = [];
  
  const startMins = parseTimeToMinutes(startStr) || 0;
  const endMins = parseTimeToMinutes(endStr) || 1439;
  
  // Align to next 30 min boundary for start
  let currentMins = Math.ceil(startMins / 30) * 30;
  
  while (currentMins <= endMins) {
    const h = Math.floor(currentMins / 60) % 24;
    const m = currentMins % 60;
    const value = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
    slots.push({ value, label: formatTimeLabel(value) });
    currentMins += 30;
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
