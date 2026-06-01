import { CommonModule, DatePipe } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { APP_SESSION_STORAGE_KEY, parseStoredSession } from '../../auth/session';
import { TECHNICIAN_SPECIALTY_OPTIONS, Technician, TechnicianFilter, TechnicianFormModel, TechnicianStatus } from './technicians.model';
import { TechniciansService } from './technicians.service';

@Component({
  selector: 'app-technicians',
  standalone: true,
  imports: [CommonModule, DatePipe, FormsModule],
  templateUrl: './technicians.component.html',
  styleUrls: ['./technicians.component.css', '../../shared/shared-pages.css'],
})
export class TechniciansComponent implements OnInit {
  readonly technicianSpecialtyOptions = TECHNICIAN_SPECIALTY_OPTIONS;

  technicians: Technician[] = [];
  technicianFilter: TechnicianFilter = 'activos';
  technicianForm: TechnicianFormModel = this.createEmptyTechnicianForm();
  showTechnicianForm = false;
  isTechniciansLoading = false;
  isSavingTechnician = false;
  editingTechnicianId: number | null = null;
  technicianFeedback = '';

  constructor(private readonly techniciansService: TechniciansService) {}

  ngOnInit(): void {
    this.loadTechnicians();
  }

  get filteredTechnicians(): Technician[] {
    if (this.technicianFilter === 'todos') {
      return this.technicians;
    }
    if (this.technicianFilter === 'historial') {
      return this.technicians.filter((technician) => technician.status === 'fuera_de_servicio');
    }
    return this.technicians.filter((technician) => technician.status !== 'fuera_de_servicio');
  }

  get currentWorkshopId(): number | null {
    if (typeof window === 'undefined') {
      return null;
    }
    const raw = window.localStorage.getItem(APP_SESSION_STORAGE_KEY) || window.sessionStorage.getItem(APP_SESSION_STORAGE_KEY);
    const session = parseStoredSession(raw);
    return session?.role === 'workshop' ? session.id : null;
  }

  createEmptyTechnicianForm(): TechnicianFormModel {
    return {
      full_name: '',
      phone: '',
      email: '',
      specialty: '',
      status: 'disponible',
    };
  }

  statusLabel(status: TechnicianStatus): string {
    if (status === 'fuera_de_servicio') {
      return 'Fuera de servicio';
    }
    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  startCreate(): void {
    this.showTechnicianForm = true;
    this.editingTechnicianId = null;
    this.technicianFeedback = '';
    this.technicianForm = this.createEmptyTechnicianForm();
  }

  resetTechnicianForm(): void {
    this.editingTechnicianId = null;
    this.technicianFeedback = '';
    this.technicianForm = this.createEmptyTechnicianForm();
  }

  cancelTechnicianForm(): void {
    this.showTechnicianForm = false;
    this.resetTechnicianForm();
  }

  editTechnician(technician: Technician): void {
    this.showTechnicianForm = true;
    this.editingTechnicianId = technician.id;
    this.technicianFeedback = '';
    this.technicianForm = {
      full_name: technician.full_name,
      phone: technician.phone,
      email: technician.email,
      specialty: technician.specialty,
      status: technician.status,
    };
  }

  submitTechnician(): void {
    const payload = {
      workshop_id: this.currentWorkshopId,
      full_name: this.technicianForm.full_name.trim(),
      phone: this.technicianForm.phone.trim(),
      email: this.technicianForm.email.trim(),
      specialty: this.technicianForm.specialty.trim(),
      status: this.technicianForm.status,
    };

    if (!payload.full_name || !payload.phone || !payload.email || !payload.specialty) {
      this.technicianFeedback = 'Completa todos los campos del tecnico antes de guardar.';
      return;
    }

    this.isSavingTechnician = true;
    this.technicianFeedback = '';

    const request = this.editingTechnicianId
      ? this.techniciansService.updateTechnician(this.editingTechnicianId, this.currentWorkshopId, payload)
      : this.techniciansService.createTechnician(this.currentWorkshopId, payload);

    request.subscribe({
      next: () => {
        this.isSavingTechnician = false;
        this.technicianFeedback = this.editingTechnicianId
          ? 'Tecnico actualizado correctamente.'
          : 'Tecnico registrado correctamente.';
        this.resetTechnicianForm();
        this.showTechnicianForm = false;
        this.loadTechnicians();
      },
      error: () => {
        this.isSavingTechnician = false;
        this.technicianFeedback = this.editingTechnicianId
          ? 'No se pudo actualizar el tecnico.'
          : 'No se pudo registrar el tecnico.';
      },
    });
  }

  deleteTechnician(technician: Technician): void {
    const confirmed = window.confirm(`¿Deseas eliminar a ${technician.full_name}?`);
    if (!confirmed) {
      return;
    }

    this.techniciansService.deleteTechnician(technician.id, this.currentWorkshopId).subscribe({
      next: () => {
        this.technicianFeedback = 'Tecnico eliminado correctamente.';
        this.loadTechnicians();
      },
      error: () => {
        this.technicianFeedback = 'No se pudo eliminar el tecnico.';
      },
    });
  }

  toggleTechnicianStatus(technician: Technician): void {
    const nextStatus: TechnicianStatus =
      technician.status === 'disponible'
        ? 'ocupado'
        : technician.status === 'ocupado'
          ? 'fuera_de_servicio'
          : 'disponible';

    this.techniciansService
      .updateTechnicianStatus(technician, nextStatus, this.currentWorkshopId)
      .subscribe({ next: () => this.loadTechnicians() });
  }

  loadTechnicians(): void {
    this.isTechniciansLoading = true;
    this.techniciansService.listTechnicians(this.currentWorkshopId).subscribe({
      next: (technicians) => {
        this.technicians = technicians;
        this.isTechniciansLoading = false;
      },
      error: () => {
        this.technicians = [];
        this.isTechniciansLoading = false;
      },
    });
  }
}
