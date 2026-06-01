import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../../shared/api-base';
import {
  WorkshopApprovalStatus,
  WorkshopRegistration,
  WorkshopUpdatePayload,
} from './workshops.model';

@Injectable({
  providedIn: 'root',
})
export class WorkshopsService {
  private readonly http = inject(HttpClient);
  private readonly workshopsApiUrl = `${API_BASE_URL}/workshops`;

  listWorkshops(): Observable<WorkshopRegistration[]> {
    return this.http.get<WorkshopRegistration[]>(this.workshopsApiUrl);
  }

  updateWorkshopApprovalStatus(
    workshopId: number,
    approvalStatus: WorkshopApprovalStatus,
  ): Observable<WorkshopRegistration> {
    return this.http.put<WorkshopRegistration>(
      `${this.workshopsApiUrl}/${workshopId}/approval-status`,
      { approval_status: approvalStatus },
    );
  }

  updateWorkshop(
    workshopId: number,
    payload: WorkshopUpdatePayload,
  ): Observable<WorkshopRegistration> {
    return this.http.put<WorkshopRegistration>(
      `${this.workshopsApiUrl}/${workshopId}`,
      payload,
    );
  }

  deleteWorkshop(workshopId: number): Observable<void> {
    return this.http.delete<void>(`${this.workshopsApiUrl}/${workshopId}`);
  }
}
