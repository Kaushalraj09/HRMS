import { Component, OnInit, OnDestroy, AfterViewInit, ElementRef, ViewChild, Inject, PLATFORM_ID, ViewEncapsulation, Input, Output, EventEmitter, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Subscription, interval } from 'rxjs';
import { startWith, switchMap } from 'rxjs/operators';
import { environment } from '../../../../../environments/environment';

import * as L from 'leaflet';

export interface EmployeeLocation {
  employeeId?: number;
  employee_id?: number;
  employeeName: string;
  employee_name?: string;
  designation?: string;
  department?: string;
  latitude: number;
  longitude: number;
  city: string;
  state: string;
  punchInTime?: string | null;
  punch_in_time?: string | null;
  punchOutTime?: string | null;
  punch_out_time?: string | null;
  workMode: 'FIELD' | 'OFFICE' | 'REMOTE' | string;
  work_mode?: 'FIELD' | 'OFFICE' | 'REMOTE' | string;
  status: 'ACTIVE' | 'WORKING' | 'PUNCHED_OUT' | 'LATE' | 'ON_LEAVE' | 'ABSENT' | string;
}

export interface CityHubCluster {
  city: string;
  count: number;
  lat: number;
  lng: number;
  colorClass: string;
  employees: EmployeeLocation[];
}

@Component({
  selector: 'app-employee-location-map',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './employee-location-map.html',
  styleUrls: ['./employee-location-map.css'],
  encapsulation: ViewEncapsulation.None
})
export class EmployeeLocationMap implements OnInit, OnDestroy, AfterViewInit, OnChanges {
  @ViewChild('mapContainer', { static: false }) mapContainer!: ElementRef;

  @Input() filter: string = 'ALL';
  @Output() filterChange = new EventEmitter<string>();

  private map!: L.Map;
  private markersLayerGroup = L.layerGroup();
  private refreshSub!: Subscription;
  private isBrowser: boolean;

  allLocations: EmployeeLocation[] = [];
  filteredLocations: EmployeeLocation[] = [];
  cityHubs: CityHubCluster[] = [];
  loading = false;
  error = '';

  private cityColorMap: Record<string, string> = {
    'delhi': 'hub-delhi',
    'new delhi': 'hub-delhi',
    'pune': 'hub-pune',
    'mumbai': 'hub-mumbai',
    'hyderabad': 'hub-hyderabad',
    'bengaluru': 'hub-bengaluru',
    'bangalore': 'hub-bengaluru',
    'sasaram': 'hub-teal',
    'rohtas': 'hub-teal',
    'indore': 'hub-orange',
    'gaya': 'hub-teal',
    'kolkata': 'hub-purple',
    'chennai': 'hub-delhi'
  };

