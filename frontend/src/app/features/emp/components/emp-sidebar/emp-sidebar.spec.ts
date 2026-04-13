import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EmpSidebar } from './emp-sidebar';

describe('EmpSidebar', () => {
  let component: EmpSidebar;
  let fixture: ComponentFixture<EmpSidebar>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EmpSidebar],
    }).compileComponents();

    fixture = TestBed.createComponent(EmpSidebar);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
