import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../../shared/api-base';
import { Client, ClientFormModel, ClientStatus } from './clients.model';

@Injectable({
  providedIn: 'root',
})
export class ClientsService {
  private readonly http = inject(HttpClient);
  private readonly clientsApiUrl = `${API_BASE_URL}/clients`;

  listClients(): Observable<Client[]> {
    return this.http.get<Client[]>(this.clientsApiUrl);
  }

  updateClientStatus(clientId: number, status: ClientStatus): Observable<Client> {
    return this.http.put<Client>(`${this.clientsApiUrl}/${clientId}/status`, { status });
  }

  updateClient(clientId: number, payload: ClientFormModel): Observable<Client> {
    return this.http.put<Client>(`${this.clientsApiUrl}/${clientId}`, payload);
  }

  deleteClient(clientId: number): Observable<void> {
    return this.http.delete<void>(`${this.clientsApiUrl}/${clientId}`);
  }
}
