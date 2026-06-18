import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MasterDashboard } from './master-dashboard';
import { provideStandaloneComponentTestProviders } from '../../../testing/standalone-test-helpers';

describe('MasterDashboard', () => {
  let component: MasterDashboard;
  let fixture: ComponentFixture<MasterDashboard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MasterDashboard],
      providers: provideStandaloneComponentTestProviders()
    }).compileComponents();

    fixture = TestBed.createComponent(MasterDashboard);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
