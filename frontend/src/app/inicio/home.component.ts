import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { AfterViewInit, Component, ElementRef, ViewChild, inject } from '@angular/core';
import { FormsModule, NgForm, NgModel } from '@angular/forms';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { RouterLink } from '@angular/router';
import { API_BASE_URL } from '../shared/api-base';
import { AlertSuccessComponent } from '../shared/alert-success.component';
import { ValidationDialogComponent } from '../shared/validation-dialog.component';

declare const L: any;

type HeroBenefit = {
  title: string;
  description: string;
  icon: string;
};

@Component({
  selector: 'app-home-page',
  standalone: true,
  imports: [AlertSuccessComponent, CommonModule, FormsModule, MatDialogModule, RouterLink],
  template: `
    <main class="home-showcase">
      <section class="hero-banner">
        <div class="hero-overlay"></div>

        <div class="hero-grid">
          <div class="hero-copy">
            <p class="hero-kicker">Plataforma SaaS para empresas de auxilio</p>
            <h1>REGISTRA TU EMPRESA Y ADMINISTRA TU RED DE SUCURSALES</h1>

            <article class="register-card">
              <p class="card-eyebrow">Registro oficial</p>
              <h2>Registrar mi empresa</h2>
              <p class="card-lead">
                Crea tu tenant, define sucursales reales, habilita técnicos y opera emergencias y
                cotizaciones desde un solo panel.
              </p>
              <div class="register-form">
                <p class="terms-copy" style="margin-bottom: 1.25rem;">
                  El alta pública real de empresas se realiza desde <strong>/registro-taller</strong>.
                  La gestión operativa de talleres queda dentro de <strong>Mis Sucursales</strong>.
                </p>

                <div class="form-actions">
                  <a class="cta-primary" routerLink="/registro-taller">Registrar mi empresa</a>
                  <a class="cta-secondary" routerLink="/contacto">Solicitar asesoría</a>
                </div>
              </div>
            </article>
          </div>

          <div class="hero-side">
            <div class="hero-side-copy">
              <p class="hero-intro">
                Impulsa tu taller con clientes verificados, solicitudes de auxilio en tiempo real y acompañamiento comercial desde el primer día.
              </p>
              <p class="hero-highlight">
                <span>Más clientes, más servicios,</span>
                <span>más oportunidades</span>
                <span class="light">para crecer</span>
              </p>
            </div>

            <div class="mechanic-spotlight" aria-hidden="true">
              <div class="spotlight-halo"></div>
              <div class="mechanic-card">
                <div class="mechanic-tag">Servicio 24/7</div>
                <div class="mechanic-portrait"></div>
              </div>
            </div>

            <aside class="contact-card">
              <p class="contact-kicker">Atención inmediata</p>
              <h2>¿Tienes preguntas? ¡Contáctanos!</h2>

              <a class="contact-action phone" href="tel:800163316">
                <span class="icon">☎</span>
                <span class="contact-text">
                  <strong>800 16 3316</strong>
                  <small>Línea gratuita</small>
                </span>
              </a>

              <a class="contact-action whatsapp" href="https://wa.me/59177795636" target="_blank" rel="noreferrer">
                <span class="icon">W</span>
                <span class="contact-text">
                  <strong>777 95 636</strong>
                  <small>Por WhatsApp</small>
                </span>
              </a>
            </aside>
          </div>
        </div>
      </section>

      <section class="benefits-panel">
        <div class="benefits-head">
          <p class="benefits-kicker">Crecimiento para talleres aliados</p>
          <h2>Beneficios de unirte a nuestra red</h2>
        </div>

        <div class="benefits-grid">
          <article class="benefit-card" *ngFor="let benefit of benefits">
            <span class="benefit-icon">{{ benefit.icon }}</span>
            <div>
              <h3>{{ benefit.title }}</h3>
              <p>{{ benefit.description }}</p>
            </div>
          </article>
        </div>
      </section>
    </main>

    <app-alert-success
      *ngIf="submitState === 'success'"
      [title]="'Solicitud enviada correctamente'"
      [message]="'Tu solicitud ha sido enviada correctamente. Nuestro equipo está revisando la información de tu taller.'"
    ></app-alert-success>
  `,
  styleUrl: './home.component.css',
})
export class HomePageComponent implements AfterViewInit {
  private readonly http = inject(HttpClient);
  private readonly dialog = inject(MatDialog);
  private readonly apiUrl = `${API_BASE_URL}/workshops`;
  private successMessageTimeout?: ReturnType<typeof setTimeout>;
  readonly isSecureContext = window.isSecureContext;

  @ViewChild('workshopMap', { static: true })
  private readonly workshopMapRef?: ElementRef<HTMLDivElement>;

  private mapInstance?: any;
  private mapMarker?: any;

  selectedLatitude = -17.7833;
  selectedLongitude = -63.1821;
  isLocationChosen = false;
  readonly userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  readonly userUtcOffsetMinutes = new Date().getTimezoneOffset() * -1;
  isLocating = false;
  locationMessage = '';
  showLocationError = false;

  readonly form = {
    workshopName: '',
    contactName: '',
    phone: '',
    email: '',
    zone: '',
    specialty: '',
  };

  isSubmitting = false;
  submitState: 'idle' | 'success' | 'error' = 'idle';
  submitMessage = '';

  readonly workshopZones = [
    'zona norte',
    'zona sur',
    'zona este',
    'zona oeste',
    'zona centro',
  ];

  readonly specialties = [
    'Batería',
    'Neumático',
    'Combustible',
    'Motor',
    'Sistema eléctrico',
    'Accidente',
    'Cerrajería / llaves',
  ];

