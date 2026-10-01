import { Component, Input, Output, EventEmitter, forwardRef, ElementRef, HostListener, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';

export interface CalendarDay {
  date: Date;
  isoString: string; // YYYY-MM-DD
  dayNumber: number;
  isCurrentMonth: boolean;
  isToday: boolean;
  isSelected: boolean;
  isDisabled: boolean;
}

@Component({
  selector: 'app-custom-datepicker',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './custom-datepicker.html',
  styleUrl: './custom-datepicker.css',
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => CustomDatepickerComponent),
      multi: true
    }
  ]
})
export class CustomDatepickerComponent implements ControlValueAccessor, OnInit {
  @Input() placeholder: string = 'Select Date';
  @Input() disabled: boolean = false;
  @Input() inputId: string = '';
  @Input() min: string = '';
  @Input() max: string = '';
  
  @Input() value: string = ''; // YYYY-MM-DD
  @Output() valueChange = new EventEmitter<string>();

  isOpen = false;
  viewMode: 'days' | 'months' | 'years' = 'days';
  currentViewDate = new Date();
  selectedPickerYear = new Date().getFullYear();
  
  calendarDays: CalendarDay[] = [];
  weekDays = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
  monthList = [
    { name: 'January', short: 'Jan' },
    { name: 'February', short: 'Feb' },
    { name: 'March', short: 'Mar' },
    { name: 'April', short: 'Apr' },
    { name: 'May', short: 'May' },
    { name: 'June', short: 'Jun' },
    { name: 'July', short: 'Jul' },
    { name: 'August', short: 'Aug' },
    { name: 'September', short: 'Sep' },
    { name: 'October', short: 'Oct' },
    { name: 'November', short: 'Nov' },
    { name: 'December', short: 'Dec' }
  ];
  
  yearsGrid: number[] = [];

  onChange: any = () => {};
  onTouched: any = () => {};

  constructor(private eRef: ElementRef) {}

