import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, interval, Subscription } from 'rxjs';
import { TodayAttendanceState } from '../models/attendance.model';

@Injectable({
  providedIn: 'root'
})
export class TimeEngineService implements OnDestroy {
  private stateSubject = new BehaviorSubject<TodayAttendanceState | null>(null);
  public state$ = this.stateSubject.asObservable();
  
  private timerSub: Subscription | null = null;

  constructor() {
    this.startEngine();
  }

  private startEngine() {
    this.timerSub = interval(1000).subscribe(() => {
      const currentState = this.stateSubject.value;
      if (!currentState) return;

      const now = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
      const newState = { ...currentState };

      // 1. If Working, increment Worked Time
      if (newState.isWorking) {
        newState.totalWorkedSeconds++;
      }

      // 2. Dynamic shift timing evaluation
      if (!newState.shiftStart || !newState.shiftEnd) return;
      const shiftStart = this.parseShiftTime(now, newState.shiftStart);
      const shiftEnd = this.parseShiftTime(now, newState.shiftEnd);

      if (newState.overtimeApproved) {
        const maxOtMinutes = newState.maxOvertimeMinutes || 120;
        const overtimeStart = newState.overtimeStartTime ? this.parseShiftTime(now, newState.overtimeStartTime) : shiftEnd;
        const multiplier = newState.overtimeExtended ? 2 : 1;
        const overtimeEnd = new Date(overtimeStart.getTime() + (maxOtMinutes * 60 * 1000 * multiplier));
        const totalOvertimeSeconds = Math.max(0, Math.floor((overtimeEnd.getTime() - overtimeStart.getTime()) / 1000));

        newState.shiftTotalSeconds = totalOvertimeSeconds;

        if (now < overtimeStart) {
          newState.remainingSeconds = totalOvertimeSeconds;
          newState.shiftElapsedSeconds = 0;
        } else if (now > overtimeEnd) {
          newState.remainingSeconds = 0;
          newState.shiftElapsedSeconds = totalOvertimeSeconds;
        } else {
          newState.remainingSeconds = Math.max(0, Math.floor((overtimeEnd.getTime() - now.getTime()) / 1000));
          newState.shiftElapsedSeconds = Math.floor((now.getTime() - overtimeStart.getTime()) / 1000);
        }
      } else {
        const totalSec = Math.max(0, Math.floor((shiftEnd.getTime() - shiftStart.getTime()) / 1000));
        newState.shiftTotalSeconds = newState.shiftTotalSeconds || (totalSec > 0 ? totalSec : 28800);

        if (now < shiftStart) {
          newState.shiftElapsedSeconds = 0;
          newState.remainingSeconds = newState.shiftTotalSeconds;
        } else if (now > shiftEnd) {
          newState.shiftElapsedSeconds = newState.shiftTotalSeconds;
          newState.remainingSeconds = 0;
        } else {
          newState.shiftElapsedSeconds = Math.floor((now.getTime() - shiftStart.getTime()) / 1000);
          const secondsUntilEnd = Math.max(0, Math.floor((shiftEnd.getTime() - now.getTime()) / 1000));
          newState.remainingSeconds = Math.max(0, secondsUntilEnd - newState.approvedSeconds);
        }
      }

      this.stateSubject.next(newState);
    });
  }

  private parseShiftTime(referenceDate: Date, timeStr: string): Date {
    const dt = new Date(referenceDate);
    if (!timeStr) return dt;

    let hours = 0;
    let minutes = 0;

    const ampmMatch = timeStr.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);
    if (ampmMatch) {
      hours = parseInt(ampmMatch[1], 10);
      minutes = parseInt(ampmMatch[2], 10);
      const mer = ampmMatch[3].toUpperCase();
      if (mer === 'PM' && hours < 12) hours += 12;
      if (mer === 'AM' && hours === 12) hours = 0;
    } else {
      const parts = timeStr.split(':');
      if (parts.length >= 2) {
        hours = parseInt(parts[0], 10);
        minutes = parseInt(parts[1], 10);
      }
    }

    dt.setHours(hours, minutes, 0, 0);
    return dt;
  }

  public updateState(state: TodayAttendanceState) {
    this.stateSubject.next(state);
  }

  public formatHHMMSS(seconds: number): string {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return [h, m, s].map(v => v < 10 ? '0' + v : v).join(':');
  }

  ngOnDestroy() {
    if (this.timerSub) {
      this.timerSub.unsubscribe();
    }
  }
}