  private colorPalette = ['hub-teal', 'hub-delhi', 'hub-orange', 'hub-mumbai', 'hub-pune', 'hub-hyderabad', 'hub-bengaluru'];

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
      setTimeout(() => {
        this.initMap();
      }, 80);
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['filter']) {
      this.applyFilterAndRender();
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

  clearFilter(): void {
    this.filter = 'ALL';
    this.filterChange.emit('ALL');
    this.applyFilterAndRender();
  }

  getFilterLabel(): string {
    const f = (this.filter || 'ALL').toUpperCase();
    if (f === 'PRESENT') return 'Present';
    if (f === 'WORKING') return 'Working';
    if (f === 'ON_LEAVE' || f === 'LEAVE') return 'On Leave';
    if (f === 'ABSENT') return 'Absent';
    return 'All';
  }

  getFilterColorClass(): string {
    const f = (this.filter || 'ALL').toUpperCase();
    if (f === 'PRESENT') return 'dot-green';
    if (f === 'WORKING') return 'dot-blue';
    if (f === 'ON_LEAVE' || f === 'LEAVE') return 'dot-orange';
    if (f === 'ABSENT') return 'dot-red';
    return 'dot-gray';
  }

  private getFilterSubLabel(count: number): string {
    const f = (this.filter || 'ALL').toUpperCase();
    const plural = count === 1 ? 'Employee' : 'Employees';
    if (f === 'PRESENT') return `${plural} Present`;
    if (f === 'WORKING') return `${plural} Working`;
    if (f === 'ON_LEAVE' || f === 'LEAVE') return `${plural} On Leave`;
    if (f === 'ABSENT') return `${plural} Absent`;
    return plural;
  }

  private initMap(): void {
    if (!this.mapContainer || !this.mapContainer.nativeElement) return;

    const bounds = L.latLngBounds([6.0, 68.0], [37.5, 97.5]);
    
    this.map = L.map(this.mapContainer.nativeElement, {
      center: [21.5, 79.2],
      zoom: 4.5,
      zoomSnap: 0.1,
      minZoom: 3.5,
      maxZoom: 18,
      maxBounds: bounds,
      maxBoundsViscosity: 0.8,
      zoomControl: true,
      attributionControl: false
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      maxZoom: 18,
      subdomains: 'abcd'
    }).addTo(this.map);

    this.map.addLayer(this.markersLayerGroup);

    this.applyFilterAndRender();
  }

  private startPolling(): void {
    const apiUrl = `${environment.apiBaseUrl}/attendance/today-locations`;
    this.loading = true;

    this.refreshSub = interval(30000)
      .pipe(
        startWith(0),
        switchMap(() => {
          return this.http.get<any[]>(apiUrl);
        })
      )
      .subscribe({
        next: (data) => {
          this.loading = false;
          this.error = '';
          if (data && Array.isArray(data)) {
            this.allLocations = data.map(item => ({
              employeeId: item.employeeId ?? item.employee_id,
              employeeName: item.employeeName ?? item.employee_name ?? 'Employee',
              designation: item.designation || 'Team Member',
              department: item.department || '',
              latitude: Number(item.latitude),
              longitude: Number(item.longitude),
              city: item.city || 'Office',
              state: item.state || 'India',
              punchInTime: item.punchInTime ?? item.punch_in_time,
              punchOutTime: item.punchOutTime ?? item.punch_out_time,
              workMode: item.workMode ?? item.work_mode ?? 'OFFICE',
              status: (item.status || 'ACTIVE').toUpperCase()
            }));

            this.applyFilterAndRender();
          }
          this.refreshMapSize();
        },
        error: (err) => {
          this.loading = false;
          this.error = 'Failed to load employee locations';
          this.refreshMapSize();
        }
      });
  }

  applyFilterAndRender(): void {
    const f = (this.filter || 'ALL').toUpperCase();
    if (f === 'ALL') {
      this.filteredLocations = this.allLocations;
    } else if (f === 'PRESENT') {
      this.filteredLocations = this.allLocations.filter(loc => {
        const s = (loc.status || '').toUpperCase();
        return s === 'ACTIVE' || s === 'WORKING' || s === 'LATE' || s === 'PUNCHED_OUT' || !!loc.punchInTime;
      });
    } else if (f === 'WORKING') {
      this.filteredLocations = this.allLocations.filter(loc => {
        const s = (loc.status || '').toUpperCase();
        return (s === 'ACTIVE' || s === 'WORKING' || s === 'LATE') && !loc.punchOutTime;
      });
    } else if (f === 'ON_LEAVE' || f === 'LEAVE') {
      this.filteredLocations = this.allLocations.filter(loc => {
        const s = (loc.status || '').toUpperCase();
        return s === 'ON_LEAVE' || s === 'LEAVE';
      });
    } else if (f === 'ABSENT') {
      this.filteredLocations = this.allLocations.filter(loc => {
        const s = (loc.status || '').toUpperCase();
        return s === 'ABSENT';
      });
    } else {
      this.filteredLocations = this.allLocations;
    }

    this.groupLocationsIntoCityHubs();
    this.renderAllCityMarkers();
  }

  private groupLocationsIntoCityHubs(): void {
    const cityMap = new Map<string, { city: string; latSum: number; lngSum: number; employees: EmployeeLocation[] }>();

    this.filteredLocations.forEach(loc => {
      const cityName = (loc.city || 'Office').trim();
      const cityKey = cityName.toLowerCase();

      if (!cityMap.has(cityKey)) {
        cityMap.set(cityKey, {
          city: cityName,
          latSum: 0,
          lngSum: 0,
          employees: []
        });
      }

      const entry = cityMap.get(cityKey)!;
      entry.latSum += loc.latitude;
      entry.lngSum += loc.longitude;
      entry.employees.push(loc);
    });

    let colorIdx = 0;
    this.cityHubs = Array.from(cityMap.values()).map(entry => {
      const cityKey = entry.city.toLowerCase();
      const colorClass = this.cityColorMap[cityKey] || this.colorPalette[colorIdx % this.colorPalette.length];
      colorIdx++;

      const count = entry.employees.length;
      return {
        city: entry.city,
        count: count,
        lat: entry.latSum / count,
        lng: entry.lngSum / count,
        colorClass: colorClass,
        employees: entry.employees
      };
    });
  }

  private renderAllCityMarkers(): void {
    if (!this.map) return;

    this.markersLayerGroup.clearLayers();

    if (this.cityHubs.length === 0) {
      this.fitIndiaView();
      return;
    }

    const bounds = L.latLngBounds([]);

    this.cityHubs.forEach(hub => {
      // 1. Teardrop Pin Marker with count & glowing aura
      const hubIcon = L.divIcon({
        className: 'city-hub-div-icon',
        html: `
          <div class="city-hub-circle ${hub.colorClass}">
            <span class="hub-city-name">${hub.city}</span>
            <span class="hub-city-count">${hub.count}</span>
          </div>
        `,
        iconSize: [50, 56],
        iconAnchor: [25, 54]
      });

      const marker = L.marker([hub.lat, hub.lng], { icon: hubIcon });

      // 2. Rich Hover Tooltip Popup showing every employee in this location
      const empRows = hub.employees.map(emp => {
        const initials = (emp.employeeName || 'Emp').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        const modeClass = (emp.workMode || 'office').toLowerCase();
        const s = (emp.status || 'ACTIVE').toUpperCase();
        
        let statusBadgeHtml = '';
        let timeInfoHtml = '';

        if (s === 'ON_LEAVE' || s === 'LEAVE') {
          statusBadgeHtml = '<span class="popup-status on_leave">On Leave</span>';
          timeInfoHtml = '<span class="popup-time"><i class="fas fa-calendar-alt"></i> Leave</span>';
        } else if (s === 'ABSENT') {
          statusBadgeHtml = '<span class="popup-status absent">Absent</span>';
          timeInfoHtml = '<span class="popup-time"><i class="fas fa-user-times"></i> Not Punched</span>';
        } else if (s === 'PUNCHED_OUT') {
          statusBadgeHtml = '<span class="popup-status punched_out">Punched Out</span>';
          timeInfoHtml = `<span class="popup-time"><i class="far fa-clock"></i> ${emp.punchInTime || '-'} - ${emp.punchOutTime || '-'}</span>`;
        } else if (s === 'LATE') {
          statusBadgeHtml = '<span class="popup-status late">Late</span>';
          timeInfoHtml = `<span class="popup-time"><i class="far fa-clock"></i> ${emp.punchInTime || 'Working'}</span>`;
        } else {
          statusBadgeHtml = '<span class="popup-status active">Working</span>';
          timeInfoHtml = `<span class="popup-time"><i class="far fa-clock"></i> ${emp.punchInTime || 'Working'}</span>`;
        }

        return `
          <div class="popup-emp-row">
            <div class="popup-emp-avatar">${initials}</div>
            <div class="popup-emp-info">
              <div class="popup-emp-name">${emp.employeeName}</div>
              <div class="popup-emp-meta">
                ${timeInfoHtml}
                <span class="popup-pill ${modeClass}">${emp.workMode}</span>
                ${statusBadgeHtml}
              </div>
            </div>
          </div>
        `;
      }).join('');

      const popupHtml = `
        <div class="custom-map-popup">
          <div class="popup-header">
            <span class="popup-city-title">📍 ${hub.city}</span>
            <span class="popup-city-sub">${hub.count} ${this.getFilterSubLabel(hub.count)}</span>
          </div>
          <div class="popup-emp-list">
            ${empRows}
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml, {
        offset: L.point(0, -48),
        className: 'custom-leaflet-popup',
        closeButton: false,
        autoPan: false
      });

      marker.on('mouseover', () => {
        marker.openPopup();
      });
      marker.on('mouseout', () => {
        marker.closePopup();
      });

      marker.on('click', () => {
        this.map.flyTo([hub.lat, hub.lng], 8, { duration: 0.6 });
      });

      this.markersLayerGroup.addLayer(marker);
      bounds.extend([hub.lat, hub.lng]);
    });

    if (bounds.isValid()) {
      if (this.cityHubs.length === 1) {
        this.map.setView([this.cityHubs[0].lat, this.cityHubs[0].lng], 6.5);
      } else {
        this.map.fitBounds(bounds.pad(0.35), { maxZoom: 8 });
      }
    } else {
      this.fitIndiaView();
    }

    this.refreshMapSize();
  }

  private fitIndiaView(): void {
    if (!this.map) return;
    this.map.setView([21.5, 79.2], 4.5);
    this.refreshMapSize();
  }

  private refreshMapSize(): void {
    if (!this.map) return;
    setTimeout(() => {
      if (this.map) {
        this.map.invalidateSize();
      }
    }, 100);
  }
}
