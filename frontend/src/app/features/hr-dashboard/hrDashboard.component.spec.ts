import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HrDashboardComponent } from './hrDashboard.component';

describe('HrDashboardComponent', () => {
  let component: HrDashboardComponent;
  let fixture: ComponentFixture<HrDashboardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HrDashboardComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(HrDashboardComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
