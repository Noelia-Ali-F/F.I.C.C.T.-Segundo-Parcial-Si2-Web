import { Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import { SessionRequestContext } from '../../auth/session-context';
import { EmergenciesService } from '../../emergencias/emergencies/emergencies.service';
import { MaintenanceRequest } from '../../emergencias/emergencies/emergencies.model';

@Injectable({
  providedIn: 'root',
})
export class ReportsService {
  constructor(private readonly emergenciesService: EmergenciesService) {}

  loadReportRequests(context: SessionRequestContext): Observable<MaintenanceRequest[]> {
    return this.emergenciesService
      .listEmergencyReports(context)
      .pipe(map((reports) => reports.map((report) => this.emergenciesService.mapEmergencyReportToRequest(report))));
  }
}
