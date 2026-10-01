import { Component, AfterViewInit, OnDestroy, ViewChild, ElementRef, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chart } from 'chart.js/auto';

export interface AttendanceStatusData {
  present: number;
  leave: number;
  absent: number;
  late: number;
  presentPct: string;
  leavePct: string;
  absentPct: string;
  latePct: string;
}

@Component({
  selector: 'app-attendance-status-chart',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './attendance-status-chart.html',
  styleUrls: ['./attendance-status-chart.css']
})
export class AttendanceStatusChartComponent implements AfterViewInit, OnDestroy, OnChanges {
  @ViewChild('chartCanvas') chartCanvas!: ElementRef<HTMLCanvasElement>;

  @Input() data: AttendanceStatusData = {
    present: 35,
    leave: 5,
    absent: 2,
    late: 4,
    presentPct: '83.3%',
    leavePct: '11.9%',
    absentPct: '4.8%',
    latePct: '9.5%'
  };

  private chartInstance: Chart | null = null;

  ngAfterViewInit(): void {
    this.createChart();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['data'] && !changes['data'].firstChange) {
      this.updateChart();
    }
  }

  private createChart(): void {
    if (!this.chartCanvas) return;
    const ctx = this.chartCanvas.nativeElement.getContext('2d');
    if (!ctx) return;

    if (this.chartInstance) {
      this.chartInstance.destroy();
    }

    this.chartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Present', 'Leave', 'Absent', 'Late'],
        datasets: [
          {
            data: [
              this.data.present,
              this.data.leave,
              this.data.absent,
              this.data.late
            ],
            backgroundColor: [
              '#22A06B', // Present green
              '#F5B942', // Leave amber
              '#EF5350', // Absent red
              '#F59E0B'  // Late orange
            ],
            hoverBackgroundColor: [
              '#1E8D5E',
              '#E5A934',
              '#DC3545',
              '#D97706'
            ],
            borderWidth: 2,
            borderColor: '#FFFFFF',
            hoverOffset: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '74%',
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: '#1E293B',
            titleColor: '#FFFFFF',
            bodyColor: '#F8FAFC',
            padding: 8,
            cornerRadius: 6,
            callbacks: {
              label: (context) => {
                const label = context.label || '';
                const value = context.parsed || 0;
                let pct = '';
                if (label === 'Present') pct = this.data.presentPct;
                else if (label === 'Leave') pct = this.data.leavePct;
                else if (label === 'Absent') pct = this.data.absentPct;
                else if (label === 'Late') pct = this.data.latePct;
                return ` ${label}: ${value} (${pct})`;
              }
            }
          }
        },
        animation: {
          duration: 600
        }
      }
    });
  }

  private updateChart(): void {
    if (!this.chartInstance) {
      this.createChart();
      return;
    }
    this.chartInstance.data.datasets[0].data = [
      this.data.present,
      this.data.leave,
      this.data.absent,
      this.data.late
    ];
    this.chartInstance.update();
  }

  ngOnDestroy(): void {
    if (this.chartInstance) {
      this.chartInstance.destroy();
      this.chartInstance = null;
    }
  }
}
