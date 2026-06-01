import { CommonModule, DatePipe } from '@angular/common';
import { Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { WorkshopsService } from './workshops.service';
import {
  WORKSHOP_SPECIALTY_OPTIONS,
  WORKSHOP_ZONE_OPTIONS,
  WorkshopApprovalStatus,
  WorkshopFormModel,
  WorkshopRegistration,
} from './workshops.model';

declare const L: any;

@Component({
  selector: 'app-workshops',
  standalone: true,
  imports: [CommonModule, DatePipe, FormsModule],
  templateUrl: './workshops.component.html',
  styleUrls: ['./workshops.component.css', '../../shared/shared-pages.css'],
})
export class WorkshopsComponent implements OnInit, OnDestroy {
  readonly workshopZoneOptions = WORKSHOP_ZONE_OPTIONS;
  readonly workshopSpecialtyOptions = WORKSHOP_SPECIALTY_OPTIONS;
  readonly workshopsPageSize = 15;
  readonly isSecureContext =
    typeof window !== 'undefined' ? window.isSecureContext : false;

  workshops: WorkshopRegistration[] = [];
  workshopsPage = 1;
  isLoading = false;
  isUpdatingWorkshopApproval = false;
  isSavingWorkshop = false;
  showWorkshopEditModal = false;
  editingWorkshopId: number | null = null;
  workshopEditFeedback = '';
  workshopLocationMessage = '';
  isWorkshopLocationLocating = false;
  workshopForm: WorkshopFormModel = this.createEmptyWorkshopForm();

  private workshopEditMap?: any;
  private workshopEditMapMarker?: any;
  private workshopEditMapResizeTimer?: number;
  private workshopEditMapHost?: HTMLDivElement;

  constructor(private readonly workshopsService: WorkshopsService) {}

  @ViewChild('workshopEditMapCanvas')
  set workshopEditMapCanvas(element: ElementRef<HTMLDivElement> | undefined) {
    if (!element || typeof window === 'undefined' || !this.showWorkshopEditModal) {
      return;
    }

    window.setTimeout(() => {
      this.initializeWorkshopEditMap(element.nativeElement);
      this.renderWorkshopEditMap();
    });
  }

  ngOnInit(): void {
    this.loadWorkshops();
  }

  ngOnDestroy(): void {
    this.destroyWorkshopEditMap();
  }

  get paginatedWorkshops(): WorkshopRegistration[] {
    const start = (this.workshopsPage - 1) * this.workshopsPageSize;
    return this.workshops.slice(start, start + this.workshopsPageSize);
  }

  get workshopsTotalPages(): number {
    return Math.max(1, Math.ceil(this.workshops.length / this.workshopsPageSize));
  }

  get workshopsRangeStart(): number {
    if (!this.workshops.length) {
      return 0;
    }

    return (this.workshopsPage - 1) * this.workshopsPageSize + 1;
  }

  get workshopsRangeEnd(): number {
    return Math.min(this.workshopsPage * this.workshopsPageSize, this.workshops.length);
  }

  loadWorkshops(): void {
    this.isLoading = true;

    this.workshopsService
      .listWorkshops()
      .pipe(finalize(() => (this.isLoading = false)))
      .subscribe({
        next: (workshops) => {
          this.workshops = workshops;
          this.workshopsPage = 1;
        },
        error: () => {
          this.workshops = [];
          this.workshopsPage = 1;
        },
      });
  }

  goToPreviousWorkshopsPage(): void {
    this.workshopsPage = Math.max(1, this.workshopsPage - 1);
  }

  goToNextWorkshopsPage(): void {
    this.workshopsPage = Math.min(this.workshopsTotalPages, this.workshopsPage + 1);
  }

  getWorkshopStatus(createdAt: string): string {
    const created = new Date(createdAt).getTime();
    const hours = (Date.now() - created) / (1000 * 60 * 60);

    if (hours <= 3) {
      return 'Nuevo';
    }

    if (hours <= 24) {
      return 'Hoy';
    }

    return 'Pendiente';
  }

  workshopApprovalLabel(status: WorkshopApprovalStatus): string {
    if (status === 'activo') {
      return 'Activo';
    }

    if (status === 'rechazado') {
      return 'Rechazado';
    }

    return 'Pendiente';
  }

  createEmptyWorkshopForm(): WorkshopFormModel {
    return {
      workshop_name: '',
      contact_name: '',
      phone: '',
      email: '',
      zone: '',
      specialty: '',
      latitude: null,
      longitude: null,
      password: '',
    };
  }

  formatCoordinate(value: number | null): string {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      return '-';
    }

    return value.toFixed(6);
  }

  cycleWorkshopApproval(workshop: WorkshopRegistration): void {
    if (this.isUpdatingWorkshopApproval) {
      return;
    }

    const nextStatus: WorkshopApprovalStatus =
      workshop.approval_status === 'pendiente' ? 'activo' : 'rechazado';

    this.isUpdatingWorkshopApproval = true;

    this.workshopsService
      .updateWorkshopApprovalStatus(workshop.id, nextStatus)
      .pipe(finalize(() => (this.isUpdatingWorkshopApproval = false)))
      .subscribe({
        next: () => {
          this.loadWorkshops();
        },
        error: () => {
          window.alert('No se pudo actualizar el estado de aprobación del taller.');
        },
      });
  }

  editWorkshop(workshop: WorkshopRegistration): void {
    this.editingWorkshopId = workshop.id;
    this.workshopEditFeedback = '';
    this.workshopLocationMessage = '';
    this.workshopForm = {
      workshop_name: workshop.workshop_name,
      contact_name: workshop.contact_name,
      phone: workshop.phone,
      email: workshop.email,
      zone: workshop.zone,
      specialty: workshop.specialty,
      latitude: workshop.latitude,
      longitude: workshop.longitude,
      password: '',
    };
    this.showWorkshopEditModal = true;
  }

  deleteWorkshop(workshop: WorkshopRegistration): void {
    const confirmed = window.confirm(
      `¿Deseas eliminar el taller ${workshop.workshop_name}?`,
    );

    if (!confirmed) {
      return;
    }

    this.workshopsService.deleteWorkshop(workshop.id).subscribe({
      next: () => {
        this.loadWorkshops();
      },
      error: () => {
        window.alert('No se pudo eliminar el taller.');
      },
    });
  }

  cancelWorkshopEdit(): void {
    this.showWorkshopEditModal = false;
    this.editingWorkshopId = null;
    this.isSavingWorkshop = false;
    this.workshopEditFeedback = '';
    this.workshopLocationMessage = '';
    this.isWorkshopLocationLocating = false;
    this.workshopForm = this.createEmptyWorkshopForm();
    this.destroyWorkshopEditMap();
  }

  locateWorkshopEditCurrentPosition(): void {
    this.workshopLocationMessage = '';

    if (!this.isSecureContext) {
      this.workshopLocationMessage =
        'La ubicación automática del navegador solo funciona en HTTPS o en localhost. Usa el mapa manualmente o abre el sitio con HTTPS.';
      return;
    }

    if (!navigator.geolocation) {
      this.workshopLocationMessage = 'Tu navegador no soporta geolocalización.';
      return;
    }

    this.isWorkshopLocationLocating = true;

    navigator.geolocation.getCurrentPosition(
      (position) => {
        this.updateWorkshopEditLocation(
          position.coords.latitude,
          position.coords.longitude,
        );
        this.renderWorkshopEditMap(true);
        this.isWorkshopLocationLocating = false;
      },
      () => {
        this.isWorkshopLocationLocating = false;
        this.workshopLocationMessage =
          'No se pudo obtener tu ubicación actual. Revisa los permisos del navegador.';
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      },
    );
  }

  submitWorkshopEdit(): void {
    if (!this.editingWorkshopId) {
      return;
    }

    const target = this.workshops.find(
      (item) => item.id === this.editingWorkshopId,
    );

    if (!target) {
      this.workshopEditFeedback =
        'No se encontró el taller que intentas actualizar.';
      return;
    }

    const payload = {
      workshop_name: this.workshopForm.workshop_name.trim(),
      contact_name: this.workshopForm.contact_name.trim(),
      phone: this.workshopForm.phone.trim(),
      email: this.workshopForm.email.trim(),
      zone: this.workshopForm.zone.trim(),
      specialty: this.workshopForm.specialty.trim(),
      latitude: this.workshopForm.latitude,
      longitude: this.workshopForm.longitude,
      timezone: target.timezone,
      utc_offset_minutes: target.utc_offset_minutes,
      password: this.workshopForm.password.trim(),
    };

    if (
      !payload.workshop_name ||
      !payload.contact_name ||
      !payload.phone ||
      !payload.email ||
      !payload.zone ||
      !payload.specialty ||
      payload.latitude === null ||
      payload.longitude === null
    ) {
      this.workshopEditFeedback =
        'Completa Taller, Responsable, Contacto, Correo, Zona, Especialidad y Ubicación del Taller.';
      return;
    }

    if (payload.password && payload.password.length < 6) {
      this.workshopEditFeedback =
        'La nueva contraseña del taller debe tener al menos 6 caracteres.';
      return;
    }

    this.isSavingWorkshop = true;
    this.workshopEditFeedback = '';

    this.workshopsService
      .updateWorkshop(this.editingWorkshopId, payload)
      .pipe(finalize(() => (this.isSavingWorkshop = false)))
      .subscribe({
        next: () => {
          this.cancelWorkshopEdit();
          this.loadWorkshops();
        },
        error: () => {
          this.workshopEditFeedback = 'No se pudo actualizar el taller.';
        },
      });
  }

  private initializeWorkshopEditMap(element: HTMLDivElement): void {
    if (typeof L === 'undefined') {
      return;
    }

    if (this.workshopEditMapHost && this.workshopEditMapHost !== element) {
      this.destroyWorkshopEditMap();
    }

    this.workshopEditMapHost = element;

    if (!this.workshopEditMap) {
      const [latitude, longitude] = this.getWorkshopEditCoordinates();

      this.workshopEditMap = L.map(element, {
        zoomControl: true,
        scrollWheelZoom: true,
      }).setView([latitude, longitude], 13);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(this.workshopEditMap);

      this.workshopEditMapMarker = L.marker([latitude, longitude], {
        draggable: true,
      }).addTo(this.workshopEditMap);

      this.workshopEditMapMarker.on('dragend', () => {
        const position = this.workshopEditMapMarker.getLatLng();
        this.updateWorkshopEditLocation(position.lat, position.lng);
      });

      this.workshopEditMap.on(
        'click',
        (event: { latlng: { lat: number; lng: number } }) => {
          this.updateWorkshopEditLocation(event.latlng.lat, event.latlng.lng);
        },
      );
    }

    this.scheduleWorkshopEditMapResize();
  }

  private renderWorkshopEditMap(animate = false): void {
    if (!this.workshopEditMap || !this.workshopEditMapMarker) {
      return;
    }

    const [latitude, longitude] = this.getWorkshopEditCoordinates();
    this.workshopEditMapMarker.setLatLng([latitude, longitude]);
    this.workshopEditMap.setView([latitude, longitude], 15, { animate });
    this.scheduleWorkshopEditMapResize();
  }

  private updateWorkshopEditLocation(latitude: number, longitude: number): void {
    this.workshopForm = {
      ...this.workshopForm,
      latitude,
      longitude,
    };
    this.workshopLocationMessage = '';

    if (this.workshopEditMapMarker) {
      this.workshopEditMapMarker.setLatLng([latitude, longitude]);
    }
  }

  private getWorkshopEditCoordinates(): [number, number] {
    const latitude =
      typeof this.workshopForm.latitude === 'number' &&
      Number.isFinite(this.workshopForm.latitude)
        ? this.workshopForm.latitude
        : -17.7833;
    const longitude =
      typeof this.workshopForm.longitude === 'number' &&
      Number.isFinite(this.workshopForm.longitude)
        ? this.workshopForm.longitude
        : -63.1821;

    return [latitude, longitude];
  }

  private scheduleWorkshopEditMapResize(): void {
    if (typeof window === 'undefined' || !this.workshopEditMap) {
      return;
    }

    if (this.workshopEditMapResizeTimer !== undefined) {
      window.clearTimeout(this.workshopEditMapResizeTimer);
    }

    this.workshopEditMapResizeTimer = window.setTimeout(() => {
      this.workshopEditMap?.invalidateSize();
    }, 120);
  }

  private destroyWorkshopEditMap(): void {
    if (
      typeof window !== 'undefined' &&
      this.workshopEditMapResizeTimer !== undefined
    ) {
      window.clearTimeout(this.workshopEditMapResizeTimer);
      this.workshopEditMapResizeTimer = undefined;
    }

    if (this.workshopEditMap) {
      this.workshopEditMap.remove();
      this.workshopEditMap = undefined;
      this.workshopEditMapMarker = undefined;
    }

    this.workshopEditMapHost = undefined;
  }
}
