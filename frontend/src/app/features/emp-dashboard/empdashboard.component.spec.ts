import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EmpDashboardComponent } from './empdashboard.component';

describe('EmpDashboardComponent', () => {
  let component: EmpDashboardComponent;
  let fixture: ComponentFixture<EmpDashboardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EmpDashboardComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(EmpDashboardComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
