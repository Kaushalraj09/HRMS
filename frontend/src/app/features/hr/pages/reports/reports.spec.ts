import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HRReportsComponent } from './reports';
import { provideStandaloneComponentTestProviders } from '../../../../../testing/standalone-test-helpers';

describe('HRReportsComponent', () => {
  let component: HRReportsComponent;
  let fixture: ComponentFixture<HRReportsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HRReportsComponent],
      providers: provideStandaloneComponentTestProviders()
    }).compileComponents();

    fixture = TestBed.createComponent(HRReportsComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