  readonly benefits: HeroBenefit[] = [
    {
      title: 'Oportunidades constantes',
      description: 'Recibe solicitudes de asistencia en tiempo real y mejora la ocupación diaria de tu taller.',
      icon: '◉',
    },
    {
      title: 'Acceso a IA avanzada',
      description: 'Diagnóstico rápido automatizado para evaluar emergencias y asignar prioridad.',
      icon: '◎',
    },
    {
      title: 'Expansión de clientes',
      description: 'Incrementa tu visibilidad y tu base de clientes con emergencias locales.',
      icon: '◌',
    },
  ];

  ngAfterViewInit(): void {
    if (!this.workshopMapRef || typeof L === 'undefined') {
      return;
    }

    this.mapInstance = L.map(this.workshopMapRef.nativeElement, {
      center: [this.selectedLatitude, this.selectedLongitude],
      zoom: 13,
      scrollWheelZoom: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(this.mapInstance);

    this.mapMarker = L.marker([this.selectedLatitude, this.selectedLongitude], {
      draggable: true,
    }).addTo(this.mapInstance);

    this.mapMarker.on('dragend', () => {
      const position = this.mapMarker.getLatLng();
      this.updateSelectedLocation(position.lat, position.lng);
    });

    this.mapInstance.on('click', (event: { latlng: { lat: number; lng: number } }) => {
      this.mapMarker.setLatLng(event.latlng);
      this.updateSelectedLocation(event.latlng.lat, event.latlng.lng);
    });
  }

  submitWorkshop(workshopForm: NgForm): void {
    if (this.isSubmitting) {
      return;
    }

    const missingFields = this.getMissingFields(!!workshopForm.invalid);

    if (missingFields.length > 0) {
      this.showLocationError = true;
      this.openValidationDialog(missingFields);
      return;
    }

    this.isSubmitting = true;
    this.submitState = 'idle';
    this.submitMessage = '';

    this.http
      .post(this.apiUrl, {
        workshop_name: this.form.workshopName.trim(),
        contact_name: this.form.contactName.trim(),
        phone: this.form.phone.trim(),
        email: this.form.email.trim(),
        zone: this.form.zone,
        specialty: this.form.specialty,
        latitude: this.selectedLatitude,
        longitude: this.selectedLongitude,
        timezone: this.userTimezone,
        utc_offset_minutes: this.userUtcOffsetMinutes,
      })
      .subscribe({
        next: () => {
          this.isSubmitting = false;
          this.submitState = 'success';
          workshopForm.resetForm({
            workshopName: '',
            contactName: '',
            phone: '',
            email: '',
            zone: '',
            specialty: '',
          });
          this.isLocationChosen = false;
          this.showLocationError = false;
          this.locationMessage = '';
          this.scheduleSuccessMessageHide();
        },
        error: (error: HttpErrorResponse) => {
          this.isSubmitting = false;
          this.submitState = 'error';
          this.submitMessage =
            error.error?.detail || 'No se pudo registrar el taller. Verifica el backend e inténtalo otra vez.';
        },
      });
  }

  locateCurrentPosition(): void {
    this.locationMessage = '';

    if (!this.isSecureContext) {
      this.locationMessage =
        'La ubicación automática del navegador solo funciona en HTTPS o en localhost. En esta URL usa el mapa manualmente o abre el sitio con HTTPS.';
      return;
    }

    if (!navigator.geolocation) {
      this.locationMessage = 'Tu navegador no soporta geolocalización.';
      return;
    }

    this.isLocating = true;

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;

        this.updateSelectedLocation(latitude, longitude);

        if (this.mapMarker) {
          this.mapMarker.setLatLng([latitude, longitude]);
        }

        if (this.mapInstance) {
          this.mapInstance.setView([latitude, longitude], 16, { animate: true });
        }

        this.isLocating = false;
      },
      () => {
        this.isLocating = false;
        this.locationMessage =
          'No se pudo obtener tu ubicación actual. Revisa los permisos del navegador.';
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      },
    );
  }

  private updateSelectedLocation(latitude: number, longitude: number): void {
    this.selectedLatitude = latitude;
    this.selectedLongitude = longitude;
    this.isLocationChosen = true;
    this.showLocationError = false;
  }

  showFieldError(model: NgModel): boolean {
    return !!model.invalid && (!!model.touched || !!model.dirty);
  }

  private scheduleSuccessMessageHide(): void {
    if (this.successMessageTimeout) {
      clearTimeout(this.successMessageTimeout);
    }

    this.successMessageTimeout = setTimeout(() => {
      this.submitState = 'idle';
    }, 5000);
  }

  private getMissingFields(formInvalid: boolean): string[] {
    const missingFields: string[] = [];

    if (!this.form.workshopName.trim()) {
      missingFields.push('Nombre del Taller');
    }

    if (!this.form.contactName.trim()) {
      missingFields.push('Nombre Responsable');
    }

    if (!this.form.phone.trim() || this.form.phone.trim().length < 7) {
      missingFields.push('Número Telefónico');
    }

    if (!this.form.email.trim() || !this.form.email.includes('@')) {
      missingFields.push('Correo Electrónico');
    }

    if (!this.form.zone) {
      missingFields.push('Dirección del Taller');
    }

    if (!this.form.specialty) {
      missingFields.push('Tipo de Especialidades');
    }

    if (!this.isLocationChosen) {
      missingFields.push('Ubicación del Taller');
    }

    this.showLocationError = !this.isLocationChosen;

    if (!formInvalid && this.isLocationChosen) {
      return [];
    }

    return missingFields;
  }

  private openValidationDialog(missingFields: string[]): void {
    this.dialog.open(ValidationDialogComponent, {
      width: '420px',
      maxWidth: 'calc(100vw - 2rem)',
      data: { missingFields },
    });
  }
}
