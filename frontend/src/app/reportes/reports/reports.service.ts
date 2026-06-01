import { Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import { EmergenciesService } from '../../emergencias/emergencies/emergencies.service';
import { MaintenanceRequest } from '../../emergencias/emergencies/emergencies.model';

@Injectable({
  providedIn: 'root',
})
export class ReportsService {
  constructor(private readonly emergenciesService: EmergenciesService) {}

  loadReportRequests(workshopId: number | null): Observable<MaintenanceRequest[]> {
    return this.emergenciesService
      .listEmergencyReports(workshopId)
      .pipe(map((reports) => reports.map((report) => this.emergenciesService.mapEmergencyReportToRequest(report))));
  }
}
