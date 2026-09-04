import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService, ToastItem } from '../../../core/services/toast.service';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-global-toast',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './global-toast.component.html',
  styleUrls: ['./global-toast.component.css']
})
export class GlobalToastComponent {
  public readonly toasts$: Observable<ToastItem[]>;

  constructor(private readonly toastService: ToastService) {
    this.toasts$ = this.toastService.toasts$;
  }

  public dismiss(id: string, event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    this.toastService.dismiss(id);
  }

  public trackById(_index: number, item: ToastItem): string {
    return item.id;
  }

  public getIconClass(type: string): string {
    switch (type) {
      case 'success': return 'fas fa-check';
      case 'error': return 'fas fa-exclamation';
      case 'warning': return 'fas fa-exclamation-triangle';
      case 'info': return 'fas fa-info';
      default: return 'fas fa-bell';
    }
  }

  public getRole(type: string): string {
    return type === 'error' ? 'alert' : 'status';
  }

  public getAriaLive(type: string): string {
    return type === 'error' ? 'assertive' : 'polite';
  }
}
