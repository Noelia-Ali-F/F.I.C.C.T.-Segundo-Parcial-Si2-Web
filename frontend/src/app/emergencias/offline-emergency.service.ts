import { Injectable, NgZone, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { BehaviorSubject, Subject, lastValueFrom } from 'rxjs';

import { API_BASE_URL } from '../shared/api-base';
import { getSessionRequestContext } from '../auth/session-context';

export type OfflineSyncStatus = 'pending_sync' | 'syncing' | 'synced' | 'sync_error';

export interface OfflineEmergency {
  localId: string;
  syncStatus: OfflineSyncStatus;
  createdAt: string;
  syncedAt?: string;
  serverId?: number;
  errorMessage?: string;
  retryCount: number;
  vehicleName: string;
  vehiclePlate: string;
  problemType: string;
  description?: string;
  latitude?: number;
  longitude?: number;
  address?: string;
  zone?: string;
  nearestWorkshopId?: number;
  nearestWorkshopName?: string;
  nearestWorkshopSpecialty?: string;
  nearestWorkshopZone?: string;
  nearestWorkshopDistanceMeters?: number;
  routingTotalMatchingSucursales?: number;
  routingCandidates?: EmergencyRoutingCandidate[];
  audioDurationSeconds?: number;
  photoDataUrls: string[];
  audioDataUrl?: string;
}

export interface EmergencyRoutingCandidate {
  workshop_id: number;
  workshop_name: string;
  sucursal_id: number | null;
  sucursal_nombre: string | null;
  specialty: string | null;
  specialties: string[];
  zone: string | null;
  latitude: number;
  longitude: number;
  distance_meters: number;
  specialty_match: boolean;
}

export interface EmergencyRoutingPreview {
  problem_type: string;
  problem_type_standardized: string | null;
  total_matching_sucursales: number;
  nearest_workshop_id: number | null;
  nearest_workshop_name: string | null;
  nearest_sucursal_id: number | null;
  nearest_sucursal_nombre: string | null;
  nearest_workshop_distance_meters: number | null;
  candidates: EmergencyRoutingCandidate[];
}

export interface OfflineEmergencySavePayload {
  vehicleName: string;
  vehiclePlate: string;
  problemType: string;
  description?: string;
  latitude?: number;
  longitude?: number;
  address?: string;
  zone?: string;
  nearestWorkshopId?: number;
  nearestWorkshopName?: string;
  nearestWorkshopSpecialty?: string;
  nearestWorkshopZone?: string;
  nearestWorkshopDistanceMeters?: number;
  routingTotalMatchingSucursales?: number;
  routingCandidates?: EmergencyRoutingCandidate[];
  audioDurationSeconds?: number;
  photoDataUrls: string[];
  audioDataUrl?: string;
}

const DB_NAME = 'ficct_offline_emergencies_v1';
const DB_VERSION = 1;
const STORE_NAME = 'emergencies';
const MAX_AUTO_RETRY = 3;

@Injectable({ providedIn: 'root' })
export class OfflineEmergencyService {
  private readonly http = inject(HttpClient);
  private readonly ngZone = inject(NgZone);

  private dbReady: Promise<IDBDatabase> = this.openDb();

  readonly isOnline$ = new BehaviorSubject<boolean>(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );
  readonly syncUpdate$ = new Subject<{ localId: string; status: OfflineSyncStatus }>();

  constructor() {
    this.setupNetworkListeners();
    if (navigator.onLine) {
      setTimeout(() => this.syncPendingEmergencies(), 4000);
    }
  }

  private openDb(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = evt => {
        const db = (evt.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: 'localId' });
          store.createIndex('syncStatus', 'syncStatus', { unique: false });
          store.createIndex('createdAt', 'createdAt', { unique: false });
        }
      };
      req.onsuccess = evt => resolve((evt.target as IDBOpenDBRequest).result);
      req.onerror = () => reject(req.error);
    });
  }

  private setupNetworkListeners(): void {
    window.addEventListener('online', () => {
      this.ngZone.run(() => {
        this.isOnline$.next(true);
        this.syncPendingEmergencies();
      });
    });
    window.addEventListener('offline', () => {
      this.ngZone.run(() => this.isOnline$.next(false));
    });
  }

  async saveEmergency(payload: OfflineEmergencySavePayload): Promise<string> {
    const localId = crypto.randomUUID();
    const emergency: OfflineEmergency = {
      ...payload,
      localId,
      syncStatus: 'pending_sync',
      retryCount: 0,
      createdAt: new Date().toISOString(),
    };
    const db = await this.dbReady;
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      tx.objectStore(STORE_NAME).put(emergency);
      tx.oncomplete = () => resolve(localId);
      tx.onerror = () => reject(tx.error);
    });
  }

  async fetchRoutingPreview(payload: {
    problemType: string;
    latitude: number;
    longitude: number;
    description?: string;
  }): Promise<EmergencyRoutingPreview> {
    const { headers } = getSessionRequestContext();
    let params = new HttpParams()
      .set('problem_type', payload.problemType)
      .set('latitude', String(payload.latitude))
      .set('longitude', String(payload.longitude));
    if (payload.description?.trim()) {
      params = params.set('description', payload.description.trim());
    }
    return await lastValueFrom(
      this.http.get<EmergencyRoutingPreview>(`${API_BASE_URL}/emergencias/routing-preview`, {
        params,
        headers,
      })
    );
  }

  async listEmergencies(): Promise<OfflineEmergency[]> {
    const db = await this.dbReady;
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const req = tx.objectStore(STORE_NAME).getAll();
      req.onsuccess = () => {
        const all = req.result as OfflineEmergency[];
        all.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
        resolve(all);
      };
      req.onerror = () => reject(req.error);
    });
  }

  async deleteEmergency(localId: string): Promise<void> {
    const db = await this.dbReady;
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      tx.objectStore(STORE_NAME).delete(localId);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  async syncPendingEmergencies(): Promise<void> {
    if (!navigator.onLine) return;
    const all = await this.listEmergencies();
    const toSync = all.filter(
      e =>
        e.syncStatus === 'pending_sync' ||
        (e.syncStatus === 'sync_error' && (e.retryCount ?? 0) < MAX_AUTO_RETRY)
    );
    for (const emergency of toSync) {
      await this.syncSingleEmergency(emergency);
    }
  }

  async syncSingleEmergency(emergency: OfflineEmergency): Promise<void> {
    if (!navigator.onLine) return;

    await this.patchEmergency(emergency.localId, { syncStatus: 'syncing' });
    this.ngZone.run(() =>
      this.syncUpdate$.next({ localId: emergency.localId, status: 'syncing' })
    );

    try {
      const formData = this.buildFormData(emergency);
      const { headers } = getSessionRequestContext();
      const response = await lastValueFrom(
        this.http.post<{ id: number }>(`${API_BASE_URL}/emergencias`, formData, { headers })
      );
      await this.patchEmergency(emergency.localId, {
        syncStatus: 'synced',
        syncedAt: new Date().toISOString(),
        serverId: response.id,
        errorMessage: undefined,
      });
      this.ngZone.run(() =>
        this.syncUpdate$.next({ localId: emergency.localId, status: 'synced' })
      );
    } catch (err: unknown) {
      const retryCount = (emergency.retryCount ?? 0) + 1;
      await this.patchEmergency(emergency.localId, {
        syncStatus: 'sync_error',
        retryCount,
        errorMessage: this.extractErrorMessage(err),
      });
      this.ngZone.run(() =>
        this.syncUpdate$.next({ localId: emergency.localId, status: 'sync_error' })
      );
    }
  }

  private async patchEmergency(localId: string, patch: Partial<OfflineEmergency>): Promise<void> {
    const db = await this.dbReady;
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const getReq = store.get(localId);
      getReq.onsuccess = () => {
        const existing = getReq.result as OfflineEmergency | undefined;
        if (!existing) { resolve(); return; }
        store.put({ ...existing, ...patch });
      };
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  private buildFormData(emergency: OfflineEmergency): FormData {
    const fd = new FormData();
    fd.append('local_id', emergency.localId);
    fd.append('vehicle_name', emergency.vehicleName);
    fd.append('vehicle_plate', emergency.vehiclePlate);
    fd.append('problem_type', emergency.problemType);
    if (emergency.description) fd.append('description', emergency.description);
    if (emergency.latitude != null) fd.append('latitude', String(emergency.latitude));
    if (emergency.longitude != null) fd.append('longitude', String(emergency.longitude));
    if (emergency.address) fd.append('address', emergency.address);
    if (emergency.zone) fd.append('zone', emergency.zone);
    if (emergency.nearestWorkshopId != null) fd.append('nearest_workshop_id', String(emergency.nearestWorkshopId));
    if (emergency.nearestWorkshopName) fd.append('nearest_workshop_name', emergency.nearestWorkshopName);
    if (emergency.nearestWorkshopSpecialty) fd.append('nearest_workshop_specialty', emergency.nearestWorkshopSpecialty);
    if (emergency.nearestWorkshopZone) fd.append('nearest_workshop_zone', emergency.nearestWorkshopZone);
    if (emergency.nearestWorkshopDistanceMeters != null) {
      fd.append('nearest_workshop_distance_meters', String(emergency.nearestWorkshopDistanceMeters));
    }
    if (emergency.audioDurationSeconds != null)
      fd.append('audio_duration_seconds', String(emergency.audioDurationSeconds));

    emergency.photoDataUrls.forEach((dataUrl, i) => {
      const blob = this.dataUrlToBlob(dataUrl);
      const ext = blob.type.split('/')[1] ?? 'jpg';
      fd.append('photos', blob, `offline_photo_${i}.${ext}`);
    });

    if (emergency.audioDataUrl) {
      const blob = this.dataUrlToBlob(emergency.audioDataUrl);
      const ext = blob.type.split('/')[1] ?? 'webm';
      fd.append('audio', blob, `offline_audio.${ext}`);
    }

    return fd;
  }

  private dataUrlToBlob(dataUrl: string): Blob {
    const [header, base64Data] = dataUrl.split(',');
    const mime = header.match(/:(.*?);/)?.[1] ?? 'application/octet-stream';
    const bytes = atob(base64Data);
    const buffer = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) {
      buffer[i] = bytes.charCodeAt(i);
    }
    return new Blob([buffer], { type: mime });
  }

  private extractErrorMessage(err: unknown): string {
    if (err && typeof err === 'object') {
      const e = err as Record<string, unknown>;
      if (e['error'] && typeof e['error'] === 'object') {
        const detail = (e['error'] as Record<string, unknown>)['detail'];
        if (detail) {
          return typeof detail === 'string' ? detail : JSON.stringify(detail);
        }
      }
      if (typeof e['message'] === 'string') return e['message'];
    }
    return 'Error de sincronización desconocido';
  }

  getSyncStatusLabel(status: OfflineSyncStatus): string {
    switch (status) {
      case 'pending_sync': return 'Pendiente de sincronización';
      case 'syncing': return 'Sincronizando...';
      case 'synced': return 'Sincronizada';
      case 'sync_error': return 'Error de sincronización';
    }
  }

  getSyncStatusClass(status: OfflineSyncStatus): string {
    switch (status) {
      case 'pending_sync': return 'badge-pending';
      case 'syncing': return 'badge-syncing';
      case 'synced': return 'badge-synced';
      case 'sync_error': return 'badge-error';
    }
  }
}
