import { CommonModule } from '@angular/common';
import { Component, OnDestroy, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';

import {
  EmergencyRoutingPreview,
  OfflineEmergencyService,
} from './offline-emergency.service';

const PROBLEM_TYPES = [
  'Batería',
  'Neumático',
  'Combustible',
  'Motor',
  'Sistema eléctrico',
  'Accidente',
  'Cerrajería / llaves',
  'Otro',
];

const MAX_PHOTOS = 6;

@Component({
  selector: 'app-offline-emergency-form',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="offline-form-page">
      <header class="offline-form-header">
        <a routerLink="/emergencias-offline" class="back-link">← Mis emergencias offline</a>
        <div class="header-net-badge" [class.online]="isOnline" [class.offline]="!isOnline">
          <span class="net-dot"></span>
          {{ isOnline ? 'Con conexión' : 'Sin conexión' }}
        </div>
      </header>

      <main class="offline-form-card" *ngIf="!saved; else successTpl">
        <h1 class="form-title">Registrar emergencia vehicular</h1>
        <p class="form-subtitle">
          Los datos se guardarán en el dispositivo y se enviarán al servidor
          automáticamente cuando recuperes la conexión.
        </p>

        <form (ngSubmit)="onSubmit()" #emergencyForm="ngForm" novalidate>

          <!-- Datos del vehículo -->
          <fieldset class="form-section">
            <legend>Vehículo</legend>

            <label class="form-field">
              <span>Nombre del vehículo <em>*</em></span>
              <input
                type="text"
                name="vehicleName"
                [(ngModel)]="form.vehicleName"
                required
                minlength="2"
                maxlength="160"
                placeholder="Ej. Toyota Corolla blanco"
              />
              <span class="field-error" *ngIf="submitted && !form.vehicleName">Campo requerido</span>
            </label>

            <label class="form-field">
              <span>Placa <em>*</em></span>
              <input
                type="text"
                name="vehiclePlate"
                [(ngModel)]="form.vehiclePlate"
                required
                minlength="3"
                maxlength="40"
                placeholder="Ej. 123 ABC"
                style="text-transform: uppercase"
              />
              <span class="field-error" *ngIf="submitted && !form.vehiclePlate">Campo requerido</span>
            </label>
          </fieldset>

          <!-- Tipo de incidente -->
          <fieldset class="form-section">
            <legend>Incidente</legend>

            <label class="form-field">
              <span>Tipo de incidente <em>*</em></span>
              <select name="problemType" [(ngModel)]="form.problemType" (ngModelChange)="onProblemTypeChanged()" required>
                <option value="" disabled>Selecciona un tipo...</option>
                <option *ngFor="let pt of problemTypes" [value]="pt">{{ pt }}</option>
              </select>
              <span class="field-error" *ngIf="submitted && !form.problemType">Campo requerido</span>
            </label>

            <label class="form-field">
              <span>Descripción del problema</span>
              <textarea
                name="description"
                [(ngModel)]="form.description"
                (blur)="refreshRoutingPreviewIfPossible()"
                rows="4"
                maxlength="4000"
                placeholder="Describe el problema con detalle para que el técnico llegue preparado..."
              ></textarea>
            </label>
          </fieldset>

          <!-- Ubicación GPS -->
          <fieldset class="form-section">
            <legend>Ubicación</legend>

            <div class="gps-row">
              <div class="gps-coords" *ngIf="form.latitude != null; else noCoords">
                <span class="gps-icon">📍</span>
                <span>
                  {{ form.latitude | number:'1.5-5' }}, {{ form.longitude | number:'1.5-5' }}
                </span>
                <button type="button" class="btn-sm btn-ghost" (click)="clearLocation()">
                  Limpiar
                </button>
              </div>
              <ng-template #noCoords>
                <span class="gps-empty">Sin ubicación capturada</span>
              </ng-template>

              <button
                type="button"
                class="btn-gps"
                (click)="captureLocation()"
                [disabled]="locationLoading"
              >
                {{ locationLoading ? 'Obteniendo...' : (form.latitude != null ? 'Actualizar GPS' : 'Capturar GPS') }}
              </button>
            </div>

            <p class="field-error" *ngIf="locationError">{{ locationError }}</p>

            <div class="routing-preview-card" *ngIf="routingPreview || routingPreviewLoading || routingPreviewError">
              <div class="routing-preview-header">
                <div>
                  <p class="routing-kicker">Sugerencia inteligente</p>
                  <h3>Sucursales compatibles</h3>
                </div>
                <button
                  type="button"
                  class="btn-sm btn-ghost"
                  (click)="refreshRoutingPreviewIfPossible(true)"
                  [disabled]="routingPreviewLoading || !canResolveRoutingPreview"
                >
                  {{ routingPreviewLoading ? 'Consultando...' : 'Actualizar sugerencia' }}
                </button>
              </div>

              <p class="routing-helper" *ngIf="!routingPreviewLoading && !routingPreview && !routingPreviewError">
                Captura ubicación y selecciona el tipo de incidente para sugerir la sucursal más cercana.
              </p>
              <p class="field-error" *ngIf="routingPreviewError">{{ routingPreviewError }}</p>

              <div class="routing-highlight" *ngIf="routingPreview as preview">
                <p class="routing-label">Sucursal sugerida para el móvil</p>
                <strong>{{ preview.nearest_sucursal_nombre || 'Sin sucursal sugerida' }}</strong>
                <span>
                  {{ preview.nearest_workshop_name || 'Sin taller sugerido' }}
                  <ng-container *ngIf="preview.nearest_workshop_distance_meters != null">
                    · {{ formatDistance(preview.nearest_workshop_distance_meters) }}
                  </ng-container>
                </span>
                <small>
                  {{ preview.total_matching_sucursales }} sucursal{{ preview.total_matching_sucursales === 1 ? '' : 'es' }}
                  compatible{{ preview.total_matching_sucursales === 1 ? '' : 's' }}
                </small>
              </div>

              <div class="routing-candidates" *ngIf="routingPreview?.candidates?.length">
                <article
                  class="routing-candidate"
                  *ngFor="let candidate of routingPreview!.candidates; let i = index"
                  [class.routing-candidate-primary]="i === 0"
                >
                  <div class="routing-candidate-main">
                    <strong>{{ candidate.sucursal_nombre || ('Sucursal #' + candidate.sucursal_id) }}</strong>
                    <span>{{ candidate.workshop_name }}</span>
                  </div>
                  <div class="routing-candidate-meta">
                    <span>{{ candidate.specialty || 'Especialidad general' }}</span>
                    <span>{{ formatDistance(candidate.distance_meters) }}</span>
                  </div>
                </article>
              </div>
            </div>

            <label class="form-field" *ngIf="form.latitude != null">
              <span>Dirección / referencia (opcional)</span>
              <input
                type="text"
                name="address"
                [(ngModel)]="form.address"
                maxlength="255"
                placeholder="Ej. Av. San Martín esquina Warnes"
              />
            </label>

            <label class="form-field" *ngIf="form.latitude != null">
              <span>Zona (opcional)</span>
              <input
                type="text"
                name="zone"
                [(ngModel)]="form.zone"
                maxlength="120"
                placeholder="Ej. Plan 3000"
              />
            </label>
          </fieldset>

          <!-- Fotografías -->
          <fieldset class="form-section">
            <legend>Fotografías (máx. {{ maxPhotos }})</legend>

            <div class="photo-grid" *ngIf="photoDataUrls.length > 0">
              <div class="photo-thumb" *ngFor="let url of photoDataUrls; let i = index">
                <img [src]="url" [alt]="'Foto ' + (i + 1)" />
                <button type="button" class="photo-remove" (click)="removePhoto(i)" title="Eliminar foto">✕</button>
              </div>
            </div>

            <label
              class="btn-upload"
              [class.disabled]="photoDataUrls.length >= maxPhotos"
              *ngIf="photoDataUrls.length < maxPhotos"
            >
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                (change)="onPhotosSelected($event)"
                style="display:none"
              />
              + Agregar fotos ({{ photoDataUrls.length }}/{{ maxPhotos }})
            </label>
          </fieldset>

          <!-- Audio -->
          <fieldset class="form-section">
            <legend>Audio</legend>

            <div class="audio-controls">
              <ng-container *ngIf="!audioDataUrl; else audioPreview">
                <button
                  type="button"
                  class="btn-record"
                  [class.recording]="isRecording"
                  (click)="toggleRecording()"
                >
                  <span class="record-icon">{{ isRecording ? '⏹' : '🎙' }}</span>
                  {{ isRecording ? 'Detener (' + recordingSeconds + 's)' : 'Grabar audio' }}
                </button>

                <span class="audio-separator">o</span>

                <label class="btn-upload-audio">
                  <input
                    type="file"
                    accept="audio/*"
                    (change)="onAudioFileSelected($event)"
                    style="display:none"
                  />
                  Adjuntar archivo
                </label>
              </ng-container>

              <ng-template #audioPreview>
                <div class="audio-preview">
                  <audio [src]="audioDataUrl" controls></audio>
                  <span class="audio-duration" *ngIf="form.audioDurationSeconds">
                    {{ form.audioDurationSeconds | number:'1.0-0' }}s
                  </span>
                  <button type="button" class="btn-sm btn-ghost" (click)="clearAudio()">
                    Eliminar audio
                  </button>
                </div>
              </ng-template>

              <p class="field-error" *ngIf="micError">{{ micError }}</p>
            </div>
          </fieldset>

          <!-- Acciones -->
          <div class="form-actions">
            <a routerLink="/emergencias-offline" class="btn-ghost">Cancelar</a>
            <button
              type="submit"
              class="btn-primary"
              [disabled]="saving"
            >
              {{ saving ? 'Guardando...' : 'Guardar emergencia' }}
            </button>
          </div>

          <p class="field-error form-error" *ngIf="saveError">{{ saveError }}</p>
        </form>
      </main>

      <ng-template #successTpl>
        <div class="success-card">
          <div class="success-icon">✅</div>
          <h2>¡Emergencia registrada!</h2>
          <p>
            La solicitud quedó guardada en tu dispositivo con estado
            <strong>Pendiente de sincronización</strong>.
            {{ isOnline ? 'La sincronización iniciará automáticamente.' : 'Se sincronizará cuando recuperes la conexión.' }}
          </p>
          <div class="success-actions">
            <button type="button" class="btn-primary" (click)="goToList()">
              Ver mis emergencias
            </button>
            <button type="button" class="btn-ghost" (click)="resetForm()">
              Registrar otra
            </button>
          </div>
        </div>
      </ng-template>
    </div>
  `,
  styles: [`
    .offline-form-page {
      max-width: 680px;
      margin: 0 auto;
      padding: 1.5rem 1rem 3rem;
    }

    .offline-form-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
      gap: 1rem;
    }

    .back-link {
      color: var(--text-primary);
      text-decoration: none;
      font-weight: 600;
      font-size: 0.9rem;
    }
    .back-link:hover { text-decoration: underline; }

    .header-net-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 0.82rem;
      font-weight: 600;
    }
    .header-net-badge.online { background: #d1fae5; color: #065f46; }
    .header-net-badge.offline { background: #fee2e2; color: #991b1b; }
    .net-dot {
      width: 8px; height: 8px; border-radius: 50%;
    }
    .online .net-dot { background: #059669; }
    .offline .net-dot { background: #dc2626; animation: blink 1.2s infinite; }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

    .offline-form-card {
      background: white;
      border-radius: 20px;
      border: 1px solid rgba(23,59,114,0.1);
      box-shadow: 0 4px 24px rgba(23,59,114,0.08);
      padding: 2rem;
    }

    .form-title {
      margin: 0 0 0.4rem;
      font-family: var(--font-display);
      font-size: 1.6rem;
      color: var(--text-primary);
    }
    .form-subtitle {
      margin: 0 0 1.8rem;
      color: var(--text-secondary);
      font-size: 0.9rem;
      line-height: 1.5;
    }

    fieldset.form-section {
      border: none;
      margin: 0 0 1.5rem;
      padding: 0;
    }
    fieldset.form-section legend {
      font-weight: 700;
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
      margin-bottom: 0.8rem;
    }

    .form-field {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-bottom: 0.9rem;
    }
    .form-field span { font-size: 0.88rem; font-weight: 600; color: var(--text-primary); }
    .form-field em { color: #dc2626; font-style: normal; margin-left: 2px; }
    .form-field input,
    .form-field select,
    .form-field textarea {
      padding: 0.55rem 0.75rem;
      border: 1.5px solid #d1d9e8;
      border-radius: 8px;
      font-size: 0.95rem;
      color: var(--text-primary);
      background: #fafbff;
      transition: border-color 0.2s;
    }
    .form-field input:focus,
    .form-field select:focus,
    .form-field textarea:focus {
      outline: none;
      border-color: #173b72;
    }

    .field-error { font-size: 0.82rem; color: #dc2626; margin-top: 2px; }

    .gps-row {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      flex-wrap: wrap;
      margin-bottom: 0.75rem;
    }
    .gps-coords {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.9rem;
      color: var(--text-secondary);
      background: #f0f4ff;
      padding: 6px 12px;
      border-radius: 8px;
    }
    .gps-empty { font-size: 0.88rem; color: var(--text-muted); }

    .btn-gps {
      padding: 0.45rem 1rem;
      background: #173b72;
      color: white;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.88rem;
      font-weight: 600;
      white-space: nowrap;
    }
    .btn-gps:disabled { opacity: 0.5; cursor: not-allowed; }

    .photo-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 0.75rem;
    }
    .photo-thumb {
      position: relative;
      width: 80px; height: 80px;
      border-radius: 8px;
      overflow: hidden;
      border: 1.5px solid #d1d9e8;
    }
    .photo-thumb img { width: 100%; height: 100%; object-fit: cover; }
    .photo-remove {
      position: absolute;
      top: 2px; right: 2px;
      width: 20px; height: 20px;
      border-radius: 50%;
      background: rgba(0,0,0,0.55);
      color: white;
      border: none;
      cursor: pointer;
      font-size: 11px;
      line-height: 1;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .btn-upload {
      display: inline-block;
      padding: 0.5rem 1rem;
      border: 1.5px dashed #9baec8;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.88rem;
      color: var(--text-secondary);
      text-align: center;
      transition: border-color 0.2s, color 0.2s;
    }
    .btn-upload:hover:not(.disabled) { border-color: #173b72; color: var(--text-primary); }
    .btn-upload.disabled { opacity: 0.4; cursor: not-allowed; }

    .audio-controls { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
    .audio-separator { font-size: 0.85rem; color: var(--text-muted); }

    .btn-record {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 0.5rem 1.1rem;
      background: #173b72;
      color: white;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.88rem;
      font-weight: 600;
      transition: background 0.2s;
    }
    .btn-record.recording { background: #dc2626; animation: pulse-rec 1s infinite; }
    @keyframes pulse-rec { 0%,100%{opacity:1} 50%{opacity:0.7} }

    .btn-upload-audio {
      padding: 0.5rem 1rem;
      border: 1.5px dashed #9baec8;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.88rem;
      color: var(--text-secondary);
    }
    .btn-upload-audio:hover { border-color: #173b72; color: var(--text-primary); }

    .audio-preview { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
    .audio-preview audio { height: 36px; }
    .audio-duration { font-size: 0.82rem; color: var(--text-muted); }

    .form-actions {
      display: flex;
      justify-content: flex-end;
      gap: 0.75rem;
      margin-top: 2rem;
      padding-top: 1.25rem;
      border-top: 1px solid #e8ecf5;
    }
    .form-error { margin-top: 0.75rem; text-align: center; }

    .btn-primary {
      padding: 0.65rem 1.6rem;
      background: #173b72;
      color: white;
      border: none;
      border-radius: 10px;
      cursor: pointer;
      font-weight: 700;
      font-size: 0.95rem;
      transition: background 0.2s;
    }
    .btn-primary:hover:not(:disabled) { background: #0f2a55; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

    .btn-ghost {
      padding: 0.65rem 1.2rem;
      background: transparent;
      color: var(--text-secondary);
      border: 1.5px solid #d1d9e8;
      border-radius: 10px;
      cursor: pointer;
      font-weight: 600;
      font-size: 0.9rem;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
    }
    .btn-ghost:hover { border-color: #173b72; color: var(--text-primary); }

    .btn-sm { font-size: 0.8rem; padding: 3px 8px; border-radius: 6px; }

    .routing-preview-card {
      margin: 1rem 0 1.2rem;
      padding: 1rem;
      border-radius: 14px;
      background:
        linear-gradient(135deg, rgba(24, 78, 164, 0.08), rgba(27, 164, 132, 0.08)),
        #f8fbff;
      border: 1px solid rgba(23, 59, 114, 0.12);
    }
    .routing-preview-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 0.75rem;
      margin-bottom: 0.8rem;
    }
    .routing-kicker {
      margin: 0 0 0.15rem;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #4b638b;
      font-weight: 700;
    }
    .routing-preview-header h3 {
      margin: 0;
      font-size: 1rem;
      color: var(--text-primary);
    }
    .routing-helper {
      margin: 0;
      color: var(--text-secondary);
      font-size: 0.88rem;
      line-height: 1.5;
    }
    .routing-highlight {
      display: grid;
      gap: 0.2rem;
      padding: 0.85rem 0.9rem;
      border-radius: 12px;
      background: white;
      border: 1px solid rgba(23, 59, 114, 0.08);
      box-shadow: 0 10px 24px rgba(23, 59, 114, 0.05);
    }
    .routing-label {
      margin: 0;
      color: #4b638b;
      font-size: 0.74rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 700;
    }
    .routing-highlight strong {
      color: var(--text-primary);
      font-size: 1rem;
    }
    .routing-highlight span,
    .routing-highlight small {
      color: var(--text-secondary);
    }
    .routing-candidates {
      display: grid;
      gap: 0.65rem;
      margin-top: 0.85rem;
    }
    .routing-candidate {
      display: flex;
      justify-content: space-between;
      gap: 0.75rem;
      align-items: center;
      padding: 0.75rem 0.9rem;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.75);
      border: 1px solid rgba(23, 59, 114, 0.08);
    }
    .routing-candidate-primary {
      border-color: rgba(16, 185, 129, 0.35);
      background: rgba(236, 253, 245, 0.92);
    }
    .routing-candidate-main,
    .routing-candidate-meta {
      display: grid;
      gap: 0.15rem;
    }
    .routing-candidate-main span,
    .routing-candidate-meta span {
      color: var(--text-secondary);
      font-size: 0.84rem;
    }
    .routing-candidate-meta {
      text-align: right;
      min-width: 110px;
    }

    .success-card {
      background: white;
      border-radius: 20px;
      border: 1px solid rgba(23,59,114,0.1);
      box-shadow: 0 4px 24px rgba(23,59,114,0.08);
      padding: 2.5rem;
      text-align: center;
    }
    .success-icon { font-size: 3rem; margin-bottom: 1rem; }
    .success-card h2 {
      font-family: var(--font-display);
      font-size: 1.5rem;
      color: var(--text-primary);
      margin: 0 0 0.75rem;
    }
    .success-card p { color: var(--text-secondary); line-height: 1.6; margin: 0 0 1.5rem; }
    .success-actions { display: flex; justify-content: center; gap: 0.75rem; flex-wrap: wrap; }
  `],
})
export class OfflineEmergencyFormComponent implements OnDestroy {
  private readonly offlineService = inject(OfflineEmergencyService);
  private readonly router = inject(Router);
  private readonly sub: Subscription;

  readonly problemTypes = PROBLEM_TYPES;
  readonly maxPhotos = MAX_PHOTOS;

  isOnline = navigator.onLine;

  form = {
    vehicleName: '',
    vehiclePlate: '',
    problemType: '',
    description: '',
    latitude: null as number | null,
    longitude: null as number | null,
    address: '',
    zone: '',
    audioDurationSeconds: null as number | null,
  };

  photoDataUrls: string[] = [];
  audioDataUrl: string | null = null;

  locationLoading = false;
  locationError = '';
  routingPreviewLoading = false;
  routingPreviewError = '';
  routingPreview: EmergencyRoutingPreview | null = null;
  isRecording = false;
  recordingSeconds = 0;
  micError = '';
  submitted = false;
  saving = false;
  saveError = '';
  saved = false;

  private mediaRecorder: MediaRecorder | null = null;
  private recordingInterval: ReturnType<typeof setInterval> | null = null;
  private audioChunks: BlobPart[] = [];

  constructor() {
    this.sub = this.offlineService.isOnline$.subscribe(online => {
      this.isOnline = online;
    });
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
    this.stopRecordingCleanup();
  }

  get canResolveRoutingPreview(): boolean {
    return !!this.form.problemType && this.form.latitude != null && this.form.longitude != null && this.isOnline;
  }

  captureLocation(): void {
    if (!navigator.geolocation) {
      this.locationError = 'Geolocalización no disponible en este navegador';
      return;
    }
    this.locationLoading = true;
    this.locationError = '';
    navigator.geolocation.getCurrentPosition(
      pos => {
        this.form.latitude = pos.coords.latitude;
        this.form.longitude = pos.coords.longitude;
        this.locationLoading = false;
        void this.refreshRoutingPreviewIfPossible();
      },
      () => {
        this.locationError = 'No se pudo obtener la ubicación. Verifica los permisos del navegador.';
        this.locationLoading = false;
      },
      { timeout: 12000, maximumAge: 60000 }
    );
  }

  clearLocation(): void {
    this.form.latitude = null;
    this.form.longitude = null;
    this.form.address = '';
    this.form.zone = '';
    this.routingPreview = null;
    this.routingPreviewError = '';
  }

  onProblemTypeChanged(): void {
    if (!this.form.problemType) {
      this.routingPreview = null;
      this.routingPreviewError = '';
      return;
    }
    void this.refreshRoutingPreviewIfPossible();
  }

  async refreshRoutingPreviewIfPossible(force = false): Promise<void> {
    if (!this.canResolveRoutingPreview) {
      if (force && !this.isOnline) {
        this.routingPreviewError = 'Necesitas conexión para consultar sucursales compatibles.';
      }
      return;
    }
    this.routingPreviewLoading = true;
    this.routingPreviewError = '';
    try {
      this.routingPreview = await this.offlineService.fetchRoutingPreview({
        problemType: this.form.problemType,
        latitude: this.form.latitude!,
        longitude: this.form.longitude!,
        description: this.form.description?.trim() || undefined,
      });
    } catch {
      this.routingPreview = null;
      this.routingPreviewError = 'No se pudo consultar la sucursal sugerida. Puedes guardar igual y el backend resolverá el destino al sincronizar.';
    } finally {
      this.routingPreviewLoading = false;
    }
  }

  onPhotosSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    const remaining = MAX_PHOTOS - this.photoDataUrls.length;
    files.slice(0, remaining).forEach(file => {
      const reader = new FileReader();
      reader.onloadend = () => {
        this.photoDataUrls.push(reader.result as string);
      };
      reader.readAsDataURL(file);
    });
    input.value = '';
  }

  removePhoto(index: number): void {
    this.photoDataUrls.splice(index, 1);
  }

  toggleRecording(): void {
    if (this.isRecording) {
      this.stopRecording();
    } else {
      this.startRecording();
    }
  }

  private startRecording(): void {
    this.micError = '';
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
      this.audioChunks = [];
      this.mediaRecorder = new MediaRecorder(stream);
      this.mediaRecorder.ondataavailable = evt => this.audioChunks.push(evt.data);
      this.mediaRecorder.onstop = () => {
        const mimeType = this.mediaRecorder?.mimeType || 'audio/webm';
        const blob = new Blob(this.audioChunks, { type: mimeType });
        this.form.audioDurationSeconds = this.recordingSeconds;
        const reader = new FileReader();
        reader.onloadend = () => {
          this.audioDataUrl = reader.result as string;
        };
        reader.readAsDataURL(blob);
        stream.getTracks().forEach(t => t.stop());
      };
      this.mediaRecorder.start();
      this.isRecording = true;
      this.recordingSeconds = 0;
      this.recordingInterval = setInterval(() => this.recordingSeconds++, 1000);
    }).catch(() => {
      this.micError = 'No se pudo acceder al micrófono. Verifica los permisos del navegador.';
    });
  }

  private stopRecording(): void {
    this.mediaRecorder?.stop();
    this.isRecording = false;
    if (this.recordingInterval) {
      clearInterval(this.recordingInterval);
      this.recordingInterval = null;
    }
  }

  private stopRecordingCleanup(): void {
    if (this.isRecording) this.stopRecording();
  }

  onAudioFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onloadend = () => {
      this.audioDataUrl = reader.result as string;
      this.form.audioDurationSeconds = null;
    };
    reader.readAsDataURL(file);
    input.value = '';
  }

  clearAudio(): void {
    this.audioDataUrl = null;
    this.form.audioDurationSeconds = null;
  }

  async onSubmit(): Promise<void> {
    this.submitted = true;
    if (!this.form.vehicleName.trim() || !this.form.vehiclePlate.trim() || !this.form.problemType) {
      return;
    }
    this.saving = true;
    this.saveError = '';
    try {
      await this.offlineService.saveEmergency({
        vehicleName: this.form.vehicleName.trim(),
        vehiclePlate: this.form.vehiclePlate.trim().toUpperCase(),
        problemType: this.form.problemType,
        description: this.form.description?.trim() || undefined,
        latitude: this.form.latitude ?? undefined,
        longitude: this.form.longitude ?? undefined,
        address: this.form.address?.trim() || undefined,
        zone: this.form.zone?.trim() || undefined,
        nearestWorkshopId: this.routingPreview?.nearest_workshop_id ?? undefined,
        nearestWorkshopName: this.routingPreview?.nearest_workshop_name ?? undefined,
        nearestWorkshopSpecialty: this.routingPreview?.problem_type_standardized ?? this.form.problemType,
        nearestWorkshopZone: this.routingPreview?.candidates?.[0]?.zone ?? undefined,
        nearestWorkshopDistanceMeters: this.routingPreview?.nearest_workshop_distance_meters ?? undefined,
        routingTotalMatchingSucursales: this.routingPreview?.total_matching_sucursales ?? undefined,
        routingCandidates: this.routingPreview?.candidates ?? undefined,
        audioDurationSeconds: this.form.audioDurationSeconds ?? undefined,
        photoDataUrls: [...this.photoDataUrls],
        audioDataUrl: this.audioDataUrl ?? undefined,
      });
      this.saved = true;
      if (navigator.onLine) {
        this.offlineService.syncPendingEmergencies();
      }
    } catch {
      this.saveError = 'No se pudo guardar la emergencia. Intenta nuevamente.';
    } finally {
      this.saving = false;
    }
  }

  goToList(): void {
    this.router.navigate(['/emergencias-offline']);
  }

  resetForm(): void {
    this.saved = false;
    this.submitted = false;
    this.saveError = '';
    this.form = {
      vehicleName: '', vehiclePlate: '', problemType: '', description: '',
      latitude: null, longitude: null, address: '', zone: '',
      audioDurationSeconds: null,
    };
    this.routingPreview = null;
    this.routingPreviewError = '';
    this.routingPreviewLoading = false;
    this.photoDataUrls = [];
    this.audioDataUrl = null;
  }

  formatDistance(distanceMeters: number | null | undefined): string {
    if (distanceMeters == null) {
      return 'Sin distancia';
    }
    if (distanceMeters >= 1000) {
      return `${(distanceMeters / 1000).toFixed(1)} km`;
    }
    return `${Math.round(distanceMeters)} m`;
  }
}
