import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../../shared/api-base';
import { Technician, TechnicianFormModel, TechnicianStatus } from './technicians.model';

@Injectable({
  providedIn: 'root',
})
export class TechniciansService {
  private readonly http = inject(HttpClient);
  private readonly techniciansApiUrl = `${API_BASE_URL}/technicians`;

  listTechnicians(workshopId: number | null): Observable<Technician[]> {
    const params = workshopId ? new HttpParams().set('workshop_id', workshopId) : undefined;
    return this.http.get<Technician[]>(this.techniciansApiUrl, { params });
  }

  createTechnician(
    workshopId: number | null,
    payload: TechnicianFormModel & { workshop_id: number | null },
  ): Observable<Technician> {
    const params = workshopId ? new HttpParams().set('workshop_id', workshopId) : undefined;
    return this.http.post<Technician>(this.techniciansApiUrl, payload, { params });
  }

  updateTechnician(
    technicianId: number,
    workshopId: number | null,
    payload: TechnicianFormModel & { workshop_id: number | null },
  ): Observable<Technician> {
    const params = workshopId ? new HttpParams().set('workshop_id', workshopId) : undefined;
    return this.http.put<Technician>(`${this.techniciansApiUrl}/${technicianId}`, payload, { params });
  }

  deleteTechnician(technicianId: number, workshopId: number | null): Observable<void> {
    const params = workshopId ? new HttpParams().set('workshop_id', workshopId) : undefined;
    return this.http.delete<void>(`${this.techniciansApiUrl}/${technicianId}`, { params });
  }

  updateTechnicianStatus(
    technician: Technician,
    nextStatus: TechnicianStatus,
    workshopId: number | null,
  ): Observable<Technician> {
    const params = workshopId ? new HttpParams().set('workshop_id', workshopId) : undefined;
    return this.http.put<Technician>(`${this.techniciansApiUrl}/${technician.id}`, {
      workshop_id: technician.workshop_id ?? workshopId,
      full_name: technician.full_name,
      phone: technician.phone,
      email: technician.email,
      specialty: technician.specialty,
      status: nextStatus,
    }, { params });
  }
}
