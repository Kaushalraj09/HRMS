import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MasterSidebar } from './master-sidebar';

describe('MasterSidebar', () => {
  let component: MasterSidebar;
  let fixture: ComponentFixture<MasterSidebar>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MasterSidebar],
    }).compileComponents();

    fixture = TestBed.createComponent(MasterSidebar);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
