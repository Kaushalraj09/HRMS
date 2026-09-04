import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { GlobalToastComponent } from './shared/components/global-toast/global-toast.component';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, MatFormFieldModule, MatSelectModule, GlobalToastComponent],
  templateUrl: './app.html',
  styleUrls: ['./app.css']
})
export class App {
  protected readonly title = signal('HRMS');
}
