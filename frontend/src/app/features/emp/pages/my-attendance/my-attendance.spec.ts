import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MyAttendance } from './my-attendance';
import { provideStandaloneComponentTestProviders } from '../../../../../testing/standalone-test-helpers';

describe('MyAttendance', () => {
  let component: MyAttendance;
  let fixture: ComponentFixture<MyAttendance>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MyAttendance],
      providers: provideStandaloneComponentTestProviders()
    }).compileComponents();

    fixture = TestBed.createComponent(MyAttendance);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
