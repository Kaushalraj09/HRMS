import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root' 
})
export class EmpSidebarService {
  private empSidebarOpenSubject = new BehaviorSubject<boolean>(true);
  
  isEmpSidebarOpen$ = this.empSidebarOpenSubject.asObservable();

  constructor() { }

  toggleSidebar(): void {
    this.empSidebarOpenSubject.next(!this.empSidebarOpenSubject.value);
  }

  setSidebarState(isOpen: boolean): void {
    this.empSidebarOpenSubject.next(isOpen);
  }
}
