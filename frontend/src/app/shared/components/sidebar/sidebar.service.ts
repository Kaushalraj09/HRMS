import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root' 
})
export class SidebarService {
  private sidebarOpenSubject = new BehaviorSubject<boolean>(true);
  
  isSidebarOpen$ = this.sidebarOpenSubject.asObservable();

  constructor() { }

  toggleSidebar(): void {
    this.sidebarOpenSubject.next(!this.sidebarOpenSubject.value);
  }

  setSidebarState(isOpen: boolean): void {
    this.sidebarOpenSubject.next(isOpen);
  }
}
