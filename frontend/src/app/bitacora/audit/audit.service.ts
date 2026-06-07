import { Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import { SessionRequestContext } from '../../auth/session-context';
import { EmergenciesService } from '../../emergencias/emergencies/emergencies.service';
import { AuditItem, AuditTone, MaintenanceRequest } from '../../emergencias/emergencies/emergencies.model';

@Injectable({
  providedIn: 'root',
})
export class AuditService {
  constructor(private readonly emergenciesService: EmergenciesService) {}

  loadAuditItems(context: SessionRequestContext): Observable<AuditItem[]> {
    return this.emergenciesService.listEmergencyReports(context).pipe(
      map((reports) =>
        reports
          .map((report) => this.emergenciesService.mapEmergencyReportToRequest(report))
          .map((request) => this.mapRequestToAuditItem(request))
          .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()),
      ),
    );
  }

  private mapRequestToAuditItem(request: MaintenanceRequest): AuditItem {
    const tone: AuditTone =
      request.status === 'activo'
        ? 'success'
        : request.status === 'rechazado'
          ? 'danger'
          : 'warning';

    return {
      title: `${request.code} · ${request.problemType}`,
      detail: request.detail,
      meta: `${request.client} · ${request.vehicle}${request.assignedTechnicianName ? ` · ${request.assignedTechnicianName}` : ''}`,
      createdAt: request.createdAt,
      tone,
    };
  }
}
