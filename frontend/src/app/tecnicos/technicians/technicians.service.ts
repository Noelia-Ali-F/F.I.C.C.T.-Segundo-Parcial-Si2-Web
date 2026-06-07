import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { SessionRequestContext } from '../../auth/session-context';
import { API_BASE_URL } from '../../shared/api-base';
import { Technician, TechnicianFormModel, TechnicianStatus } from './technicians.model';

@Injectable({
  providedIn: 'root',
})
export class TechniciansService {
  private readonly http = inject(HttpClient);
  private readonly techniciansApiUrl = `${API_BASE_URL}/technicians`;

  listTechnicians(context: SessionRequestContext): Observable<Technician[]> {
    const params = context.workshopId ? new HttpParams().set('workshop_id', context.workshopId) : undefined;
    return this.http.get<Technician[]>(this.techniciansApiUrl, {
      params,
      headers: context.headers,
    });
  }

  createTechnician(
    context: SessionRequestContext,
    payload: TechnicianFormModel & { workshop_id: number | null },
  ): Observable<Technician> {
    const params = context.workshopId ? new HttpParams().set('workshop_id', context.workshopId) : undefined;
    return this.http.post<Technician>(this.techniciansApiUrl, payload, {
      params,
      headers: context.headers,
    });
  }

  updateTechnician(
    technicianId: number,
    context: SessionRequestContext,
    payload: TechnicianFormModel & { workshop_id: number | null },
  ): Observable<Technician> {
    const params = context.workshopId ? new HttpParams().set('workshop_id', context.workshopId) : undefined;
    return this.http.put<Technician>(`${this.techniciansApiUrl}/${technicianId}`, payload, {
      params,
      headers: context.headers,
    });
  }

  deleteTechnician(technicianId: number, context: SessionRequestContext): Observable<void> {
    const params = context.workshopId ? new HttpParams().set('workshop_id', context.workshopId) : undefined;
    return this.http.delete<void>(`${this.techniciansApiUrl}/${technicianId}`, {
      params,
      headers: context.headers,
    });
  }

  updateTechnicianStatus(
    technician: Technician,
    nextStatus: TechnicianStatus,
    context: SessionRequestContext,
  ): Observable<Technician> {
    const params = context.workshopId ? new HttpParams().set('workshop_id', context.workshopId) : undefined;
    return this.http.put<Technician>(`${this.techniciansApiUrl}/${technician.id}`, {
      workshop_id: technician.workshop_id ?? context.workshopId,
      full_name: technician.full_name,
      phone: technician.phone,
      email: technician.email,
      specialty: technician.specialty,
      status: nextStatus,
    }, {
      params,
      headers: context.headers,
    });
  }
}
