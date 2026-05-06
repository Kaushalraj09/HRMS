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

      const now = new Date();
      const newState = { ...currentState };

      // 1. Update Shift Elapsed
      newState.shiftElapsedSeconds = this.calculateShiftElapsed(now);

      // 2. If Working, increment Worked Time
      if (newState.isWorking) {
        newState.totalWorkedSeconds++;
      }

      // 3. Recalculate Remaining Time = (Shift End - Now) - Approved
      const secondsUntilShiftEnd = this.calculateSecondsUntilShiftEnd(now);
      newState.remainingSeconds = Math.max(0, secondsUntilShiftEnd - newState.approvedSeconds);

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
