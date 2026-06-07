import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { SessionRequestContext } from '../../auth/session-context';
import { API_BASE_URL, BACKEND_BASE_URL } from '../../shared/api-base';
import { EmergencyReport, EmergencyStatus, MaintenanceRequest } from './emergencies.model';

@Injectable({
  providedIn: 'root',
})
export class EmergenciesService {
  private readonly http = inject(HttpClient);
  private readonly emergenciesApiUrl = `${API_BASE_URL}/emergencies`;

  listEmergencyReports(context: SessionRequestContext): Observable<EmergencyReport[]> {
    let params = new HttpParams();
    if (context.workshopId) {
      params = params.set('nearest_workshop_id', String(context.workshopId));
    }
    return this.http.get<EmergencyReport[]>(this.emergenciesApiUrl, {
      params,
      headers: context.headers,
    });
  }

  updateEmergencyStatus(
    emergencyId: number,
    status: Exclude<EmergencyStatus, 'pendiente'>,
    context: SessionRequestContext,
  ): Observable<EmergencyReport> {
    const params = context.workshopId ? new HttpParams().set('workshop_id', String(context.workshopId)) : undefined;
    return this.http.put<EmergencyReport>(
      `${this.emergenciesApiUrl}/${emergencyId}/status`,
      { emergency_status: status },
      {
        params,
        headers: context.headers,
      },
    );
  }

  assignTechnician(
    emergencyId: number,
    context: SessionRequestContext,
    technicianId: number,
  ): Observable<EmergencyReport> {
    return this.http.put<EmergencyReport>(
      `${this.emergenciesApiUrl}/${emergencyId}/assign-technician`,
      { technician_id: technicianId },
      {
        params: new HttpParams().set('workshop_id', String(context.workshopId)),
        headers: context.headers,
      },
    );
  }

  deleteEmergency(
    emergencyId: number,
    context: SessionRequestContext,
  ): Observable<void> {
    const params = context.workshopId ? new HttpParams().set('workshop_id', String(context.workshopId)) : undefined;
    return this.http.delete<void>(`${this.emergenciesApiUrl}/${emergencyId}`, {
      params,
      headers: context.headers,
    });
  }

  mapEmergencyReportToRequest(report: EmergencyReport): MaintenanceRequest {
    const detailParts = [
      report.problem_type_standardized?.trim(),
      report.description?.trim(),
    ].filter(Boolean);

    const detail = detailParts.length
      ? detailParts.join(' · ')
      : report.problem_type;

    const distanceMeters = report.nearest_workshop_distance_meters;
    const priority =
      distanceMeters !== null && distanceMeters <= 3000
        ? 'Alta'
        : distanceMeters !== null && distanceMeters <= 8000
          ? 'Media'
          : 'Baja';

    return {
      id: report.id,
      code: `EMG-${String(report.id).padStart(4, '0')}`,
      client: report.client_name?.trim() || 'Cliente no identificado',
      vehicle: `${report.vehicle_name} · ${report.vehicle_plate}`,
      location: report.address?.trim() || report.zone?.trim() || 'Ubicación no disponible',
      priority,
      status: report.emergency_status ?? 'pendiente',
      price: report.price,
      distance: this.formatDistance(report.nearest_workshop_distance_meters),
      detail,
      reportedAt: this.relativeTimeLabel(report.created_at),
      createdAt: report.created_at,
      latitude: report.latitude,
      longitude: report.longitude,
      nearestWorkshopId: report.nearest_workshop_id,
      nearestWorkshopName: report.nearest_workshop_name,
      problemType: report.problem_type,
      standardizedProblemType: report.problem_type_standardized,
      clientDescription: report.description?.trim() || null,
      audioTranscript: report.audio_transcript?.trim() || null,
      photoUrls: this.getEmergencyPhotoUrls(report),
      audioUrl: this.normalizeBackendAssetUrl(report.audio_url),
      assignmentId: report.assignment_id,
      assignmentStatus: report.assignment_status,
      assignedTechnicianId: report.assigned_technician_id,
      assignedTechnicianName: report.assigned_technician_name,
      assignedTechnicianPhone: report.assigned_technician_phone,
      assignedTechnicianSpecialty: report.assigned_technician_specialty,
    };
  }

  formatReportPrice(price: number | null): string {
    if (price === null || Number.isNaN(price)) {
      return 'A cotizar';
    }
    return `Bs ${price.toLocaleString('es-BO', { maximumFractionDigits: 0 })}`;
  }

  calculateReportServiceAmount(price: number | null): number | null {
    if (price === null || Number.isNaN(price)) {
      return null;
    }
    return Math.round(price * 0.1);
  }

  calculateReportNetAmount(price: number | null): number | null {
    if (price === null || Number.isNaN(price)) {
      return null;
    }
    return price - this.calculateReportServiceAmount(price)!;
  }

  private formatDistance(distanceMeters: number | null): string {
    if (distanceMeters === null || Number.isNaN(distanceMeters)) {
      return 'Sin distancia';
    }
    if (distanceMeters < 1000) {
      return `${Math.round(distanceMeters)} m`;
    }
    return `${(distanceMeters / 1000).toFixed(1)} km`;
  }

  private relativeTimeLabel(createdAt: string): string {
    const created = new Date(createdAt).getTime();
    if (Number.isNaN(created)) {
      return 'Reciente';
    }
    const diffMinutes = Math.max(1, Math.round((Date.now() - created) / (1000 * 60)));
    if (diffMinutes < 60) {
      return `Hace ${diffMinutes} min`;
    }
    const diffHours = Math.round(diffMinutes / 60);
    if (diffHours < 24) {
      return `Hace ${diffHours} h`;
    }
    const diffDays = Math.round(diffHours / 24);
    return `Hace ${diffDays} d`;
  }

  private getEmergencyPhotoUrls(report: EmergencyReport): string[] {
    const rawPhotoUrls = this.parseMediaList(report.photo_urls);
    const rawPhotoPaths = this.parseMediaList(report.photo_paths);
    const normalizedPhotoUrls = rawPhotoUrls
      .map((photoUrl) => this.normalizeBackendAssetUrl(photoUrl))
      .filter((photoUrl): photoUrl is string => Boolean(photoUrl));
    const normalizedPhotoPaths = rawPhotoPaths
      .map((photoUrl) => this.normalizeBackendAssetUrl(photoUrl))
      .filter((photoUrl): photoUrl is string => Boolean(photoUrl));
    return Array.from(new Set([...normalizedPhotoUrls, ...normalizedPhotoPaths]));
  }

  private parseMediaList(value: string[] | string | null | undefined): string[] {
    if (Array.isArray(value)) {
      return value.filter((item): item is string => typeof item === 'string' && Boolean(item.trim()));
    }
    if (typeof value !== 'string') {
      return [];
    }
    const trimmed = value.trim();
    if (!trimmed) {
      return [];
    }
    try {
      const parsed = JSON.parse(trimmed);
      if (Array.isArray(parsed)) {
        return parsed.filter((item): item is string => typeof item === 'string' && Boolean(item.trim()));
      }
    } catch {
      return [trimmed];
    }
    return [];
  }

  private normalizeBackendAssetUrl(value: string | null | undefined): string | null {
    if (!value || !value.trim()) {
      return null;
    }
    if (/^https?:\/\//i.test(value)) {
      return value;
    }
    return `${BACKEND_BASE_URL}/${value.replace(/^\/+/, '')}`;
  }
}
