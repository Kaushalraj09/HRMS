import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs/internal/BehaviorSubject';

@Injectable({
  providedIn: 'root',
})
export class HrSidebarService {
    private hrSidebarOpenSubject = new BehaviorSubject<boolean>(true);
    
    isHrSidebarOpen$ = this.hrSidebarOpenSubject.asObservable();
  
    constructor() { }
  
    toggleSidebar(): void {
      this.hrSidebarOpenSubject.next(!this.hrSidebarOpenSubject.value);
    }
  
    setSidebarState(isOpen: boolean): void {
      this.hrSidebarOpenSubject.next(isOpen);
    }
  }
  
