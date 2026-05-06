export const SHIFT_START_SECONDS = 9 * 3600;
export const SHIFT_END_SECONDS = 18 * 3600;
export const SHIFT_TOTAL_SECONDS = SHIFT_END_SECONDS - SHIFT_START_SECONDS;

export function parseTimeToSeconds(value: string | null | undefined): number {
  if (!value) {
    return 0;
  }
  const [hours = '0', minutes = '0', seconds = '0'] = value.split(':');
  return Number(hours) * 3600 + Number(minutes) * 60 + Number(seconds);
}

export function secondsSinceMidnight(date: Date): number {
  return date.getHours() * 3600 + date.getMinutes() * 60 + date.getSeconds();
}

export function getShiftElapsedSeconds(now: Date): number {
  const currentSeconds = secondsSinceMidnight(now);
  if (currentSeconds <= SHIFT_START_SECONDS) {
    return 0;
  }
  if (currentSeconds >= SHIFT_END_SECONDS) {
    return SHIFT_TOTAL_SECONDS;
  }
  return currentSeconds - SHIFT_START_SECONDS;
}

export function getShiftProgress(now: Date): number {
  return getShiftElapsedSeconds(now) / SHIFT_TOTAL_SECONDS;
}

export function clampSeconds(value: number, min = 0, max = Number.MAX_SAFE_INTEGER): number {
  return Math.min(max, Math.max(min, Math.floor(Number.isFinite(value) ? value : 0)));
}

export function formatSecondsToClock(totalSeconds: number): string {
  const safeSeconds = clampSeconds(totalSeconds);
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const seconds = safeSeconds % 60;
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

export function secondsToHourFloat(totalSeconds: number): number {
  return clampSeconds(totalSeconds) / 3600;
}
