import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet,MatFormFieldModule,MatSelectModule],
  templateUrl: './app.html',
  styleUrls: ['./app.css']
})
export class App {
  protected readonly title = signal('frontend');
}