  ngOnInit(): void {
    if (this.value) {
      const parts = this.value.split('-');
      if (parts.length === 3) {
        this.currentViewDate = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
      }
    }
    this.selectedPickerYear = this.currentViewDate.getFullYear();
    this.generateCalendar();
    this.generateYearsGrid(this.selectedPickerYear);
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.eRef.nativeElement.contains(event.target)) {
      this.isOpen = false;
      this.viewMode = 'days';
    }
  }

  get formattedDisplay(): string {
    if (!this.value) return this.placeholder;
    const parts = this.value.split('-');
    if (parts.length === 3) {
      const year = parts[0];
      const month = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const d = new Date(parseInt(year), month, day);
      if (!isNaN(d.getTime())) {
        return d.toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' });
      }
    }
    return this.value;
  }

  get currentMonthYearLabel(): string {
    return this.currentViewDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  }

  get currentMonthShortLabel(): string {
    return this.currentViewDate.toLocaleDateString('en-US', { month: 'short' });
  }

  openUpward = false;
  alignRight = false;

  togglePicker(): void {
    if (this.disabled) return;
    this.isOpen = !this.isOpen;
    if (this.isOpen) {
      this.viewMode = 'days';
      this.calculatePlacement();
      if (this.value) {
        const parts = this.value.split('-');
        if (parts.length === 3) {
          this.currentViewDate = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, 1);
        }
      }
      this.selectedPickerYear = this.currentViewDate.getFullYear();
      this.generateCalendar();
      this.generateYearsGrid(this.selectedPickerYear);
    }
  }

  private calculatePlacement(): void {
    try {
      const trigger = this.eRef.nativeElement.querySelector('.datepicker-trigger');
      if (trigger) {
        const rect = trigger.getBoundingClientRect();
        const spaceBelow = window.innerHeight - rect.bottom;
        const spaceAbove = rect.top;

        // Check if datepicker is inside a modal or dialog container
        const modal = trigger.closest('.modal-card, .modal-dialog, .modal-content, [class*="modal"]');
        if (modal) {
          const modalRect = modal.getBoundingClientRect();
          const spaceAboveInModal = rect.top - modalRect.top;
          // In a modal, never open upward unless there is ample room (>320px) inside the modal above the input
          if (spaceAboveInModal < 320) {
            this.openUpward = false;
          } else {
            this.openUpward = spaceBelow < 330 && spaceAboveInModal >= 320;
          }
        } else {
          // Standard page flow: calendar popup is ~330px high
          this.openUpward = spaceBelow < 330 && spaceAbove > 340;
        }

        // Align right if calendar card (~280px wide) would overflow viewport on the right
        this.alignRight = (rect.left + 290) > window.innerWidth;
      }
    } catch {
      this.openUpward = false;
      this.alignRight = false;
    }
  }

  toggleMonthYearPicker(event: Event): void {
    event.stopPropagation();
    if (this.viewMode === 'days') {
      this.viewMode = 'months';
      this.selectedPickerYear = this.currentViewDate.getFullYear();
    } else if (this.viewMode === 'months') {
      this.viewMode = 'years';
      this.generateYearsGrid(this.selectedPickerYear);
    } else {
      this.viewMode = 'days';
    }
  }

  prevMonth(event: Event): void {
    event.stopPropagation();
    if (this.viewMode === 'days') {
      this.currentViewDate = new Date(this.currentViewDate.getFullYear(), this.currentViewDate.getMonth() - 1, 1);
      this.selectedPickerYear = this.currentViewDate.getFullYear();
      this.generateCalendar();
    } else if (this.viewMode === 'months') {
      this.selectedPickerYear--;
    } else if (this.viewMode === 'years') {
      this.generateYearsGrid(this.yearsGrid[0] - 12);
    }
  }

  nextMonth(event: Event): void {
    event.stopPropagation();
    if (this.viewMode === 'days') {
      this.currentViewDate = new Date(this.currentViewDate.getFullYear(), this.currentViewDate.getMonth() + 1, 1);
      this.selectedPickerYear = this.currentViewDate.getFullYear();
      this.generateCalendar();
    } else if (this.viewMode === 'months') {
      this.selectedPickerYear++;
    } else if (this.viewMode === 'years') {
      this.generateYearsGrid(this.yearsGrid[this.yearsGrid.length - 1] + 1);
    }
  }

  selectMonth(monthIndex: number, event: Event): void {
    event.stopPropagation();
    this.currentViewDate = new Date(this.selectedPickerYear, monthIndex, 1);
    this.viewMode = 'days';
    this.generateCalendar();
  }

  selectYear(year: number, event: Event): void {
    event.stopPropagation();
    this.selectedPickerYear = year;
    this.viewMode = 'months';
  }

  selectToday(event: Event): void {
    event.stopPropagation();
    const today = new Date();
    const iso = this.toIsoString(today);
    this.selectDate(iso);
  }

  clearDate(event: Event): void {
    event.stopPropagation();
    this.value = '';
    this.onChange('');
    this.onTouched();
    this.valueChange.emit('');
    this.isOpen = false;
    this.viewMode = 'days';
    this.generateCalendar();
  }

  selectDay(day: CalendarDay, event: Event): void {
    event.stopPropagation();
    if (day.isDisabled) return;
    this.selectDate(day.isoString);
  }

  private selectDate(iso: string): void {
    this.value = iso;
    this.onChange(this.value);
    this.onTouched();
    this.valueChange.emit(this.value);
    this.isOpen = false;
    this.viewMode = 'days';
    this.generateCalendar();
  }

  generateCalendar(): void {
    const year = this.currentViewDate.getFullYear();
    const month = this.currentViewDate.getMonth();

    const firstDayOfMonth = new Date(year, month, 1);
    const lastDayOfMonth = new Date(year, month + 1, 0);

    const startDayOfWeek = firstDayOfMonth.getDay();
    const totalDaysInMonth = lastDayOfMonth.getDate();

    const todayIso = this.toIsoString(new Date());
    const days: CalendarDay[] = [];

    // Previous month padding days
    const prevMonthLastDay = new Date(year, month, 0).getDate();
    for (let i = startDayOfWeek - 1; i >= 0; i--) {
      const prevDate = new Date(year, month - 1, prevMonthLastDay - i);
      const iso = this.toIsoString(prevDate);
      days.push({
        date: prevDate,
        isoString: iso,
        dayNumber: prevDate.getDate(),
        isCurrentMonth: false,
        isToday: iso === todayIso,
        isSelected: iso === this.value,
        isDisabled: this.isDateDisabled(iso)
      });
    }

    // Current month days
    for (let d = 1; d <= totalDaysInMonth; d++) {
      const currDate = new Date(year, month, d);
      const iso = this.toIsoString(currDate);
      days.push({
        date: currDate,
        isoString: iso,
        dayNumber: d,
        isCurrentMonth: true,
        isToday: iso === todayIso,
        isSelected: iso === this.value,
        isDisabled: this.isDateDisabled(iso)
      });
    }

    // Next month padding days to complete 35 or 42 grid cells (avoiding extra redundant 6th row)
    const targetCells = days.length > 35 ? 42 : (days.length > 28 ? 35 : 28);
    const remainingCells = targetCells - days.length;
    for (let i = 1; i <= remainingCells; i++) {
      const nextDate = new Date(year, month + 1, i);
      const iso = this.toIsoString(nextDate);
      days.push({
        date: nextDate,
        isoString: iso,
        dayNumber: i,
        isCurrentMonth: false,
        isToday: iso === todayIso,
        isSelected: iso === this.value,
        isDisabled: this.isDateDisabled(iso)
      });
    }

    this.calendarDays = days;
  }

  private generateYearsGrid(centerYear: number): void {
    const startYear = centerYear - 5;
    const years: number[] = [];
    for (let i = 0; i < 12; i++) {
      years.push(startYear + i);
    }
    this.yearsGrid = years;
  }

  private isDateDisabled(iso: string): boolean {
    if (this.min && iso < this.min) return true;
    if (this.max && iso > this.max) return true;
    return false;
  }

  private toIsoString(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  // ControlValueAccessor methods
  writeValue(val: any): void {
    this.value = val || '';
    if (this.value) {
      const parts = this.value.split('-');
      if (parts.length === 3) {
        this.currentViewDate = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, 1);
        this.selectedPickerYear = this.currentViewDate.getFullYear();
      }
    }
    this.generateCalendar();
  }

  registerOnChange(fn: any): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: any): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
  }
}
