/**
 * Attendance Calculation Utilities
 * 
 * Requirements:
 * - Shift: 9 Hours (including 55m break)
 * - Break: Fixed 55 Minutes
 */

export const FIXED_BREAK_MINUTES = 55;
export const REQUIRED_SHIFT_MINUTES = 540; // 9 hours

/**
 * Calculate actual worked time (excluding break)
 * Formula: (Total Duration) - 55 Minutes
 */
export function calculateWorkedTime(totalMinutes: number): number {
    return Math.max(0, totalMinutes - FIXED_BREAK_MINUTES);
}

/**
 * Calculate overtime
 * Formula: Total Duration - 9 Hours (if duration > 9h)
 */
export function calculateOvertime(totalMinutes: number): number {
    return Math.max(0, totalMinutes - REQUIRED_SHIFT_MINUTES);
}

/**
 * Calculate Grand Total
 * Formula: Actual Working Time + Overtime
 */
export function calculateGrandTotal(workedMinutes: number, overtimeMinutes: number): number {
    return workedMinutes + overtimeMinutes;
}

/**
 * Format minutes to human-readable string (e.g., 8h 5m)
 */
export function formatMinutesToHours(minutes: number | null | undefined): string {
    if (minutes === null || minutes === undefined || isNaN(minutes)) return '-';
    if (minutes === 0) return '0h 0m';
    
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return `${h}h ${m}m`;
}

/**
 * Parse time string (HH:mm:ss) to total minutes from midnight
 */
export function timeStringToMinutes(timeStr: string | null | undefined): number | null {
    if (!timeStr) return null;
    const parts = timeStr.split(':');
    if (parts.length < 2) return null;
    return parseInt(parts[0]) * 60 + parseInt(parts[1]);
}
