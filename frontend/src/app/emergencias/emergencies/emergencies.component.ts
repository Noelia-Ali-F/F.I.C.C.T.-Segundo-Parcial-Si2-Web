import { CommonModule, DatePipe } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { APP_SESSION_STORAGE_KEY, parseStoredSession } from '../../auth/session';
import { Technician } from '../../tecnicos/technicians/technicians.model';
import { TechniciansService } from '../../tecnicos/technicians/technicians.service';
import { EmergenciesService } from './emergencies.service';
import { EmergencyStatus, MaintenanceRequest } from './emergencies.model';

@Component({
  selector: 'app-emergencies',
  standalone: true,
  imports: [CommonModule, DatePipe, FormsModule],
  templateUrl: './emergencies.component.html',
  styleUrls: ['./emergencies.component.css', '../../shared/shared-pages.css'],
})
export class EmergenciesComponent implements OnInit {
  maintenanceRequests: MaintenanceRequest[] = [];
  technicians: Technician[] = [];
  selectedMaintenanceRequestId: number | null = null;
  selectedEmergencyTechnicianId: number | null = null;
  isEmergenciesLoading = false;
  isUpdatingEmergencyStatus = false;
  isAssigningEmergencyTechnician = false;
  emergencyAssignmentFeedback = '';
  emergencyFeedback = '';
  showEmergencyModal = false;

  constructor(
    private readonly emergenciesService: EmergenciesService,
    private readonly techniciansService: TechniciansService,
  ) {}

  ngOnInit(): void {
    this.loadEmergencies();
    this.loadTechnicians();
  }

  get currentWorkshopId(): number | null {
    if (typeof window === 'undefined') {
      return null;
    }
    const raw = window.localStorage.getItem(APP_SESSION_STORAGE_KEY) || window.sessionStorage.getItem(APP_SESSION_STORAGE_KEY);
    const session = parseStoredSession(raw);
    return session?.role === 'workshop' ? session.id : null;
  }

  get selectedMaintenanceRequest(): MaintenanceRequest | null {
    return this.maintenanceRequests.find((request) => request.id === this.selectedMaintenanceRequestId) ?? null;
  }

  loadEmergencies(): void {
    this.isEmergenciesLoading = true;
    this.emergenciesService.listEmergencyReports(this.currentWorkshopId).subscribe({
      next: (reports) => {
        this.maintenanceRequests = reports.map((report) => this.emergenciesService.mapEmergencyReportToRequest(report));
        this.selectedMaintenanceRequestId = this.maintenanceRequests[0]?.id ?? null;
        this.selectedEmergencyTechnicianId = this.selectedMaintenanceRequest?.assignedTechnicianId ?? null;
        this.isEmergenciesLoading = false;
      },
      error: () => {
        this.maintenanceRequests = [];
        this.selectedMaintenanceRequestId = null;
        this.isEmergenciesLoading = false;
      },
    });
  }

  loadTechnicians(): void {
    this.techniciansService.listTechnicians(this.currentWorkshopId).subscribe({
      next: (technicians) => {
        this.technicians = technicians.filter((technician) => technician.status !== 'fuera_de_servicio');
      },
      error: () => {
        this.technicians = [];
      },
    });
  }

  openEmergencyModal(request: MaintenanceRequest): void {
    this.selectedMaintenanceRequestId = request.id;
    this.selectedEmergencyTechnicianId = request.assignedTechnicianId;
    this.emergencyAssignmentFeedback = '';
    this.emergencyFeedback = '';
    this.showEmergencyModal = true;
  }

  closeEmergencyModal(): void {
    this.showEmergencyModal = false;
    this.selectedEmergencyTechnicianId = null;
    this.emergencyAssignmentFeedback = '';
    this.emergencyFeedback = '';
  }

  updateSelectedEmergencyStatus(nextStatus: Exclude<EmergencyStatus, 'pendiente'>): void {
    const selected = this.selectedMaintenanceRequest;
    if (!selected || this.isUpdatingEmergencyStatus) {
      return;
    }
    this.isUpdatingEmergencyStatus = true;
    this.emergenciesService.updateEmergencyStatus(selected.id, nextStatus, this.currentWorkshopId).subscribe({
      next: () => {
        this.isUpdatingEmergencyStatus = false;
        this.emergencyFeedback = `Emergencia ${nextStatus === 'activo' ? 'aceptada' : 'rechazada'} correctamente.`;
        this.loadEmergencies();
      },
      error: () => {
        this.isUpdatingEmergencyStatus = false;
        this.emergencyFeedback = 'No se pudo actualizar el estado de la emergencia.';
      },
    });
  }

  assignSelectedEmergencyTechnician(): void {
    const selected = this.selectedMaintenanceRequest;
    if (!selected || !this.currentWorkshopId || !this.selectedEmergencyTechnicianId || this.isAssigningEmergencyTechnician) {
      return;
    }
    this.isAssigningEmergencyTechnician = true;
    this.emergencyAssignmentFeedback = '';
    this.emergenciesService.assignTechnician(selected.id, this.currentWorkshopId, this.selectedEmergencyTechnicianId).subscribe({
      next: () => {
        this.isAssigningEmergencyTechnician = false;
        this.emergencyAssignmentFeedback = 'Tecnico asignado correctamente.';
        this.loadEmergencies();
      },
      error: () => {
        this.isAssigningEmergencyTechnician = false;
        this.emergencyAssignmentFeedback = 'No se pudo asignar el tecnico.';
      },
    });
  }

  deleteEmergency(request: MaintenanceRequest): void {
    const confirmed = window.confirm(`¿Deseas eliminar la emergencia ${request.code}?`);
    if (!confirmed) {
      return;
    }
    this.emergenciesService.deleteEmergency(request.id, this.currentWorkshopId).subscribe({
      next: () => this.loadEmergencies(),
      error: () => window.alert('No se pudo eliminar la emergencia.'),
    });
  }

  formatPrice(price: number | null): string {
    return this.emergenciesService.formatReportPrice(price);
  }
}
