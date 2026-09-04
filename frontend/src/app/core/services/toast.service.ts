import { Injectable, NgZone } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  type: ToastType;
  title: string;
  message: string;
  duration: number;
  isClosing?: boolean;
}

export interface ToastOptions {
  title?: string;
  duration?: number;
}

@Injectable({
  providedIn: 'root'
})
export class ToastService {
  private readonly toastsSubject = new BehaviorSubject<ToastItem[]>([]);
  public readonly toasts$: Observable<ToastItem[]> = this.toastsSubject.asObservable();

  private activeTimeouts = new Map<string, any>();
  private recentMessages = new Map<string, number>();

  constructor(private readonly ngZone: NgZone) {}

  public showSuccess(message: string, title?: string, duration: number = 4500): string | null {
    return this.show('success', message, { title: title || 'Success', duration });
  }

  public showError(message: string, title?: string, duration: number = 6500): string | null {
    return this.show('error', message, { title: title || 'Error', duration });
  }

  public showWarning(message: string, title?: string, duration: number = 5000): string | null {
    return this.show('warning', message, { title: title || 'Warning', duration });
  }

  public showInfo(message: string, title?: string, duration: number = 4500): string | null {
    return this.show('info', message, { title: title || 'Notice', duration });
  }

  public show(type: ToastType, message: string, options?: ToastOptions): string | null {
    if (!message || !message.trim()) {
      return null;
    }

    const cleanMessage = message.trim();
    const now = Date.now();
    const dedupKey = `${type}:${cleanMessage}`;

    // Suppress duplicates emitted within 1500ms
    const lastSeen = this.recentMessages.get(dedupKey);
    if (lastSeen && (now - lastSeen) < 1500) {
      return null;
    }
    this.recentMessages.set(dedupKey, now);

    const id = `toast-${now}-${Math.random().toString(36).slice(2, 7)}`;
    const duration = options?.duration ?? (type === 'error' ? 6500 : 4500);
    const title = options?.title ?? this.getDefaultTitle(type);

    const toast: ToastItem = {
      id,
      type,
      title,
      message: cleanMessage,
      duration,
      isClosing: false
    };

    this.ngZone.run(() => {
      // New notifications stack at the top (or prepended)
      const current = this.toastsSubject.value;
      this.toastsSubject.next([toast, ...current]);

      if (duration > 0) {
        const timeout = setTimeout(() => {
          this.dismiss(id);
        }, duration);
        this.activeTimeouts.set(id, timeout);
      }
    });

    return id;
  }

  public dismiss(id: string): void {
    const current = this.toastsSubject.value;
    const target = current.find(t => t.id === id);
    if (!target) return;

    if (this.activeTimeouts.has(id)) {
      clearTimeout(this.activeTimeouts.get(id));
      this.activeTimeouts.delete(id);
    }

    this.ngZone.run(() => {
      // Mark as closing for smooth exit animation
      this.toastsSubject.next(
        this.toastsSubject.value.map(t => t.id === id ? { ...t, isClosing: true } : t)
      );

      // Remove after animation completes (250ms)
      setTimeout(() => {
        this.ngZone.run(() => {
          this.toastsSubject.next(this.toastsSubject.value.filter(t => t.id !== id));
        });
      }, 250);
    });
  }

  public clear(): void {
    this.activeTimeouts.forEach(t => clearTimeout(t));
    this.activeTimeouts.clear();
    this.toastsSubject.next([]);
  }

  private getDefaultTitle(type: ToastType): string {
    switch (type) {
      case 'success': return 'Success';
      case 'error': return 'Error';
      case 'warning': return 'Warning';
      case 'info': return 'Notice';
      default: return 'Notification';
    }
  }
}
