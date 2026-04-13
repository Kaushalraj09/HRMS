import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HrSidebar } from './hr-sidebar';

describe('HrSidebar', () => {
  let component: HrSidebar;
  let fixture: ComponentFixture<HrSidebar>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HrSidebar],
    }).compileComponents();

    fixture = TestBed.createComponent(HrSidebar);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
