import { Component, AfterViewInit, OnDestroy, ViewChild, ElementRef, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Chart } from 'chart.js/auto';
import { ManagerService } from '../../../../core/services/manager.service';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select/custom-select';

@Component({
  selector: 'app-attendance-trend-chart',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent],
  templateUrl: './attendance-trend-chart.html',
  styleUrls: ['./attendance-trend-chart.css']
})
export class AttendanceTrendChartComponent implements AfterViewInit, OnDestroy {
  @ViewChild('trendCanvas') trendCanvas!: ElementRef<HTMLCanvasElement>;

  selectedPeriod = 'This Month';
  periods = ['Today', 'This Month', 'Last Month'];
  periodOptions: SelectOption[] = [
    { label: 'Today', value: 'Today' },
    { label: 'This Month', value: 'This Month' },
    { label: 'Last Month', value: 'Last Month' }
  ];
  isLoading = false;

  chartInstance: Chart | null = null;

  constructor(
    private readonly managerService: ManagerService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngAfterViewInit(): void {
    this.loadTrendData();
  }

  onPeriodChange(newPeriod?: string): void {
    if (newPeriod) {
      this.selectedPeriod = newPeriod;
    }
    this.loadTrendData();
  }

  loadTrendData(): void {
    this.isLoading = true;
    this.managerService.getAttendanceTrend(this.selectedPeriod).subscribe({
      next: (res) => {
        this.isLoading = false;
        if (!this.chartInstance) {
          this.createChart(res.labels, res.present, res.leave, res.absent);
        } else {
          this.chartInstance.data.labels = res.labels;
          this.chartInstance.data.datasets[0].data = res.present;
          this.chartInstance.data.datasets[1].data = res.leave;
          this.chartInstance.data.datasets[2].data = res.absent;
          this.chartInstance.update();
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Failed to load live attendance trend:', err);
        this.isLoading = false;
        if (!this.chartInstance) {
          const month = new Date().toLocaleString('en-US', { month: 'short' });
          const dynamicLabels = [`1 ${month}`, `5 ${month}`, `10 ${month}`, `15 ${month}`, `20 ${month}`, `25 ${month}`, `30 ${month}`];
          this.createChart(dynamicLabels, [0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0]);
        }
        this.cdr.detectChanges();
      }
    });
  }

  private createChart(labels: string[], present: number[], leave: number[], absent: number[]): void {
    if (!this.trendCanvas) return;
    const ctx = this.trendCanvas.nativeElement.getContext('2d');
    if (!ctx) return;

    if (this.chartInstance) {
      this.chartInstance.destroy();
    }

    const grad = ctx.createLinearGradient(0, 0, 0, 200);
    grad.addColorStop(0, 'rgba(34, 160, 107, 0.16)');
    grad.addColorStop(1, 'rgba(34, 160, 107, 0.00)');

    this.chartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Present',
            data: present,
            borderColor: '#22A06B',
            backgroundColor: grad,
            fill: true,
            tension: 0.35,
            borderWidth: 2.2,
            pointBackgroundColor: '#22A06B',
            pointBorderColor: '#FFFFFF',
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6
          },
          {
            label: 'Leave',
            data: leave,
            borderColor: '#F5B942',
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.35,
            borderWidth: 2,
            pointBackgroundColor: '#F5B942',
            pointBorderColor: '#FFFFFF',
            pointBorderWidth: 2,
            pointRadius: 3.5,
            pointHoverRadius: 5.5
          },
          {
            label: 'Absent',
            data: absent,
            borderColor: '#EF5350',
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.35,
            borderWidth: 2,
            pointBackgroundColor: '#EF5350',
            pointBorderColor: '#FFFFFF',
            pointBorderWidth: 2,
            pointRadius: 3.5,
            pointHoverRadius: 5.5
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: '#0F172A',
            titleColor: '#F8FAFC',
            bodyColor: '#CBD5E1',
            padding: 10,
            cornerRadius: 8,
            boxPadding: 4,
            usePointStyle: true,
            callbacks: {
              label: (context) => ` ${context.dataset.label}: ${context.parsed.y}%`
            }
          }
        },
        scales: {
          x: {
            grid: {
              display: false
            },
            ticks: {
              color: '#94A3B8',
              font: {
                size: 11,
                family: "'Inter', sans-serif"
              }
            },
            border: {
              color: '#E2E8F0'
            }
          },
          y: {
            min: 0,
            max: 100,
            ticks: {
              stepSize: 20,
              color: '#94A3B8',
              font: {
                size: 11,
                family: "'Inter', sans-serif"
              },
              callback: (val) => `${val}%`
            },
            grid: {
              color: '#F1F5F9'
            },
            border: {
              dash: [4, 4],
              color: 'transparent'
            }
          }
        }
      }
    });
  }

  ngOnDestroy(): void {
    if (this.chartInstance) {
      this.chartInstance.destroy();
      this.chartInstance = null;
    }
  }
}
