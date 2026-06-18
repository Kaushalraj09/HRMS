import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EmpDashboard } from './emp-dashboard';
import { provideStandaloneComponentTestProviders } from '../../../../../testing/standalone-test-helpers';

describe('EmpDashboardComponent', () => {
  let component: EmpDashboard;
  let fixture: ComponentFixture<EmpDashboard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EmpDashboard],
      providers: provideStandaloneComponentTestProviders()
    }).compileComponents();

    fixture = TestBed.createComponent(EmpDashboard);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
