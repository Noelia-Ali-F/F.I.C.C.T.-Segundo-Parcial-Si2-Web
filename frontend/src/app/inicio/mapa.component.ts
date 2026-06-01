import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { AfterViewInit, Component, ElementRef, ViewChild, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { API_BASE_URL } from '../shared/api-base';

declare const L: any;

type WorkshopMapItem = {
  id: number;
  workshop_name: string;
  contact_name: string;
  phone: string;
  email: string;
  zone: string;
  specialty: string;
  latitude: number | null;
  longitude: number | null;
  timezone: string | null;
  utc_offset_minutes: number | null;
  created_at: string;
};

@Component({
  selector: 'app-map-page',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <main class="page">
      <section class="section-hero map-hero">
        <div>
          <p class="eyebrow">Mapa</p>
          <h1>Talleres registrados en el mapa</h1>
          <p class="lead">
            Mostramos los puntos guardados en la columna de ubicación del registro de talleres y
            destacamos la especialidad principal de cada uno.
          </p>
        </div>

        <div class="map-hero-card">
          <span>Cobertura real</span>
          <strong>{{ mappedWorkshops.length }} puntos con coordenadas</strong>
          <p>
            Cada marcador usa la ubicación registrada y muestra la especialidad del taller al hacer
            clic.
          </p>
        </div>
      </section>

      <section class="map-layout">
        <div class="map-frame">
          <div #mapCanvas class="map-canvas" aria-label="Mapa de talleres registrados"></div>

          <div class="map-overlay-message" *ngIf="isLoading">
            Cargando ubicaciones de talleres...
          </div>

          <div class="map-overlay-message error" *ngIf="!isLoading && loadError">
            {{ loadError }}
          </div>

          <div class="map-overlay-message" *ngIf="!isLoading && !loadError && !mappedWorkshops.length">
            No hay talleres con coordenadas registradas para mostrar en el mapa.
          </div>
        </div>

        <aside class="map-sidebar">
          <article class="map-note">
            <p class="eyebrow">Referencia</p>
            <h2>Puntos desde “Registra tu taller mecánico”</h2>
            <p>
              El mapa consume los datos de la API de talleres y pinta solo los registros que tienen
              latitud y longitud válidas.
            </p>
          </article>

          <article class="map-stat">
            <span>Especialidades</span>
            <strong>{{ specialtiesCount }}</strong>
          </article>

          <article class="map-stat">
            <span>Último punto</span>
            <strong>{{ selectedWorkshop?.specialty || 'Sin selección' }}</strong>
            <p *ngIf="selectedWorkshop">
              {{ selectedWorkshop.workshop_name }} · {{ selectedWorkshop.zone }}
            </p>
          </article>

          <article class="map-stat">
            <span>Acción</span>
            <a class="button primary" routerLink="/dashboard">Ver registros</a>
          </article>

          <article class="map-list-card" *ngIf="mappedWorkshops.length">
            <div class="map-list-head">
              <span>Talleres ubicados</span>
              <strong>{{ mappedWorkshops.length }}</strong>
            </div>

            <button
              class="map-list-item"
              type="button"
              *ngFor="let workshop of mappedWorkshops"
              (click)="focusWorkshop(workshop)"
            >
              <strong>{{ workshop.specialty }}</strong>
              <span>{{ workshop.workshop_name }}</span>
              <small>{{ workshop.latitude | number: '1.4-4' }}, {{ workshop.longitude | number: '1.4-4' }}</small>
            </button>
          </article>
        </aside>
      </section>
    </main>
  `,
  styleUrl: '../shared/shared-pages.css',
})
export class MapPageComponent implements AfterViewInit {
  private readonly http = inject(HttpClient);
  private readonly workshopsApiUrl = `${API_BASE_URL}/workshops`;

  @ViewChild('mapCanvas', { static: true })
  private readonly mapCanvasRef?: ElementRef<HTMLDivElement>;

  workshops: WorkshopMapItem[] = [];
  isLoading = true;
  loadError = '';
  selectedWorkshop: WorkshopMapItem | null = null;

  private map?: any;
  private markersLayer?: any;

  get mappedWorkshops(): WorkshopMapItem[] {
    return this.workshops.filter(
      (workshop) => typeof workshop.latitude === 'number' && typeof workshop.longitude === 'number',
    );
  }

  get specialtiesCount(): number {
    return new Set(this.mappedWorkshops.map((workshop) => workshop.specialty).filter(Boolean)).size;
  }

  ngAfterViewInit(): void {
    this.initializeMap();
    this.loadWorkshops();
    this.scheduleMapResize();
  }

  focusWorkshop(workshop: WorkshopMapItem): void {
    if (!this.map || workshop.latitude === null || workshop.longitude === null) {
      return;
    }

    this.selectedWorkshop = workshop;
    this.map.setView([workshop.latitude, workshop.longitude], 15, { animate: true });
    this.scheduleMapResize();
  }

  private initializeMap(): void {
    const element = this.mapCanvasRef?.nativeElement;

    if (!element || typeof L === 'undefined') {
      this.loadError = 'No se pudo inicializar el mapa.';
      this.isLoading = false;
      return;
    }

    this.map = L.map(element, {
      zoomControl: true,
      scrollWheelZoom: true,
    }).setView([-17.7833, -63.1821], 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(this.map);

    this.markersLayer = L.layerGroup().addTo(this.map);
    this.scheduleMapResize();
  }

  private loadWorkshops(): void {
    this.isLoading = true;
    this.loadError = '';

    this.http.get<WorkshopMapItem[]>(this.workshopsApiUrl).subscribe({
      next: (workshops) => {
        this.workshops = workshops;
        this.renderWorkshopMarkers();
        this.isLoading = false;
        this.scheduleMapResize();
      },
      error: () => {
        this.isLoading = false;
        this.loadError = 'No se pudieron cargar los talleres registrados desde la API.';
      },
    });
  }

  private renderWorkshopMarkers(): void {
    if (!this.map || !this.markersLayer) {
      return;
    }

    this.markersLayer.clearLayers();

    const workshops = this.mappedWorkshops;

    if (!workshops.length) {
      this.selectedWorkshop = null;
      this.map.setView([-17.7833, -63.1821], 12);
      this.scheduleMapResize();
      return;
    }

    const bounds: [number, number][] = [];

    workshops.forEach((workshop) => {
      const { latitude, longitude } = workshop;

      if (latitude === null || longitude === null) {
        return;
      }

      bounds.push([latitude, longitude]);

      const marker = L.marker([latitude, longitude]).addTo(this.markersLayer);
      marker.bindPopup(`
        <strong>${this.escapeHtml(workshop.specialty)}</strong><br>
        ${this.escapeHtml(workshop.workshop_name)}<br>
        ${this.escapeHtml(workshop.zone)}
      `);

      marker.on('click', () => {
        this.selectedWorkshop = workshop;
      });
    });

    this.selectedWorkshop = workshops[0];

    if (bounds.length === 1) {
      this.map.setView(bounds[0], 15);
      this.scheduleMapResize();
      return;
    }

    this.map.fitBounds(bounds, {
      padding: [30, 30],
      maxZoom: 15,
    });
    this.scheduleMapResize();
  }

  private escapeHtml(value: string): string {
    return value
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  private scheduleMapResize(): void {
    if (!this.map) {
      return;
    }

    requestAnimationFrame(() => {
      this.map?.invalidateSize();

      setTimeout(() => {
        this.map?.invalidateSize();
      }, 150);
    });
  }
}
