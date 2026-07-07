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

      // Construct Date object in Asia/Kolkata timezone to avoid client-side timezone mismatches
      const now = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
      const newState = { ...currentState };

      // 1. If Working, increment Worked Time
      if (newState.isWorking) {
        newState.totalWorkedSeconds++;
      }

      // 2. Update Shift Elapsed, Remaining Time, and Shift Total dynamically for Overtime or Standard shift
      if (newState.overtimeApproved) {
        const limitHour = newState.overtimeExtended ? 22 : 20;
        const overtimeEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), limitHour, 0, 0);
        const overtimeStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 18, 0, 0);
        const totalOvertimeSeconds = (limitHour - 18) * 3600;

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
        newState.shiftTotalSeconds = 9 * 3600;
        newState.shiftElapsedSeconds = this.calculateShiftElapsed(now);
        const secondsUntilShiftEnd = this.calculateSecondsUntilShiftEnd(now);
        newState.remainingSeconds = Math.max(0, secondsUntilShiftEnd - newState.approvedSeconds);
      }

      this.stateSubject.next(newState);
    });
  }

  public updateState(state: TodayAttendanceState) {
    this.stateSubject.next(state);
  }

  private calculateShiftElapsed(now: Date): number {
    const shiftStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 9, 0, 0);
    const shiftEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 18, 0, 0);
    const totalShiftSeconds = 9 * 3600;

    if (now < shiftStart) return 0;
    if (now > shiftEnd) return totalShiftSeconds;
    
    return Math.floor((now.getTime() - shiftStart.getTime()) / 1000);
  }

  private calculateSecondsUntilShiftEnd(now: Date): number {
    const shiftEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 18, 0, 0);
    if (now >= shiftEnd) return 0;
    return Math.max(0, Math.floor((shiftEnd.getTime() - now.getTime()) / 1000));
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
