import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, ElementRef, OnDestroy, OnInit, ViewChild, inject } from '@angular/core';
import { FormsModule, NgForm } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { API_BASE_URL } from '../shared/api-base';

declare const L: any;

interface Plan {
  id: number;
  nombre: string;
  descripcion: string;
  precio_mensual: number;
  limite_sucursales: number;
  limite_tecnicos: number;
}

type CompanyZoneOption = {
  label: string;
  value: string;
};

type ReverseGeocodeResponse = {
  display_name?: string;
  address?: {
    road?: string;
    pedestrian?: string;
    suburb?: string;
    neighbourhood?: string;
    city?: string;
    town?: string;
    village?: string;
    state?: string;
    country?: string;
  };
};

@Component({
  selector: 'app-registro-taller',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  styleUrl: '../shared/shared-pages.css',
  template: `
    <main class="page login-clean-page">
      <section class="login-clean-shell" style="max-width: 680px; margin: 0 auto;">
        <div class="login-clean-card" style="flex-direction: column; max-width: 680px;">

          <!-- Encabezado -->
          <article class="login-clean-form-card" style="width: 100%;">
            <h1 style="font-size: 1.6rem; margin-bottom: 0.25rem;">Registrar mi Empresa</h1>
            <p style="color: var(--color-text-muted, #666); margin-bottom: 1.5rem; font-size: 0.95rem;">
              Completa el formulario para registrar tu taller en la plataforma ACB.
              Se creará una base de datos exclusiva para tu empresa.
            </p>

            <!-- Mensaje de éxito -->
            <div *ngIf="successMessage" class="registro-success-banner">
              <p style="font-weight: 600; margin-bottom: 0.5rem;">✓ {{ successMessage }}</p>
              <p style="font-size: 0.9rem;">
                Ya puedes
                <a routerLink="/login" style="color: inherit; text-decoration: underline;">iniciar sesión</a>
                con el correo y contraseña que registraste.
              </p>
            </div>

            <!-- Error general -->
            <p *ngIf="errorMessage && !successMessage" class="login-clean-feedback">
              {{ errorMessage }}
            </p>

            <form
              *ngIf="!successMessage"
              class="login-clean-form"
              (ngSubmit)="submitRegistro(registroForm)"
              #registroForm="ngForm"
            >

              <!-- ====== SECCIÓN: DATOS DE LA EMPRESA ====== -->
              <fieldset class="registro-fieldset">
                <legend class="registro-legend">Datos de la Empresa</legend>

                <label class="form-field">
                  <span>Nombre de la empresa *</span>
                  <input
                    type="text"
                    name="nombre"
                    [(ngModel)]="form.nombre"
                    required
                    minlength="3"
                    maxlength="200"
                    placeholder="Ej: Mecánicos Express S.R.L."
                  />
                </label>

                <label class="form-field">
                  <span>Razón social</span>
                  <input
                    type="text"
                    name="razon_social"
                    [(ngModel)]="form.razon_social"
                    maxlength="300"
                    placeholder="Nombre legal completo (opcional)"
                  />
                </label>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
                  <label class="form-field">
                    <span>NIT / CI</span>
                    <input
                      type="text"
                      name="nit"
                      [(ngModel)]="form.nit"
                      maxlength="50"
                      placeholder="Ej: 12345678"
                    />
                  </label>
                  <label class="form-field">
                    <span>Teléfono</span>
                    <input
                      type="tel"
                      name="telefono"
                      [(ngModel)]="form.telefono"
                      maxlength="50"
                      placeholder="Ej: 76543210"
                    />
                  </label>
                </div>

                <label class="form-field">
                  <span>Correo de la empresa *</span>
                  <input
                    type="email"
                    name="correo"
                    [(ngModel)]="form.correo"
                    required
                    email
                    placeholder="contacto@miempresa.com"
                  />
                </label>

                <label class="form-field">
                  <span>Dirección principal</span>
                  <input
                    type="text"
                    name="direccion_principal"
                    [(ngModel)]="form.direccion_principal"
                    required
                    maxlength="400"
                    placeholder="Ej: Av. Banzer Km 5"
                    (input)="handleAddressManualInput()"
                  />
                </label>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
                  <label class="form-field">
                    <span>Zona</span>
                    <select
                      name="zona"
                      [(ngModel)]="form.zona"
                      required
                    >
                      <option value="" disabled>Selecciona una zona</option>
                      <option *ngFor="let zone of companyZoneOptions" [value]="zone.value">
                        {{ zone.label }}
                      </option>
                    </select>
                  </label>
                  <label class="form-field">
                    <span>Ciudad</span>
                    <input
                      type="text"
                      name="ciudad"
                      [(ngModel)]="form.ciudad"
                      maxlength="120"
                      placeholder="Santa Cruz"
                    />
                  </label>
                </div>

                <label class="form-field registro-map-field">
                  <span>Selecciona la ubicación exacta de tu empresa</span>
                  <div class="registro-map-shell">
                    <button
                      class="registro-map-locate-button"
                      type="button"
                      (click)="locateCurrentPosition()"
                      [disabled]="isLocating"
                      [attr.aria-label]="isLocating ? 'Obteniendo ubicación actual' : 'Usar mi ubicación actual'"
                      [title]="
                        isLocating
                          ? 'Ubicando...'
                          : isSecureContext
                            ? 'Usar mi ubicación actual'
                            : 'La ubicación automática requiere HTTPS o localhost'
                      "
                    >
                      ⌖
                    </button>
                    <div
                      #companyMap
                      class="registro-map-canvas"
                      aria-label="Mapa interactivo para la ubicación de la empresa"
                    ></div>
                  </div>
                  <div class="registro-map-meta">
                    <small>Haz clic en el mapa o arrastra el marcador para elegir la ubicación exacta.</small>
                    <strong>
                      Lat: {{ form.latitud.toFixed(6) }} | Lng: {{ form.longitud.toFixed(6) }}
                    </strong>
                    <span class="registro-map-status" *ngIf="isReverseGeocoding">
                      Buscando dirección...
                    </span>
                    <span class="registro-map-status" *ngIf="!isReverseGeocoding && detectedAddress">
                      Dirección detectada: {{ detectedAddress }}
                    </span>
                    <span class="registro-map-status error" *ngIf="locationMessage">
                      {{ locationMessage }}
                    </span>
                    <span class="registro-map-status error" *ngIf="showLocationError">
                      Debes seleccionar la ubicación de tu empresa en el mapa.
                    </span>
                    <button
                      *ngIf="canApplyDetectedAddress"
                      class="dashboard-secondary-button registro-map-address-button"
                      type="button"
                      (click)="applyDetectedAddress()"
                    >
                      Usar dirección del mapa
                    </button>
                  </div>
                </label>
              </fieldset>

              <!-- ====== SECCIÓN: PLAN ====== -->
              <fieldset class="registro-fieldset" *ngIf="planes.length > 0">
                <legend class="registro-legend">Selecciona un Plan</legend>

                <div class="registro-planes-grid">
                  <div
                    *ngFor="let plan of planes"
                    class="registro-plan-card"
                    [class.is-selected]="form.plan_id === plan.id"
                    (click)="form.plan_id = plan.id"
                  >
                    <div class="registro-plan-name">{{ plan.nombre }}</div>
                    <div class="registro-plan-price">
                      {{ plan.precio_mensual === 0 ? 'Gratis' : 'Bs. ' + plan.precio_mensual + '/mes' }}
                    </div>
                    <div class="registro-plan-desc">{{ plan.descripcion }}</div>
                    <ul class="registro-plan-features">
                      <li>{{ plan.limite_sucursales }} sucursal{{ plan.limite_sucursales !== 1 ? 'es' : '' }}</li>
                      <li>{{ plan.limite_tecnicos }} técnicos</li>
                    </ul>
                  </div>
                </div>
              </fieldset>

              <!-- ====== SECCIÓN: CUENTA DE ADMINISTRADOR ====== -->
              <fieldset class="registro-fieldset">
                <legend class="registro-legend">Cuenta del Administrador</legend>
                <p style="font-size: 0.85rem; color: var(--color-text-muted, #666); margin-bottom: 1rem;">
                  Será el SUPERADMIN_TENANT — el dueño de la cuenta de la empresa en la plataforma.
                </p>

                <label class="form-field">
                  <span>Nombre completo *</span>
                  <input
                    type="text"
                    name="admin_nombre"
                    [(ngModel)]="form.admin_nombre"
                    required
                    minlength="3"
                    maxlength="160"
                    placeholder="Tu nombre completo"
                  />
                </label>

                <label class="form-field">
                  <span>Correo del administrador *</span>
                  <input
                    type="email"
                    name="admin_email"
                    [(ngModel)]="form.admin_email"
                    required
                    email
                    placeholder="tu.nombre@miempresa.com"
                  />
                </label>

                <label class="form-field">
                  <span>Teléfono del administrador</span>
                  <input
                    type="tel"
                    name="admin_telefono"
                    [(ngModel)]="form.admin_telefono"
                    maxlength="40"
                    placeholder="Ej: 70000001"
                  />
                </label>

                <label class="form-field">
                  <span>Contraseña *</span>
                  <span class="password-field">
                    <input
                      [type]="showPassword ? 'text' : 'password'"
                      name="admin_password"
                      [(ngModel)]="form.admin_password"
                      required
                      minlength="6"
                      placeholder="Mínimo 6 caracteres"
                    />
                    <button
                      class="password-toggle"
                      type="button"
                      (click)="showPassword = !showPassword"
                      [attr.aria-label]="showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
                    >
                      {{ showPassword ? '🙈' : '👁' }}
                    </button>
                  </span>
                </label>

                <label class="form-field">
                  <span>Confirmar contraseña *</span>
                  <input
                    [type]="showPassword ? 'text' : 'password'"
                    name="admin_confirm_password"
                    [(ngModel)]="form.admin_confirm_password"
                    required
                    placeholder="Repite tu contraseña"
                  />
                </label>

                <p
                  *ngIf="form.admin_password && form.admin_confirm_password && form.admin_password !== form.admin_confirm_password"
                  class="login-clean-feedback"
                >
                  Las contraseñas no coinciden.
                </p>
              </fieldset>

              <!-- Botón submit -->
              <button
                class="button primary login-clean-submit"
                type="submit"
                [disabled]="isSubmitting"
              >
                {{ isSubmitting ? 'Registrando...' : 'Registrar mi Empresa' }}
              </button>

              <p style="text-align: center; margin-top: 0.75rem; font-size: 0.9rem;">
                ¿Ya tienes cuenta?
                <a routerLink="/login" style="color: var(--color-primary, #1a73e8);">Inicia sesión aquí</a>
              </p>

            </form>
          </article>
        </div>
      </section>
    </main>
  `,
  styles: [`
    .registro-fieldset {
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      padding: 1rem 1.25rem;
      margin-bottom: 1.25rem;
    }
    .registro-legend {
      font-weight: 600;
      font-size: 0.9rem;
      padding: 0 0.5rem;
      color: #333;
    }
    .registro-planes-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 0.75rem;
    }
    .registro-plan-card {
      border: 2px solid #e0e0e0;
      border-radius: 8px;
      padding: 0.75rem;
      cursor: pointer;
      transition: border-color 0.2s, background-color 0.2s;
      user-select: none;
    }
    .registro-plan-card:hover {
      border-color: #999;
    }
    .registro-plan-card.is-selected {
      border-color: var(--color-primary, #1a73e8);
      background-color: rgba(26, 115, 232, 0.05);
    }
    .registro-plan-name {
      font-weight: 700;
      font-size: 1rem;
      margin-bottom: 0.25rem;
    }
    .registro-plan-price {
      font-size: 0.95rem;
      color: var(--color-primary, #1a73e8);
      font-weight: 600;
      margin-bottom: 0.4rem;
    }
    .registro-plan-desc {
      font-size: 0.8rem;
      color: #666;
      margin-bottom: 0.5rem;
    }
    .registro-plan-features {
      list-style: disc;
      padding-left: 1.2rem;
      font-size: 0.8rem;
      color: #555;
      margin: 0;
    }
    .registro-success-banner {
      background-color: #e8f5e9;
      border: 1px solid #4caf50;
      border-radius: 8px;
      padding: 1rem 1.25rem;
      margin-bottom: 1.25rem;
      color: #1b5e20;
    }
    .registro-map-field {
      margin-top: 0.5rem;
    }
    .registro-map-shell {
      position: relative;
      margin-top: 0.55rem;
      border-radius: 12px;
      overflow: hidden;
      border: 1px solid #d7dfeb;
      background: #dfe7f2;
      min-height: 20rem;
    }
    .registro-map-canvas {
      min-height: 20rem;
      width: 100%;
      display: block;
      background: #dfe7f2;
    }
    .registro-map-canvas.leaflet-container {
      min-height: 20rem;
      width: 100%;
    }
    .registro-map-locate-button {
      position: absolute;
      top: 0.8rem;
      right: 0.8rem;
      z-index: 600;
      width: 2.7rem;
      height: 2.7rem;
      border: 0;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.96);
      color: #173b72;
      font-size: 1.2rem;
      box-shadow: 0 12px 30px rgba(23, 59, 114, 0.16);
      cursor: pointer;
    }
    .registro-map-locate-button:disabled {
      cursor: wait;
      opacity: 0.8;
    }
    .registro-map-meta {
      display: grid;
      gap: 0.35rem;
      margin-top: 0.7rem;
      color: #475569;
    }
    .registro-map-meta strong {
      color: #0f172a;
      font-size: 0.92rem;
    }
    .registro-map-status.error {
      color: #9a2e23;
      font-size: 0.85rem;
      font-weight: 600;
    }
    .registro-map-status {
      color: #475569;
      font-size: 0.85rem;
      font-weight: 600;
    }
    .registro-map-address-button {
      justify-self: start;
    }
    @media (max-width: 640px) {
      .registro-map-shell,
      .registro-map-canvas,
      .registro-map-canvas.leaflet-container {
        min-height: 17rem;
      }
    }
  `],
})
export class RegistroTallerComponent implements OnInit, OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private mapInstance?: any;
  private mapMarker?: any;
  readonly companyZoneOptions: CompanyZoneOption[] = [
    { label: 'zona norte', value: 'Norte' },
    { label: 'zona sur', value: 'Sur' },
    { label: 'zona este', value: 'Este' },
    { label: 'zona oeste', value: 'Oeste' },
    { label: 'zona centro', value: 'Centro' },
  ];

  @ViewChild('companyMap')
  set companyMapRef(element: ElementRef<HTMLDivElement> | undefined) {
    if (!element || typeof window === 'undefined') {
      return;
    }

    window.setTimeout(() => {
      this.initializeCompanyMap(element.nativeElement);
    });
  }

  planes: Plan[] = [];
  isSubmitting = false;
  isLocating = false;
  isLocationChosen = false;
  isReverseGeocoding = false;
  readonly isSecureContext = typeof window !== 'undefined' ? window.isSecureContext : false;
  errorMessage = '';
  successMessage = '';
  showPassword = false;
  showLocationError = false;
  locationMessage = '';
  detectedAddress = '';
  private addressTouchedManually = false;
  private lastAutofilledAddress = '';

  form = {
    nombre: '',
    razon_social: '',
    nit: '',
    correo: '',
    telefono: '',
    direccion_principal: '',
    zona: '',
    ciudad: 'Santa Cruz',
    latitud: -17.7833,
    longitud: -63.1821,
    plan_id: null as number | null,
    admin_nombre: '',
    admin_email: '',
    admin_password: '',
    admin_confirm_password: '',
    admin_telefono: '',
  };

  ngOnInit(): void {
    this.http.get<Plan[]>(`${API_BASE_URL}/public/planes`).subscribe({
      next: (planes) => {
        this.planes = planes;
        if (planes.length > 0) {
          this.form.plan_id = planes[0].id;
        }
      },
      error: () => {
        this.planes = [];
      },
    });
  }

  ngOnDestroy(): void {
    if (this.mapInstance) {
      this.mapInstance.remove();
      this.mapInstance = undefined;
      this.mapMarker = undefined;
    }
  }

  submitRegistro(form: NgForm): void {
    if (this.isSubmitting) return;

    if (form.invalid) {
      this.errorMessage = !this.form.zona
        ? 'Debes seleccionar una zona.'
        : !this.form.direccion_principal.trim()
          ? 'La dirección principal es obligatoria.'
          : 'Completa todos los campos obligatorios.';
      return;
    }
    if (!this.isLocationChosen) {
      this.showLocationError = true;
      this.errorMessage = 'Debes seleccionar la ubicación de tu empresa en el mapa.';
      return;
    }
    if (this.form.admin_password !== this.form.admin_confirm_password) {
      this.errorMessage = 'Las contraseñas del administrador no coinciden.';
      return;
    }
    if (this.form.admin_password.length < 6) {
      this.errorMessage = 'La contraseña debe tener al menos 6 caracteres.';
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';
    this.locationMessage = '';

    const body = {
      nombre: this.form.nombre.trim(),
      razon_social: this.form.razon_social.trim() || null,
      nit: this.form.nit.trim() || null,
      correo: this.form.correo.trim().toLowerCase(),
      telefono: this.form.telefono.trim() || null,
      direccion_principal: this.form.direccion_principal.trim() || null,
      zona: this.form.zona.trim() || null,
      ciudad: this.form.ciudad.trim() || 'Santa Cruz',
      latitud: this.form.latitud,
      longitud: this.form.longitud,
      plan_id: this.form.plan_id,
      admin_nombre: this.form.admin_nombre.trim(),
      admin_email: this.form.admin_email.trim().toLowerCase(),
      admin_password: this.form.admin_password,
      admin_confirm_password: this.form.admin_confirm_password,
      admin_telefono: this.form.admin_telefono.trim() || null,
    };

    this.http
      .post<{ mensaje: string; slug: string; tenant_id: number }>(`${API_BASE_URL}/public/registro-taller`, body)
      .subscribe({
        next: (resp) => {
          this.isSubmitting = false;
          this.successMessage = resp.mensaje;
        },
        error: (err: HttpErrorResponse) => {
          this.isSubmitting = false;
          const detail = err.error?.detail;
          this.errorMessage =
            (typeof detail === 'string' ? detail : detail?.message) ||
            'No se pudo completar el registro. Inténtalo nuevamente.';
        },
      });
  }

  locateCurrentPosition(): void {
    this.locationMessage = '';

    if (!this.isSecureContext) {
      this.locationMessage =
        'La ubicación automática del navegador solo funciona en HTTPS o en localhost. Usa el mapa manualmente o abre el sitio con HTTPS.';
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
        this.locationMessage = 'No se pudo obtener tu ubicación actual. Revisa los permisos del navegador.';
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      },
    );
  }

  private initializeCompanyMap(element: HTMLDivElement): void {
    if (this.mapInstance || typeof L === 'undefined') {
      return;
    }

    this.mapInstance = L.map(element, {
      center: [this.form.latitud, this.form.longitud],
      zoom: 13,
      scrollWheelZoom: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(this.mapInstance);

    this.mapMarker = L.marker([this.form.latitud, this.form.longitud], {
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

  private updateSelectedLocation(latitude: number, longitude: number): void {
    this.form.latitud = latitude;
    this.form.longitud = longitude;
    this.isLocationChosen = true;
    this.showLocationError = false;
    this.locationMessage = '';
    this.reverseGeocode(latitude, longitude);
  }

  handleAddressManualInput(): void {
    const currentValue = this.form.direccion_principal.trim();
    this.addressTouchedManually = currentValue.length > 0 && currentValue !== this.lastAutofilledAddress;
  }

  get canApplyDetectedAddress(): boolean {
    return !!this.detectedAddress && this.addressTouchedManually && this.form.direccion_principal.trim() !== this.detectedAddress;
  }

  applyDetectedAddress(): void {
    if (!this.detectedAddress) {
      return;
    }
    this.form.direccion_principal = this.detectedAddress;
    this.lastAutofilledAddress = this.detectedAddress;
    this.addressTouchedManually = false;
    this.locationMessage = '';
  }

  private reverseGeocode(latitude: number, longitude: number): void {
    this.isReverseGeocoding = true;
    this.locationMessage = '';

    this.http.get<ReverseGeocodeResponse>('https://nominatim.openstreetmap.org/reverse', {
      params: {
        format: 'jsonv2',
        lat: latitude.toFixed(6),
        lon: longitude.toFixed(6),
        'accept-language': 'es',
      },
    }).subscribe({
      next: (response) => {
        this.isReverseGeocoding = false;
        const detectedAddress = this.buildDetectedAddress(response);

        if (!detectedAddress) {
          this.detectedAddress = '';
          this.locationMessage = 'No se pudo obtener dirección exacta. Puedes escribirla manualmente.';
          return;
        }

        this.detectedAddress = detectedAddress;

        if (!this.addressTouchedManually || !this.form.direccion_principal.trim()) {
          this.form.direccion_principal = detectedAddress;
          this.lastAutofilledAddress = detectedAddress;
          this.addressTouchedManually = false;
        }

        const detectedCity = response.address?.city || response.address?.town || response.address?.village || '';
        if (!this.form.ciudad.trim() && detectedCity) {
          this.form.ciudad = detectedCity;
        }
      },
      error: () => {
        this.isReverseGeocoding = false;
        this.detectedAddress = '';
        this.locationMessage = 'No se pudo obtener la dirección automáticamente. Puedes escribirla manualmente.';
      },
    });
  }

  private buildDetectedAddress(response: ReverseGeocodeResponse): string {
    const road = response.address?.road || response.address?.pedestrian || '';
    const suburb = response.address?.suburb || response.address?.neighbourhood || '';
    const city = response.address?.city || response.address?.town || response.address?.village || '';
    const shortAddress = [road, suburb, city].filter(Boolean).join(', ');

    if (shortAddress.length >= 8) {
      return shortAddress;
    }

    return (response.display_name || '').trim();
  }
}
