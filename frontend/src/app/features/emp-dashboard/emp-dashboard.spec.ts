import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EmpDashboard } from './emp-dashboard';

describe('EmpDashboardComponent', () => {
  let component: EmpDashboard;
  let fixture: ComponentFixture<EmpDashboard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EmpDashboard],
    }).compileComponents();

    fixture = TestBed.createComponent(EmpDashboard);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
