import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';

import {
  OfflineEmergencyService,
  OfflineEmergency,
  OfflineSyncStatus,
} from './offline-emergency.service';

@Component({
  selector: 'app-offline-emergencies-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="offline-list-page">

      <!-- Cabecera -->
      <header class="list-header">
        <div>
          <h1 class="list-title">Emergencias offline</h1>
          <p class="list-subtitle">
            Solicitudes registradas localmente en este dispositivo.
          </p>
        </div>
        <div class="header-actions">
          <div class="net-badge" [class.online]="isOnline" [class.offline]="!isOnline">
            <span class="net-dot"></span>
            {{ isOnline ? 'Con conexión' : 'Sin conexión' }}
          </div>
          <button
            class="btn-sync"
            (click)="syncAll()"
            [disabled]="syncing || !isOnline"
            title="{{ !isOnline ? 'Sin conexión' : 'Sincronizar pendientes' }}"
          >
            <span class="sync-icon" [class.spinning]="syncing">⟳</span>
            {{ syncing ? 'Sincronizando…' : 'Sincronizar todo' }}
          </button>
          <a routerLink="/emergencias-offline/nueva" class="btn-primary">
            + Nueva emergencia
          </a>
        </div>
      </header>

      <!-- Resumen de contadores -->
      <div class="stats-row" *ngIf="emergencies.length > 0">
        <div class="stat-chip pending">
          <span>{{ countByStatus('pending_sync') }}</span> pendiente{{ countByStatus('pending_sync') === 1 ? '' : 's' }}
        </div>
        <div class="stat-chip syncing" *ngIf="countByStatus('syncing') > 0">
          <span>{{ countByStatus('syncing') }}</span> sincronizando
        </div>
        <div class="stat-chip synced">
          <span>{{ countByStatus('synced') }}</span> sincronizada{{ countByStatus('synced') === 1 ? '' : 's' }}
        </div>
        <div class="stat-chip error" *ngIf="countByStatus('sync_error') > 0">
          <span>{{ countByStatus('sync_error') }}</span> con error
        </div>
      </div>

      <!-- Lista vacía -->
      <div class="empty-state" *ngIf="emergencies.length === 0 && !loading">
        <div class="empty-icon">📋</div>
        <h2>Sin emergencias guardadas</h2>
        <p>
          Registra una emergencia vehicular aunque no tengas conexión.<br />
          Se sincronizará automáticamente cuando recuperes el internet.
        </p>
        <a routerLink="/emergencias-offline/nueva" class="btn-primary">
          Registrar emergencia
        </a>
      </div>

      <!-- Cargando -->
      <div class="loading-state" *ngIf="loading">
        <div class="spinner"></div>
        <p>Cargando emergencias...</p>
      </div>

      <!-- Tarjetas -->
      <div class="emergency-grid" *ngIf="!loading">
        <article
          class="emergency-card"
          *ngFor="let em of emergencies; trackBy: trackByLocalId"
          [class.card-synced]="em.syncStatus === 'synced'"
          [class.card-error]="em.syncStatus === 'sync_error'"
          [class.card-syncing]="em.syncStatus === 'syncing'"
        >
          <!-- Status badge -->
          <div class="card-status-row">
            <span class="status-badge" [ngClass]="offlineService.getSyncStatusClass(em.syncStatus)">
              <span class="status-dot" [ngClass]="em.syncStatus"></span>
              {{ offlineService.getSyncStatusLabel(em.syncStatus) }}
            </span>
            <span class="card-date">{{ formatDate(em.createdAt) }}</span>
          </div>

          <!-- Datos principales -->
          <h3 class="card-vehicle">{{ em.vehicleName }}</h3>
          <p class="card-plate">🚗 Placa: <strong>{{ em.vehiclePlate }}</strong></p>
          <p class="card-type">⚠️ {{ em.problemType }}</p>
          <p class="card-desc" *ngIf="em.description">{{ em.description }}</p>

          <!-- Ubicación -->
          <p class="card-location" *ngIf="em.latitude != null">
            📍 {{ em.latitude | number:'1.5-5' }}, {{ em.longitude | number:'1.5-5' }}
            <span *ngIf="em.address"> — {{ em.address }}</span>
          </p>

          <!-- Medios adjuntos -->
          <div class="card-media" *ngIf="em.photoDataUrls?.length || em.audioDataUrl">
            <span class="media-chip" *ngIf="em.photoDataUrls?.length">
              📷 {{ em.photoDataUrls.length }} foto{{ em.photoDataUrls.length === 1 ? '' : 's' }}
            </span>
            <span class="media-chip" *ngIf="em.audioDataUrl">🎙 Audio adjunto</span>
          </div>

          <!-- ID del servidor (si ya sincronizó) -->
          <p class="server-id" *ngIf="em.serverId">
            ID servidor: #{{ em.serverId }}
            <span *ngIf="em.syncedAt"> — {{ formatDate(em.syncedAt) }}</span>
          </p>

          <!-- Error message -->
          <p class="error-msg" *ngIf="em.syncStatus === 'sync_error' && em.errorMessage">
            {{ em.errorMessage }}
            <span *ngIf="em.retryCount">(intento {{ em.retryCount }}/3)</span>
          </p>

          <!-- Acciones -->
          <div class="card-actions">
            <button
              class="btn-retry"
              *ngIf="em.syncStatus === 'sync_error' || em.syncStatus === 'pending_sync'"
              (click)="retrySingle(em)"
              [disabled]="!isOnline"
            >
              Reintentar sync
            </button>
            <button
              class="btn-delete"
              (click)="deleteEmergency(em)"
              [disabled]="em.syncStatus === 'syncing'"
            >
              Eliminar
            </button>
          </div>
        </article>
      </div>

    </div>
  `,
  styles: [`
    .offline-list-page {
      max-width: 860px;
      margin: 0 auto;
      padding: 1.5rem 1rem 3rem;
    }

    .list-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 1rem;
      margin-bottom: 1.25rem;
      flex-wrap: wrap;
    }
    .list-title {
      margin: 0 0 0.2rem;
      font-family: var(--font-display);
      font-size: 1.8rem;
      color: var(--text-primary);
    }
    .list-subtitle { margin: 0; font-size: 0.88rem; color: var(--text-muted); }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      flex-wrap: wrap;
    }

    .net-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 0.82rem;
      font-weight: 600;
    }
    .net-badge.online { background: #d1fae5; color: #065f46; }
    .net-badge.offline { background: #fee2e2; color: #991b1b; }
    .net-dot { width: 8px; height: 8px; border-radius: 50%; }
    .online .net-dot { background: #059669; }
    .offline .net-dot { background: #dc2626; animation: blink 1.2s infinite; }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

    .btn-sync {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 0.5rem 1rem;
      background: white;
      color: var(--text-primary);
      border: 1.5px solid #d1d9e8;
      border-radius: 9px;
      cursor: pointer;
      font-weight: 600;
      font-size: 0.88rem;
    }
    .btn-sync:hover:not(:disabled) { border-color: #173b72; }
    .btn-sync:disabled { opacity: 0.45; cursor: not-allowed; }
    .sync-icon { font-size: 1rem; display: inline-block; }
    .sync-icon.spinning { animation: spin 0.8s linear infinite; }
    @keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }

    .btn-primary {
      padding: 0.55rem 1.2rem;
      background: #173b72;
      color: white;
      border: none;
      border-radius: 9px;
      cursor: pointer;
      font-weight: 700;
      font-size: 0.9rem;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
    }
    .btn-primary:hover { background: #0f2a55; }

    .stats-row {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
      margin-bottom: 1.25rem;
    }
    .stat-chip {
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 0.82rem;
      font-weight: 600;
    }
    .stat-chip span { font-size: 1rem; margin-right: 3px; }
    .stat-chip.pending { background: #fef3c7; color: #92400e; }
    .stat-chip.syncing { background: #dbeafe; color: #1e40af; }
    .stat-chip.synced { background: #d1fae5; color: #065f46; }
    .stat-chip.error { background: #fee2e2; color: #991b1b; }

    .empty-state {
      text-align: center;
      padding: 3rem 1rem;
      background: white;
      border-radius: 20px;
      border: 1px solid rgba(23,59,114,0.08);
    }
    .empty-icon { font-size: 3rem; margin-bottom: 1rem; }
    .empty-state h2 {
      font-family: var(--font-display);
      font-size: 1.4rem;
      color: var(--text-primary);
      margin: 0 0 0.6rem;
    }
    .empty-state p { color: var(--text-secondary); line-height: 1.6; margin: 0 0 1.5rem; }

    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 3rem;
      gap: 1rem;
      color: var(--text-muted);
    }
    .spinner {
      width: 36px; height: 36px;
      border: 3px solid #e8ecf5;
      border-top-color: #173b72;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
    }

    .emergency-grid {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .emergency-card {
      background: white;
      border-radius: 16px;
      border: 1.5px solid rgba(23,59,114,0.1);
      box-shadow: 0 2px 12px rgba(23,59,114,0.05);
      padding: 1.25rem 1.4rem;
      transition: box-shadow 0.2s;
    }
    .emergency-card:hover { box-shadow: 0 4px 20px rgba(23,59,114,0.1); }
    .card-synced { border-color: #a7f3d0; }
    .card-error { border-color: #fca5a5; }
    .card-syncing { border-color: #93c5fd; }

    .card-status-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;
    }
    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 3px 10px;
      border-radius: 20px;
      font-size: 0.8rem;
      font-weight: 700;
    }
    .badge-pending { background: #fef3c7; color: #92400e; }
    .badge-syncing { background: #dbeafe; color: #1e40af; }
    .badge-synced { background: #d1fae5; color: #065f46; }
    .badge-error { background: #fee2e2; color: #991b1b; }

    .status-dot {
      width: 7px; height: 7px; border-radius: 50%;
    }
    .status-dot.pending_sync { background: #d97706; }
    .status-dot.syncing { background: #2563eb; animation: blink 0.8s infinite; }
    .status-dot.synced { background: #059669; }
    .status-dot.sync_error { background: #dc2626; }

    .card-date { font-size: 0.8rem; color: var(--text-muted); }

    .card-vehicle {
      margin: 0 0 0.3rem;
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--text-primary);
    }
    .card-plate, .card-type, .card-desc, .card-location {
      margin: 0 0 0.3rem;
      font-size: 0.9rem;
      color: var(--text-secondary);
    }
    .card-desc { font-style: italic; color: var(--text-muted); }

    .card-media {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin: 0.4rem 0;
    }
    .media-chip {
      background: #f0f4ff;
      color: #3b5ba5;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.8rem;
      font-weight: 600;
    }

    .server-id {
      font-size: 0.8rem;
      color: #059669;
      margin: 0.3rem 0;
    }

    .error-msg {
      font-size: 0.82rem;
      color: #dc2626;
      background: #fef2f2;
      padding: 6px 10px;
      border-radius: 6px;
      margin: 0.4rem 0;
    }

    .card-actions {
      display: flex;
      gap: 0.5rem;
      margin-top: 0.9rem;
      padding-top: 0.75rem;
      border-top: 1px solid #f0f3fa;
    }

    .btn-retry {
      padding: 0.4rem 0.9rem;
      background: #173b72;
      color: white;
      border: none;
      border-radius: 7px;
      cursor: pointer;
      font-size: 0.85rem;
      font-weight: 600;
    }
    .btn-retry:disabled { opacity: 0.45; cursor: not-allowed; }

    .btn-delete {
      padding: 0.4rem 0.9rem;
      background: transparent;
      color: #dc2626;
      border: 1.5px solid #fca5a5;
      border-radius: 7px;
      cursor: pointer;
      font-size: 0.85rem;
      font-weight: 600;
    }
    .btn-delete:hover:not(:disabled) { background: #fef2f2; }
    .btn-delete:disabled { opacity: 0.45; cursor: not-allowed; }
  `],
})
export class OfflineEmergenciesListComponent implements OnInit, OnDestroy {
  readonly offlineService = inject(OfflineEmergencyService);

  emergencies: OfflineEmergency[] = [];
  isOnline = navigator.onLine;
  loading = true;
  syncing = false;

  private subs: Subscription[] = [];

  ngOnInit(): void {
    this.loadEmergencies();

    this.subs.push(
      this.offlineService.isOnline$.subscribe(online => {
        this.isOnline = online;
      }),
      this.offlineService.syncUpdate$.subscribe(({ localId, status }) => {
        const em = this.emergencies.find(e => e.localId === localId);
        if (em) em.syncStatus = status;
        if (status === 'synced' || status === 'sync_error') {
          this.loadEmergencies();
        }
      })
    );
  }

  ngOnDestroy(): void {
    this.subs.forEach(s => s.unsubscribe());
  }

  async loadEmergencies(): Promise<void> {
    this.loading = true;
    try {
      this.emergencies = await this.offlineService.listEmergencies();
    } finally {
      this.loading = false;
    }
  }

  countByStatus(status: OfflineSyncStatus): number {
    return this.emergencies.filter(e => e.syncStatus === status).length;
  }

  async syncAll(): Promise<void> {
    if (!this.isOnline || this.syncing) return;
    this.syncing = true;
    try {
      await this.offlineService.syncPendingEmergencies();
      await this.loadEmergencies();
    } finally {
      this.syncing = false;
    }
  }

  async retrySingle(emergency: OfflineEmergency): Promise<void> {
    if (!this.isOnline) return;
    emergency.syncStatus = 'syncing';
    await this.offlineService.syncSingleEmergency(emergency);
    await this.loadEmergencies();
  }

  async deleteEmergency(emergency: OfflineEmergency): Promise<void> {
    if (emergency.syncStatus === 'syncing') return;
    const confirmed = window.confirm(
      `¿Eliminar la emergencia de "${emergency.vehicleName}" (${emergency.vehiclePlate})?\n` +
      (emergency.syncStatus !== 'synced' ? 'Esta emergencia aún no fue sincronizada con el servidor.' : '')
    );
    if (!confirmed) return;
    await this.offlineService.deleteEmergency(emergency.localId);
    this.emergencies = this.emergencies.filter(e => e.localId !== emergency.localId);
  }

  trackByLocalId(_: number, em: OfflineEmergency): string {
    return em.localId;
  }

  formatDate(isoString: string | undefined): string {
    if (!isoString) return '';
    const d = new Date(isoString);
    return d.toLocaleString('es-BO', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}
