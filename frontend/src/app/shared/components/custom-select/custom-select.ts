import { Component, Input, Output, EventEmitter, forwardRef, HostListener, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';

export interface SelectOption {
  label: string;
  value: any;
}

@Component({
  selector: 'app-custom-select',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './custom-select.html',
  styleUrl: './custom-select.css',
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => CustomSelectComponent),
      multi: true
    }
  ]
})
export class CustomSelectComponent implements ControlValueAccessor {
  @Input() options: SelectOption[] = [];
  @Input() placeholder: string = 'Select an option';
  @Input() disabled: boolean = false;
  
  // To bind when not explicitly applying formControl objects
  @Input() value: any = null;
  @Output() valueChange = new EventEmitter<any>();

  isOpen = false;
  
  onChange: any = () => {};
  onTouched: any = () => {};

  constructor(private eRef: ElementRef) {}

  get currentLabel(): string {
    const selected = this.options.find(opt => opt.value === this.value);
    return selected ? selected.label : this.placeholder;
  }

  toggleDropdown() {
    if (this.disabled) return;
    this.isOpen = !this.isOpen;
  }

  selectOption(option: SelectOption) {
    this.value = option.value;
    this.onChange(this.value);
    this.onTouched();
    this.valueChange.emit(this.value);
    this.isOpen = false;
  }

  // ControlValueAccessor methods
  writeValue(obj: any): void {
    if (obj !== undefined) {
      this.value = obj;
    }
  }

  registerOnChange(fn: any): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: any): void {
    this.onTouched = fn;
  }

  setDisabledState?(isDisabled: boolean): void {
    this.disabled = isDisabled;
    if (isDisabled) this.isOpen = false;
  }

  @HostListener('document:click', ['$event'])
  clickout(event: Event) {
    if (!this.eRef.nativeElement.contains(event.target)) {
      this.isOpen = false;
    }
  }
}
