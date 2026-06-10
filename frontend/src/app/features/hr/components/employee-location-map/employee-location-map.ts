import { Component, OnInit, OnDestroy, AfterViewInit, ElementRef, ViewChild, Inject, PLATFORM_ID, ViewEncapsulation } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Subscription, interval } from 'rxjs';
import { startWith, switchMap } from 'rxjs/operators';

import * as L from 'leaflet';
import 'leaflet.markercluster';

interface EmployeeLocation {
  employeeId: number;
  employeeName: string;
  latitude: number;
  longitude: number;
  city: string;
  state: string;
  punchInTime: string | null;
  punchOutTime: string | null;
  workMode: 'FIELD' | 'OFFICE' | 'REMOTE';
  status: 'ACTIVE' | 'PUNCHED_OUT' | 'LATE';
}

@Component({
  selector: 'app-employee-location-map',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './employee-location-map.html',
  styleUrls: ['./employee-location-map.css'],
  encapsulation: ViewEncapsulation.None
})
export class EmployeeLocationMap implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild('mapContainer', { static: false }) mapContainer!: ElementRef;

  private map!: L.Map;
  private markerClusterGroup!: L.MarkerClusterGroup;
  private refreshSub!: Subscription;
  private isBrowser: boolean;

  allLocations: EmployeeLocation[] = [];
  filteredLocations: EmployeeLocation[] = [];
  loading = true;
  error = '';
  activeFilter = 'ALL';

  stats = {
    totalWorking: 0,
    currentlyActive: 0,
    fieldEmployees: 0,
    punchedOut: 0,
    lateArrivals: 0
  };

  constructor(
    private http: HttpClient,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {
    this.isBrowser = isPlatformBrowser(this.platformId);
  }

  ngOnInit(): void {
    if (this.isBrowser) {
      this.startPolling();
    }
  }

  ngAfterViewInit(): void {
    if (this.isBrowser) {
      this.initMap();
    }
  }

  ngOnDestroy(): void {
    if (this.refreshSub) {
      this.refreshSub.unsubscribe();
    }
    if (this.map) {
      this.map.remove();
    }
  }

  private initMap(): void {
    const bounds = L.latLngBounds([6.5, 68.0], [37.5, 97.5]);
    
    this.map = L.map(this.mapContainer.nativeElement, {
      center: [22.5937, 78.9629],
      zoom: 5,
      minZoom: 4,
      maxZoom: 18,
      maxBounds: bounds,
      maxBoundsViscosity: 1.0,
      zoomControl: true,
      attributionControl: false
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      maxZoom: 18
    }).addTo(this.map);

    this.markerClusterGroup = (L as any).markerClusterGroup({
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      maxClusterRadius: 40
    });

    this.map.addLayer(this.markerClusterGroup);
  }

  private startPolling(): void {
    const apiUrl = 'http://localhost:8000/api/v1/attendance/today-locations';

    this.refreshSub = interval(60000)
      .pipe(
        startWith(0),
        switchMap(() => {
          return this.http.get<EmployeeLocation[]>(apiUrl);
        })
      )
      .subscribe({
        next: (data) => {
          this.allLocations = data || [];
          this.calculateStats();
          this.applyFilter(this.activeFilter);
          this.loading = false;
          this.error = '';
        },
        error: (err) => {
          console.error('Failed to fetch today locations:', err);
          this.error = 'Failed to load employee locations.';
          this.loading = false;
        }
      });
  }

  calculateStats(): void {
    this.stats.totalWorking = this.allLocations.length;
    this.stats.currentlyActive = this.allLocations.filter(l => l.status === 'ACTIVE' || l.status === 'LATE').length;
    this.stats.fieldEmployees = this.allLocations.filter(l => l.workMode === 'FIELD').length;
    this.stats.punchedOut = this.allLocations.filter(l => l.status === 'PUNCHED_OUT').length;
    this.stats.lateArrivals = this.allLocations.filter(l => l.status === 'LATE').length;
  }

  setFilter(filter: string): void {
    this.activeFilter = filter;
    this.applyFilter(filter);
  }

  private applyFilter(filter: string): void {
    if (filter === 'ALL') {
      this.filteredLocations = this.allLocations;
    } else if (filter === 'ACTIVE') {
      this.filteredLocations = this.allLocations.filter(l => l.status === 'ACTIVE' || l.status === 'LATE');
    } else if (filter === 'FIELD') {
      this.filteredLocations = this.allLocations.filter(l => l.workMode === 'FIELD');
    } else if (filter === 'LATE') {
      this.filteredLocations = this.allLocations.filter(l => l.status === 'LATE');
    } else if (filter === 'PUNCHED_OUT') {
      this.filteredLocations = this.allLocations.filter(l => l.status === 'PUNCHED_OUT');
    }

    if (this.isBrowser && this.map) {
      this.updateMarkers();
    }
  }

  private updateMarkers(): void {
    this.markerClusterGroup.clearLayers();

    this.filteredLocations.forEach(loc => {
      let colorClass = 'marker-green';
      if (loc.workMode === 'FIELD') {
        colorClass = 'marker-blue';
      } else if (loc.status === 'PUNCHED_OUT') {
        colorClass = 'marker-red';
      } else if (loc.status === 'LATE') {
        colorClass = 'marker-orange';
      }

      const customIcon = L.divIcon({
        className: 'custom-div-icon',
        html: `<div class="marker-pin ${colorClass}">
                 <div class="marker-inner"></div>
               </div>`,
        iconSize: [30, 42],
        iconAnchor: [15, 42]
      });

      const tooltipContent = `
        <div class="map-tooltip">
          <div class="tooltip-header">
            <h4>${loc.employeeName}</h4>
            <span class="badge ${loc.workMode.toLowerCase()}">${loc.workMode}</span>
          </div>
          <div class="tooltip-body">
            <p><strong>Status:</strong> <span class="status-text ${loc.status.toLowerCase()}">${loc.status.replace('_', ' ')}</span></p>
            <p><strong>Location:</strong> ${loc.city}, ${loc.state}</p>
            <p><strong>Punch In:</strong> ${loc.punchInTime || 'N/A'}</p>
            ${loc.punchOutTime ? `<p><strong>Punch Out:</strong> ${loc.punchOutTime}</p>` : ''}
          </div>
        </div>
      `;

      const marker = L.marker([loc.latitude, loc.longitude], { icon: customIcon });
      marker.bindPopup(tooltipContent, {
        closeButton: false,
        offset: L.point(0, -32)
      });

      this.markerClusterGroup.addLayer(marker);
    });
  }
}
