import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ManagerSidebarService {
  private readonly sidebarOpenSubject = new BehaviorSubject<boolean>(
    typeof window !== 'undefined' ? window.innerWidth > 768 : true
  );
  readonly isSidebarOpen$ = this.sidebarOpenSubject.asObservable();

  toggleSidebar(): void {
    this.sidebarOpenSubject.next(!this.sidebarOpenSubject.value);
  }

  setSidebarState(isOpen: boolean): void {
    this.sidebarOpenSubject.next(isOpen);
  }
}
