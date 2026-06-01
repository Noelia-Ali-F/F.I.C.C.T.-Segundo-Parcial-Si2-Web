import { CommonModule, DatePipe } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Client, ClientFormModel, ClientStatus } from './clients.model';
import { ClientsService } from './clients.service';

@Component({
  selector: 'app-clients',
  standalone: true,
  imports: [CommonModule, DatePipe, FormsModule],
  templateUrl: './clients.component.html',
  styleUrls: ['./clients.component.css', '../../shared/shared-pages.css'],
})
export class ClientsComponent implements OnInit {
  clients: Client[] = [];
  isClientsLoading = false;
  showClientEditModal = false;
  showClientDeleteModal = false;
  isSavingClient = false;
  editingClientId: number | null = null;
  clientEditFeedback = '';
  clientPendingDelete: Client | null = null;
  clientForm: ClientFormModel = this.createEmptyClientForm();

  constructor(private readonly clientsService: ClientsService) {}

  ngOnInit(): void {
    this.loadClients();
  }

  createEmptyClientForm(): ClientFormModel {
    return {
      identity_card: '',
      full_name: '',
      email: '',
      phone: '',
      password: '',
      role: 'client',
      status: 'active',
      accepted_terms: true,
    };
  }

  clientStatusLabel(status: ClientStatus): string {
    return status === 'active' ? 'Activo' : 'Desactivado';
  }

  loadClients(): void {
    this.isClientsLoading = true;
    this.clientsService.listClients().subscribe({
      next: (clients) => {
        this.clients = clients;
        this.isClientsLoading = false;
      },
      error: () => {
        this.clients = [];
        this.isClientsLoading = false;
      },
    });
  }

  toggleClientStatus(client: Client): void {
    const nextStatus: ClientStatus = client.status === 'active' ? 'suspended' : 'active';
    this.clientsService.updateClientStatus(client.id, nextStatus).subscribe({
      next: () => this.loadClients(),
    });
  }

  editClient(client: Client): void {
    this.editingClientId = client.id;
    this.clientEditFeedback = '';
    this.clientForm = {
      identity_card: client.identity_card,
      full_name: client.full_name,
      email: client.email,
      phone: client.phone,
      password: '',
      role: client.role,
      status: client.status,
      accepted_terms: client.accepted_terms,
    };
    this.showClientEditModal = true;
  }

  cancelClientEdit(): void {
    this.showClientEditModal = false;
    this.editingClientId = null;
    this.isSavingClient = false;
    this.clientEditFeedback = '';
    this.clientForm = this.createEmptyClientForm();
  }

  submitClientEdit(): void {
    if (!this.editingClientId) {
      return;
    }

    const payload: ClientFormModel = {
      identity_card: this.clientForm.identity_card.trim(),
      full_name: this.clientForm.full_name.trim(),
      email: this.clientForm.email.trim(),
      phone: this.clientForm.phone.trim(),
      password: this.clientForm.password.trim(),
      role: this.clientForm.role.trim(),
      status: this.clientForm.status,
      accepted_terms: this.clientForm.accepted_terms,
    };

    if (!payload.identity_card || !payload.full_name || !payload.email || !payload.phone || !payload.role) {
      this.clientEditFeedback = 'Completa carnet, nombre, correo, telefono y rol.';
      return;
    }

    if (payload.password && payload.password.length < 6) {
      this.clientEditFeedback = 'La nueva contraseña debe tener al menos 6 caracteres.';
      return;
    }

    this.isSavingClient = true;
    this.clientEditFeedback = '';

    this.clientsService.updateClient(this.editingClientId, payload).subscribe({
      next: () => {
        this.isSavingClient = false;
        this.cancelClientEdit();
        this.loadClients();
      },
      error: () => {
        this.isSavingClient = false;
        this.clientEditFeedback = 'No se pudo actualizar el cliente.';
      },
    });
  }

  deleteClient(client: Client): void {
    this.clientPendingDelete = client;
    this.showClientDeleteModal = true;
  }

  cancelClientDelete(): void {
    this.showClientDeleteModal = false;
    this.clientPendingDelete = null;
  }

  confirmClientDelete(): void {
    if (!this.clientPendingDelete) {
      return;
    }

    this.clientsService.deleteClient(this.clientPendingDelete.id).subscribe({
      next: () => {
        this.cancelClientDelete();
        this.loadClients();
      },
      error: () => {
        window.alert('No se pudo eliminar el cliente.');
      },
    });
  }
}
