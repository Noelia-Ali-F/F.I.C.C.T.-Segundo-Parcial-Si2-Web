import { CommonModule, DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, ElementRef, OnDestroy, ViewChild, inject } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import {
  APP_SESSION_STORAGE_KEY,
  AppSession,
  clearStoredSession,
  isGlobalAdmin,
  isSucursalAdmin,
  isTechnicianRole,
  isTenantRole,
  isTenantSuperadmin,
  parseStoredSession,
} from '../auth/session';
import { RealtimeService } from '../realtime/realtime.service';
import { ConnectionState } from '../realtime/realtime.types';
import { API_BASE_URL, BACKEND_BASE_URL } from '../shared/api-base';

declare const L: any;

type SucursalRecord = {
  id: number;
  nombre: string;
  direccion: string;
  zona: string | null;
  ciudad: string;
  latitud: number | null;
  longitud: number | null;
  telefono: string | null;
  responsable: string | null;
  workshop_id: number | null;
  workshop_name: string | null;
  workshop_specialty: string | null;
  especialidades: string[];
  workshop_approval_status: string | null;
  workshop_availability_status: string | null;
  technicians_count: number;
  estado: string;
};

type SucursalZoneOption = {
  label: string;
  value: string;
};

type ReverseGeocodeResponse = {
  display_name?: string;
  address?: {
    road?: string;
    pedestrian?: string;
    suburb?: string;
    neighbourhood?: string;
    city?: string;
    town?: string;
    village?: string;
  };
};

type SucursalFormModel = {
  nombre: string;
  direccion: string;
  zona: string;
  ciudad: string;
  latitud: number | null;
  longitud: number | null;
  telefono: string;
  responsable: string;
  especialidades: string[];
};

type UsuarioEmpresaRecord = {
  id: number;
  email: string;
  full_name: string;
  phone: string;
  role: string;
  sucursal_id: number | null;
  estado: string;
};

type UsuarioEmpresaFormModel = {
  email: string;
  full_name: string;
  phone: string;
  password: string;
  role: string;
  sucursal_id: number | null;
};

type DashboardSection =
  | 'dashboard'
  | 'workshops'
  | 'technicians'
  | 'clients'
  | 'maintenance'
  | 'emergencies'
  | 'reports'
  | 'audit'
  | 'sync'
  | 'quotation_requests'
  | 'quotation_history'
  | 'contracted_services'
  | 'tenants'
  | 'sucursales'
  | 'usuarios_empresa';
type SyncTab = 'queue' | 'errors' | 'history';
type TechnicianStatus = 'disponible' | 'ocupado' | 'fuera_de_servicio';
type TechnicianFilter = 'activos' | 'todos' | 'historial';
type MaintenanceFilter = 'todas' | 'pendiente' | 'activo' | 'rechazado' | 'historial';
type WorkshopApprovalStatus = 'pendiente' | 'activo' | 'rechazado';
type ClientStatus = 'active' | 'suspended';
type AuditTone = 'info' | 'success' | 'warning' | 'danger';
type EmergencyTimelineStatus =
  | 'solicitud_recibida'
  | 'en_revision'
  | 'auxilio_asignado'
  | 'auxilio_en_camino'
  | 'tecnico_en_sitio'
  | 'servicio_en_proceso'
  | 'servicio_finalizado'
  | 'solicitud_cancelada';
type LegacyEmergencyStatus = 'pendiente' | 'activo' | 'rechazado';
type EmergencyStatus = LegacyEmergencyStatus | EmergencyTimelineStatus;

const TECHNICIAN_SPECIALTY_OPTIONS = [
  'Batería',
  'Neumático',
  'Combustible',
  'Motor',
  'Sistema eléctrico',
  'Accidente',
  'Cerrajería / llaves',
];

const ACTIVE_TECHNICIAN_STATUSES: TechnicianStatus[] = ['disponible', 'ocupado'];

const WORKSHOP_ZONE_OPTIONS = [
  'zona norte',
  'zona sur',
  'zona este',
  'zona oeste',
  'zona centro',
];

const SUCURSAL_ZONE_OPTIONS: SucursalZoneOption[] = [
  { label: 'zona norte', value: 'Norte' },
  { label: 'zona sur', value: 'Sur' },
  { label: 'zona este', value: 'Este' },
  { label: 'zona oeste', value: 'Oeste' },
  { label: 'zona centro', value: 'Centro' },
];

const SANTA_CRUZ_DEFAULT_COORDINATES = {
  latitud: -17.7833,
  longitud: -63.1821,
};

const WORKSHOP_SPECIALTY_OPTIONS = [
  'Batería',
  'Neumático',
  'Combustible',
  'Motor',
  'Sistema eléctrico',
  'Accidente',
  'Cerrajería / llaves',
];

const SUCURSAL_SPECIALTY_OPTIONS = [
  'Batería',
  'Motor',
  'Electricidad',
  'Llanta',
  'Choque',
  'Grúa',
  'Mecánica general',
];

const EMERGENCY_TIMELINE_STEPS: Array<{
  status: EmergencyTimelineStatus;
  label: string;
  icon: string;
}> = [
  { status: 'solicitud_recibida', label: 'Solicitud recibida', icon: '◉' },
  { status: 'en_revision', label: 'En revisión', icon: '◌' },
  { status: 'auxilio_asignado', label: 'Auxilio asignado', icon: '✓' },
  { status: 'auxilio_en_camino', label: 'Auxilio en camino', icon: '➜' },
  { status: 'tecnico_en_sitio', label: 'Técnico en sitio', icon: '📍' },
  { status: 'servicio_en_proceso', label: 'Servicio en proceso', icon: '⚙' },
  { status: 'servicio_finalizado', label: 'Servicio finalizado', icon: '★' },
  { status: 'solicitud_cancelada', label: 'Cancelada', icon: '✕' },
];

const LEGACY_TO_TIMELINE_STATUS_MAP: Record<LegacyEmergencyStatus, EmergencyTimelineStatus> = {
  pendiente: 'solicitud_recibida',
  activo: 'auxilio_asignado',
  rechazado: 'solicitud_cancelada',
};

type RealtimeRefreshRequest = {
  overview?: boolean;
  emergencies?: boolean;
  quotationRequests?: boolean;
  quotationHistory?: boolean;
  contractedServices?: boolean;
  tracking?: boolean;
};

const DASHBOARD_EMERGENCY_REFRESH_EVENT_TYPES = new Set([
  'emergency_registered',
  'technician_assigned',
  'emergency_status_updated',
  'technician_on_the_way',
  'technician_on_site',
  'service_started',
  'service_finished',
  'request_rejected',
]);

const DASHBOARD_QUOTATION_REFRESH_EVENT_TYPES = new Set([
  'quotation_requested',
  'quotation_submitted',
  'quotation_accepted',
  'quotation_request_sent',
  'quotation_offer_received',
  'quotation_offer_selected',
  'quotation_offer_not_selected',
  'quotation_expired',
  'quotation_request_cancelled',
]);

type DashboardStat = {
  label: string;
  value: string;
  detail: string;
  trend: string;
  tone: 'gold' | 'blue' | 'teal' | 'slate';
};

type DashboardOperationalSummaryItem = {
  label: string;
  value: string;
  detail: string;
};

type DashboardStatusBreakdownItem = {
  status: EmergencyTimelineStatus;
  label: string;
  count: number;
};

type DashboardTenantRankingItem = {
  workshop_id: number | null;
  workshop_name: string;
  total_requests: number;
  active_requests: number;
  completed_requests: number;
  cancelled_requests: number;
  technicians_available: number;
};

type DashboardZoneBreakdownItem = {
  zone: string;
  count: number;
};

type DashboardIncidentTypeBreakdownItem = {
  incident_type: string;
  label: string;
  count: number;
};

type DashboardEfficiencyRankingItem = {
  workshop_id: number | null;
  workshop_name: string;
  completed_services: number;
  avg_assignment_minutes: number | null;
  avg_arrival_minutes: number | null;
  avg_resolution_minutes: number | null;
  sla_compliance_percent: number | null;
};

type DashboardRecentEmergencyItem = {
  emergency_id: number;
  code: string;
  client_name: string;
  vehicle_name: string;
  status: EmergencyStatus;
  status_label: string;
  workshop_name: string | null;
  created_at: string;
};

type DashboardOperationalOverview = {
  scope: 'global' | 'global_saas' | 'workshop' | 'tenant' | 'sucursal' | 'technician' | 'client';
  workshop_id: number | null;
  workshop_name: string | null;
  generated_at: string;
  kpis: DashboardStat[];
  summary: DashboardOperationalSummaryItem[];
  status_breakdown: DashboardStatusBreakdownItem[];
  tenant_ranking: DashboardTenantRankingItem[];
  zone_breakdown: DashboardZoneBreakdownItem[];
  analytics_summary: DashboardOperationalSummaryItem[];
  incident_type_breakdown: DashboardIncidentTypeBreakdownItem[];
  efficiency_ranking: DashboardEfficiencyRankingItem[];
  recent_emergencies: DashboardRecentEmergencyItem[];
};

type DashboardItem = {
  title: string;
  subtitle: string;
  meta: string;
  priority: 'Alta' | 'Media' | 'Seguimiento';
};

type AuditItem = {
  title: string;
  detail: string;
  meta: string;
  createdAt: string;
  tone: AuditTone;
};

type MaintenanceRequest = {
  id: number;
  localId: string | null;
  code: string;
  client: string;
  vehicle: string;
  location: string;
  priority: 'Alta' | 'Media' | 'Baja';
  status: EmergencyStatus;
  price: number | null;
  distance: string;
  detail: string;
  reportedAt: string;
  createdAt: string;
  latitude: number | null;
  longitude: number | null;
  nearestWorkshopId: number | null;
  nearestWorkshopName: string | null;
  problemType: string;
  standardizedProblemType: string | null;
  clientDescription: string | null;
  audioTranscript: string | null;
  photoUrls: string[];
  audioUrl: string | null;
  mapEmbedUrl: SafeResourceUrl | null;
  mapExternalUrl: string | null;
  assignmentId: number | null;
  assignmentStatus: string | null;
  assignedTechnicianId: number | null;
  assignedTechnicianName: string | null;
  assignedTechnicianPhone: string | null;
  assignedTechnicianSpecialty: string | null;
  rejectionReason: string | null;
  rejectedAt: string | null;
  horaLlegada: string | null;
  latitudLlegada: number | null;
  longitudLlegada: number | null;
};

type EmergencyReport = {
  id: number;
  local_id: string | null;
  client_id: number | null;
  client_name: string | null;
  vehicle_name: string;
  vehicle_plate: string;
  problem_type: string;
  price: number | null;
  emergency_status: EmergencyStatus | null;
  problem_type_standardized: string | null;
  photo_problem_type_standardized?: string | null;
  photo_classification_confidence?: number | null;
  photo_classification_error?: string | null;
  description: string | null;
  audio_transcript: string | null;
  audio_transcript_status?: string | null;
  audio_transcript_error?: string | null;
  photo_paths?: string[] | string | null;
  photo_urls: string[] | string | null;
  audio_url: string | null;
  latitude: number | null;
  longitude: number | null;
  address: string | null;
  zone: string | null;
  nearest_workshop_id: number | null;
  nearest_workshop_name: string | null;
  nearest_workshop_specialty: string | null;
  nearest_workshop_zone: string | null;
  nearest_workshop_distance_meters: number | null;
  assignment_id: number | null;
  assignment_status: string | null;
  assigned_technician_id: number | null;
  assigned_technician_name: string | null;
  assigned_technician_phone: string | null;
  assigned_technician_email: string | null;
  assigned_technician_specialty: string | null;
  rejection_reason: string | null;
  rejected_at: string | null;
  hora_llegada: string | null;
  latitud_llegada: number | null;
  longitud_llegada: number | null;
  updated_at: string | null;
  created_at: string;
};

type WorkshopRegistration = {
  id: number;
  workshop_name: string;
  contact_name: string;
  phone: string;
  email: string;
  zone: string;
  specialty: string;
  approval_status: WorkshopApprovalStatus;
  availability_status?: string;
  latitude: number | null;
  longitude: number | null;
  timezone: string | null;
  utc_offset_minutes: number | null;
  created_at: string;
};

type EmergencyTimelineEntry = {
  status: EmergencyTimelineStatus;
  observation?: string | null;
  changed_by_role?: string | null;
  changed_by_user_id?: number | null;
  created_at: string;
};

type EmergencyTimelineResponse = {
  emergency_id: number;
  current_status: EmergencyStatus | null;
  timeline: EmergencyTimelineEntry[];
};

type EmergencyRejectionResponse = {
  emergency: EmergencyReport;
  timeline: EmergencyTimelineResponse;
};

type EmergencyTrackingActor = {
  id: number | null;
  name: string | null;
  latitude: number | null;
  longitude: number | null;
  address?: string | null;
  last_location_at?: string | null;
};

type EmergencyTrackingRoute = {
  distance_meters: number;
  distance_text: string;
  duration_seconds: number;
  duration_text: string;
  polyline: number[][] | null;
  provider: string;
};

type EmergencyTrackingResponse = {
  emergency_id: number;
  client: EmergencyTrackingActor;
  workshop: EmergencyTrackingActor;
  technician: EmergencyTrackingActor;
  route: EmergencyTrackingRoute;
  status: EmergencyStatus;
};

type Technician = {
  id: number;
  workshop_id: number | null;
  usuario_tenant_id: number | null;
  full_name: string;
  phone: string;
  email: string;
  specialty: string;
  status: TechnicianStatus;
  sucursal_id: number | null;
  sucursal_nombre: string | null;
  created_at: string;
  updated_at: string;
};

type TechnicianFormModel = {
  full_name: string;
  phone: string;
  email: string;
  specialty: string;
  status: TechnicianStatus;
  sucursal_id: number | null;
};

type Client = {
  id: number;
  identity_card: string;
  full_name: string;
  email: string;
  phone: string;
  role: string;
  status: ClientStatus;
  accepted_terms: boolean;
  created_at: string;
  updated_at: string;
};

type ClientFormModel = {
  identity_card: string;
  full_name: string;
  email: string;
  phone: string;
  password: string;
  role: string;
  status: ClientStatus;
  accepted_terms: boolean;
};

type TenantRecord = {
  id: number;
  nombre: string;
  descripcion: string | null;
  estado: string;
  created_at: string;
  updated_at: string;
};

type WorkshopFormModel = {
  workshop_name: string;
  contact_name: string;
  phone: string;
  email: string;
  zone: string;
  specialty: string;
  latitude: number | null;
  longitude: number | null;
  password: string;
};

type QuotationRequest = {
  id: number;
  emergency_id: number | null;
  client_id: number | null;
  status: string;
  requested_workshops_count: number;
  received_offers_count: number;
  selected_offer_id: number | null;
  requested_at: string;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
  workshop_invitation_status?: string | null;
  notified_at?: string | null;
  client_name?: string | null;
  client_phone?: string | null;
  workshop_names?: string | null;
  visible_workshops_count?: number | null;
  selected_workshop_name?: string | null;
  selected_offer_price?: number | null;
};

type QuotationOffer = {
  id: number;
  quotation_request_id: number;
  workshop_id: number;
  workshop_name: string | null;
  price: number | null;
  service_description: string | null;
  spare_parts?: string | null;
  labor_detail?: string | null;
  labor_cost?: number | null;
  spare_parts_cost?: number | null;
  estimated_service_time: string | null;
  estimated_arrival_time: string | null;
  warranty: string | null;
  validity_days: number | null;
  observations: string | null;
  condiciones_servicio?: string | null;
  status: string;
  created_at: string;
  expires_at: string | null;
  emergency_id?: number | null;
  request_status?: string | null;
  client_name?: string | null;
};

type QuotationOfferFormModel = {
  price: number | null;
  service_description: string;
  spare_parts: string;
  labor_detail: string;
  labor_cost: number | null;
  spare_parts_cost: number | null;
  estimated_service_time: string;
  estimated_arrival_time: string;
  warranty: string;
  validity_days: number | null;
  observations: string;
  condiciones_servicio: string;
};

type ContractedService = {
  id: number;
  quotation_request_id: number;
  workshop_id: number;
  price: number | null;
  service_description: string | null;
  spare_parts: string | null;
  labor_detail: string | null;
  labor_cost: number | null;
  spare_parts_cost: number | null;
  estimated_service_time: string | null;
  estimated_arrival_time: string | null;
  warranty: string | null;
  validity_days: number | null;
  observations: string | null;
  condiciones_servicio: string | null;
  status: string;
  offer_created_at: string | null;
  offer_expires_at: string | null;
  emergency_id: number | null;
  client_id: number | null;
  requested_at: string | null;
  request_expires_at: string | null;
  vehicle_name: string | null;
  vehicle_plate: string | null;
  problem_type: string | null;
  address: string | null;
  zone: string | null;
  latitude: number | null;
  longitude: number | null;
  emergency_description: string | null;
  emergency_status: string | null;
  emergency_created_at: string | null;
  hora_llegada: string | null;
  latitud_llegada: number | null;
  longitud_llegada: number | null;
  client_name: string | null;
  client_phone: string | null;
  workshop_name?: string | null;
};

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [CommonModule, DatePipe, FormsModule, RouterLink],
  template: `
    <main
      class="dashboard-page"
      [class.is-sidebar-collapsed]="isSidebarCollapsed"
      [class.is-exporting-report]="isExportingReport"
    >
      <aside class="dashboard-sidebar" [class.is-collapsed]="isSidebarCollapsed">
        <a class="dashboard-brand" routerLink="/">
          <span class="dashboard-brand-mark">
            <img src="/favicon.svg" alt="Logo ACB" />
          </span>
          <span>
            <strong>Taller ACB</strong>
            <small>Centro de operaciones</small>
          </span>
        </a>

        <nav class="dashboard-menu">
          <div class="dashboard-menu-group">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'dashboard'"
              (click)="selectSection('dashboard')"
              *ngIf="canAccessSection('dashboard')"
            >
              <span class="dashboard-menu-icon">⌂</span>
              <span>Dashboard</span>
            </button>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('workshops')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'workshops'"
              (click)="selectSection('workshops')"
            >
              <span class="dashboard-menu-icon">◫</span>
              <span>{{ isGlobalAdminSession ? 'Empresas' : 'Taller' }}</span>
              <span class="dashboard-menu-badge">Live</span>
            </button>

            <div class="dashboard-submenu">
              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'workshops'"
                (click)="selectSection('workshops')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>{{ isGlobalAdminSession ? 'Solicitudes de Empresas' : 'Solicitudes' }}</span>
                <strong>{{ workshops.length | number: '2.0-0' }}</strong>
              </button>
            </div>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('technicians')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'technicians'"
              (click)="selectSection('technicians')"
            >
              <span class="dashboard-menu-icon">◔</span>
              <span>Tecnicos</span>
            </button>

            <div class="dashboard-submenu">
              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'technicians'"
                (click)="selectSection('technicians')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>Lista de Tecnicos</span>
                <strong>{{ technicians.length | number: '2.0-0' }}</strong>
              </button>
            </div>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('clients')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'clients'"
              (click)="selectSection('clients')"
            >
              <span class="dashboard-menu-icon">◉</span>
              <span>Clientes</span>
            </button>

            <div class="dashboard-submenu">
              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'clients'"
                (click)="selectSection('clients')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>Lista de Clientes</span>
                <strong>{{ clients.length | number: '2.0-0' }}</strong>
              </button>
            </div>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('emergencies')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'emergencies'"
              (click)="selectSection('emergencies')"
            >
              <span class="dashboard-menu-icon">⬒</span>
              <span>Emergencias</span>
              <span class="dashboard-menu-badge">24/7</span>
            </button>

            <div class="dashboard-submenu">
              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'emergencies'"
                (click)="selectSection('emergencies')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>Solicitudes de emergencia</span>
                <strong>{{ maintenanceRequests.length | number: '2.0-0' }}</strong>
              </button>
            </div>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('reports')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'reports'"
              (click)="selectSection('reports')"
            >
              <span class="dashboard-menu-icon">▥</span>
              <span>Reportes</span>
            </button>

            <div class="dashboard-submenu">
              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'reports'"
                (click)="selectSection('reports')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>Trabajos realizados</span>
                <strong>{{ reportWorkRequests.length | number: '2.0-0' }}</strong>
              </button>
            </div>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('audit')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'audit'"
              (click)="selectSection('audit')"
            >
              <span class="dashboard-menu-icon">▣</span>
              <span>Bitacora</span>
            </button>

            <div class="dashboard-submenu">
              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'audit'"
                (click)="selectSection('audit')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>Actividad reciente</span>
                <strong>{{ auditItems.length | number: '2.0-0' }}</strong>
              </button>
            </div>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('sync')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'sync'"
              (click)="selectSection('sync')"
            >
              <span class="dashboard-menu-icon">⇄</span>
              <span>Sincronización</span>
              <span class="dashboard-menu-badge" *ngIf="syncStats.pending > 0">{{ syncStats.pending }}</span>
            </button>

            <div class="dashboard-submenu">
              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'sync'"
                (click)="selectSection('sync')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>Incidentes sincronizados</span>
                <strong>{{ syncStats.total | number: '2.0-0' }}</strong>
              </button>
            </div>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('quotation_requests')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'quotation_requests' || selectedSection === 'quotation_history'"
              (click)="selectSection('quotation_requests')"
            >
              <span class="dashboard-menu-icon">📋</span>
              <span>Cotizaciones</span>
              <span class="dashboard-menu-badge" *ngIf="quotationRequestsBadgeCount > 0">{{ quotationRequestsBadgeCount }}</span>
            </button>

            <div class="dashboard-submenu">
              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'quotation_requests'"
                (click)="selectSection('quotation_requests')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>Solicitudes recibidas</span>
                <strong *ngIf="quotationRequestsBadgeCount > 0">{{ quotationRequestsBadgeCount }}</strong>
              </button>

              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'quotation_history'"
                (click)="selectSection('quotation_history')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>Mis cotizaciones</span>
                <strong *ngIf="quotationActiveOffersCount > 0">{{ quotationActiveOffersCount }}</strong>
              </button>

              <button
                class="dashboard-submenu-item"
                type="button"
                [class.is-active]="selectedSection === 'contracted_services'"
                (click)="selectSection('contracted_services')"
              >
                <span class="dashboard-submenu-bullet"></span>
                <span>Servicios contratados</span>
                <strong *ngIf="contractedServices.length > 0">{{ contractedServices.length }}</strong>
              </button>
            </div>
          </div>

          <button
            class="dashboard-menu-link"
            type="button"
            *ngIf="!isWorkshopSession && !isTenantSession"
            [class.is-active]="selectedSection === 'tenants'"
            (click)="selectSection('tenants')"
          >
            <span class="dashboard-menu-icon">🏢</span>
            <span>Organizaciones</span>
            <span class="dashboard-menu-badge" *ngIf="tenants.length > 0">{{ tenants.length }}</span>
          </button>

          <!-- ── SECCIONES EXCLUSIVAS PARA USUARIOS TENANT ────────────── -->
          <div class="dashboard-menu-group" *ngIf="canAccessSection('sucursales')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'sucursales'"
              (click)="selectSection('sucursales')"
            >
              <span class="dashboard-menu-icon">📍</span>
              <span>Mis Sucursales</span>
              <span class="dashboard-menu-badge" *ngIf="sucursales.length > 0">{{ sucursales.length }}</span>
            </button>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('usuarios_empresa')">
            <button
              class="dashboard-menu-link"
              type="button"
              [class.is-active]="selectedSection === 'usuarios_empresa'"
              (click)="selectSection('usuarios_empresa')"
            >
              <span class="dashboard-menu-icon">👥</span>
              <span>Usuarios</span>
              <span class="dashboard-menu-badge" *ngIf="usuariosEmpresa.length > 0">{{ usuariosEmpresa.length }}</span>
            </button>
          </div>
        </nav>

        <section class="dashboard-sidebar-card">
          <span>Turno activo</span>
          <strong *ngIf="!isTenantSession">Administración general</strong>
          <strong *ngIf="isTenantSession">{{ tenantDisplayName }}</strong>
          <p *ngIf="!isTenantSession">Supervisión de afiliaciones, validación de talleres y control del panel comercial.</p>
          <p *ngIf="isTenantSession">Panel de tu empresa. Solo ves los datos de tu organización.</p>
        </section>
      </aside>

      <section class="dashboard-content">
        <header class="dashboard-topbar">
          <div class="dashboard-topbar-copy">
            <button
              class="dashboard-sidebar-toggle"
              type="button"
              (click)="toggleSidebar()"
              [attr.aria-label]="isSidebarCollapsed ? 'Expandir menu lateral' : 'Contraer menu lateral'"
            >
              ☰
            </button>
            <span class="dashboard-topbar-kicker">Panel interno</span>
            <strong>{{ sectionTitle }}</strong>
          </div>

          <div class="dashboard-topbar-actions">
            <div class="dashboard-user-pill">
              <span class="dashboard-user-avatar">{{ userInitials }}</span>
              <span class="dashboard-user-name">{{ userDisplayName }}</span>
            </div>

            <button
              class="dashboard-topbar-icon dashboard-notification-button"
              type="button"
              [class.has-alerts]="pendingEmergencyNotifications > 0"
              [attr.aria-label]="
                pendingEmergencyNotifications > 0
                  ? pendingEmergencyNotifications + ' emergencias pendientes'
                  : 'Notificaciones'
              "
              (click)="openEmergencyNotifications()"
            >
              🔔
              <span class="dashboard-notification-badge" *ngIf="pendingEmergencyNotifications > 0">
                {{ pendingEmergencyNotifications > 99 ? '99+' : pendingEmergencyNotifications }}
              </span>
            </button>

            <button
              class="dashboard-topbar-icon dashboard-topbar-logout"
              type="button"
              aria-label="Cerrar sesion"
              (click)="logout()"
            >
              ⎋
            </button>
          </div>
        </header>

        <section
          class="dashboard-stats"
          *ngIf="selectedSection === 'dashboard' || selectedSection === 'technicians' || selectedSection === 'clients'"
          [class.is-compact]="selectedSection === 'technicians' || selectedSection === 'clients'"
        >
          <article class="dashboard-stat-card" *ngFor="let stat of stats" [attr.data-tone]="stat.tone">
            <div class="dashboard-stat-top">
              <span>{{ stat.label }}</span>
              <small>{{ stat.trend }}</small>
            </div>
            <strong>{{ stat.value }}</strong>
            <p>{{ stat.detail }}</p>
          </article>
        </section>

        <section class="dashboard-grid">
          <article class="dashboard-panel dashboard-panel-accent" *ngIf="selectedSection === 'dashboard'">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">{{ overviewHeroKicker }}</p>
                <h2>{{ overviewHeroTitle }}</h2>
              </div>
              <span class="dashboard-toolbar-note" *ngIf="operationalOverview">
                Actualizado {{ operationalOverview.generated_at | date: 'shortTime' }}
              </span>
            </div>

            <p class="dashboard-loading" *ngIf="isOperationalOverviewLoading && !operationalOverview">
              Cargando indicadores operacionales...
            </p>

            <div class="operational-summary-grid" *ngIf="operationalOverview">
              <article class="operational-summary-item" *ngFor="let item of operationalOverview.summary">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
                <p>{{ item.detail }}</p>
              </article>
            </div>

            <p class="dashboard-empty" *ngIf="!isOperationalOverviewLoading && !operationalOverview">
              No se pudo cargar el resumen operacional del dashboard.
            </p>
          </article>

          <article class="dashboard-panel" *ngIf="selectedSection === 'dashboard'">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">{{ statusPanelKicker }}</p>
                <h2>{{ statusPanelTitle }}</h2>
              </div>
            </div>

            <div class="operational-breakdown-list" *ngIf="operationalOverview?.status_breakdown?.length; else noStatusBreakdown">
              <article class="operational-breakdown-item" *ngFor="let item of operationalOverview?.status_breakdown">
                <div>
                  <strong>{{ item.label }}</strong>
                  <p>{{ statusPanelItemDetail(item.count) }}</p>
                </div>
                <span class="maintenance-request-status" [attr.data-status]="statusFilterGroup(item.status)">
                  {{ item.count }}
                </span>
              </article>
            </div>
            <ng-template #noStatusBreakdown>
              <p class="dashboard-empty">{{ statusPanelEmptyMessage }}</p>
            </ng-template>
          </article>

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'dashboard' && showComparativeOperationalPanels">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Rendimiento por tenant</p>
                <h2>Ranking de Talleres</h2>
              </div>
            </div>

            <div class="operational-ranking-list" *ngIf="operationalOverview?.tenant_ranking?.length; else noTenantRanking">
              <article class="operational-ranking-item" *ngFor="let item of operationalOverview?.tenant_ranking">
                <div>
                  <strong>{{ item.workshop_name }}</strong>
                  <p>
                    {{ item.total_requests }} solicitudes · {{ item.active_requests }} activas ·
                    {{ item.completed_requests }} finalizadas
                  </p>
                </div>
                <span>{{ item.technicians_available }} técnicos libres</span>
              </article>
            </div>
            <ng-template #noTenantRanking>
              <p class="dashboard-empty">Aún no hay datos suficientes para comparar talleres.</p>
            </ng-template>
          </article>

          <article class="dashboard-panel" *ngIf="selectedSection === 'dashboard' && showComparativeOperationalPanels">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Cobertura operativa</p>
                <h2>Zonas con Mayor Demanda</h2>
              </div>
            </div>

            <div class="dashboard-mini-list" *ngIf="operationalOverview?.zone_breakdown?.length; else noZones">
              <article class="dashboard-mini-item" *ngFor="let zone of operationalOverview?.zone_breakdown">
                <div>
                  <strong>{{ zone.zone }}</strong>
                  <p>Solicitudes registradas desde esta zona del sistema.</p>
                </div>
                <span>{{ zone.count }}</span>
              </article>
            </div>
            <ng-template #noZones>
              <p class="dashboard-empty">Todavía no hay zonas con carga operativa para mostrar.</p>
            </ng-template>
          </article>

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'dashboard' && showOperationalAnalyticsPanel">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Analítica operacional</p>
                <h2>KPIs del Enunciado</h2>
              </div>
            </div>

            <div class="operational-summary-grid" *ngIf="operationalOverview?.analytics_summary?.length">
              <article class="operational-summary-item" *ngFor="let item of operationalOverview?.analytics_summary">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
                <p>{{ item.detail }}</p>
              </article>
            </div>

            <div class="dashboard-mini-list" *ngIf="operationalOverview?.incident_type_breakdown?.length; else noIncidentTypeBreakdown">
              <article class="dashboard-mini-item" *ngFor="let item of operationalOverview?.incident_type_breakdown">
                <div>
                  <strong>{{ item.label }}</strong>
                  <p>Incidentes reales clasificados dentro del scope actual.</p>
                </div>
                <span>{{ item.count }}</span>
              </article>
            </div>
            <ng-template #noIncidentTypeBreakdown>
              <p class="dashboard-empty">Todavía no hay incidentes tipificados suficientes para mostrar.</p>
            </ng-template>

            <div class="operational-ranking-list" *ngIf="operationalOverview?.efficiency_ranking?.length; else noEfficiencyRanking">
              <article class="operational-ranking-item" *ngFor="let item of operationalOverview?.efficiency_ranking">
                <div>
                  <strong>{{ item.workshop_name }}</strong>
                  <p>
                    Asignación: {{ formatAnalyticsMinutes(item.avg_assignment_minutes) }} ·
                    Llegada: {{ formatAnalyticsMinutes(item.avg_arrival_minutes) }} ·
                    SLA: {{ formatAnalyticsPercent(item.sla_compliance_percent) }}
                  </p>
                </div>
                <span>{{ item.completed_services }} finalizados</span>
              </article>
            </div>
            <ng-template #noEfficiencyRanking>
              <p class="dashboard-empty">Todavía no hay suficiente historial para medir eficiencia por taller.</p>
            </ng-template>
          </article>

          <article class="dashboard-panel" *ngIf="selectedSection === 'dashboard' && isWorkshopSession">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Capacidad del equipo</p>
                <h2>Técnicos del Tenant</h2>
              </div>
            </div>

            <div class="dashboard-mini-list" *ngIf="recentTechnicians.length; else noRecentTechnicians">
              <article class="dashboard-mini-item" *ngFor="let technician of recentTechnicians">
                <div>
                  <strong>{{ technician.full_name }}</strong>
                  <p>{{ technician.specialty }} · {{ technician.phone }}</p>
                </div>
                <span>{{ statusLabel(technician.status) }}</span>
              </article>
            </div>
            <ng-template #noRecentTechnicians>
              <p class="dashboard-empty">Todavía no hay técnicos registrados en este taller.</p>
            </ng-template>
          </article>

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'dashboard' && showRecentOperationalPanel">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Seguimiento operativo</p>
                <h2>{{ recentPanelTitle }}</h2>
              </div>
            </div>

            <div class="dashboard-list" *ngIf="operationalOverview?.recent_emergencies?.length; else noRecentOperationalEmergencies">
              <article class="dashboard-list-item" *ngFor="let item of operationalOverview?.recent_emergencies">
                <div class="dashboard-list-copy">
                  <span class="dashboard-list-priority">{{ item.code }}</span>
                  <strong>{{ item.client_name }} · {{ item.vehicle_name }}</strong>
                  <p>
                    {{ item.status_label }}
                    <span *ngIf="item.workshop_name && !isWorkshopSession"> · {{ item.workshop_name }}</span>
                  </p>
                </div>
                <span class="dashboard-list-meta">{{ item.created_at | date: 'short' }}</span>
              </article>
            </div>
            <ng-template #noRecentOperationalEmergencies>
              <p class="dashboard-empty">No hay solicitudes recientes para mostrar en el dashboard.</p>
            </ng-template>
          </article>

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'emergencies'">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Gestión de emergencias</p>
                <h2>Solicitudes de Emergencia</h2>
              </div>
              <div class="dashboard-toolbar">
                <button class="dashboard-refresh-button" type="button" (click)="loadEmergencies()">
                  Actualizar
                </button>
                <button class="dashboard-refresh-button" type="button" (click)="clearMaintenanceSearch()">
                  Limpiar filtros
                </button>
              </div>
            </div>

            <p class="dashboard-loading" *ngIf="isEmergenciesLoading">Cargando solicitudes de emergencia...</p>
            <p class="dashboard-empty" *ngIf="!isEmergenciesLoading && emergenciesFeedback">
              {{ emergenciesFeedback }}
            </p>
            <p class="dashboard-empty" *ngIf="!isEmergenciesLoading && !emergenciesFeedback && !maintenanceRequests.length">
              {{ isWorkshopSession ? 'No hay emergencias pendientes asignadas a este taller.' : 'Aún no hay solicitudes de emergencia registradas.' }}
            </p>

            <section class="maintenance-topbar" *ngIf="!isEmergenciesLoading && maintenanceRequests.length">
              <article class="maintenance-summary-card maintenance-summary-card-compact">
                <div class="maintenance-summary-head">
                  <div>
                    <p class="dashboard-panel-kicker">Resumen Taller</p>
                    <h2>Panel rápido</h2>
                  </div>
                  <span class="maintenance-summary-total">{{ maintenanceRequestsFiltered.length }}</span>
                </div>
                <div class="maintenance-summary-list maintenance-summary-list-compact">
                  <div class="maintenance-summary-item" *ngFor="let item of maintenanceSummaryCounts">
                    <strong>{{ item.value }}</strong>
                    <span>{{ item.label }}</span>
                  </div>
                </div>
              </article>

              <div class="maintenance-toolbar maintenance-toolbar-compact">
                <div class="maintenance-toolbar-actions">
                  <button class="dashboard-refresh-button" type="button" (click)="loadEmergencies()">
                    Actualizar
                  </button>
                  <button class="dashboard-secondary-button" type="button" (click)="clearMaintenanceSearch()">
                    Limpiar
                  </button>
                </div>

                <label class="maintenance-search">
                  <span>Buscar por ID, cliente, vehículo o ubicación</span>
                  <input
                    type="search"
                    [(ngModel)]="maintenanceSearch"
                    placeholder="Buscar..."
                  />
                </label>

                <div class="maintenance-filter-buttons">
                  <button
                    type="button"
                    class="dashboard-secondary-button"
                    [class.is-active]="maintenanceFilter === 'todas'"
                    (click)="setMaintenanceFilter('todas')"
                  >
                    Todas
                  </button>
                  <button
                    type="button"
                    class="dashboard-secondary-button"
                    [class.is-active]="maintenanceFilter === 'pendiente'"
                    (click)="setMaintenanceFilter('pendiente')"
                  >
                    Pendiente
                  </button>
                  <button
                    type="button"
                    class="dashboard-secondary-button"
                    [class.is-active]="maintenanceFilter === 'activo'"
                    (click)="setMaintenanceFilter('activo')"
                  >
                    Activa
                  </button>
                  <button
                    type="button"
                    class="dashboard-secondary-button"
                    [class.is-active]="maintenanceFilter === 'rechazado'"
                    (click)="setMaintenanceFilter('rechazado')"
                  >
                    Rechazado
                  </button>
                  <button
                    type="button"
                    class="dashboard-secondary-button"
                    [class.is-active]="maintenanceFilter === 'historial'"
                    (click)="setMaintenanceFilter('historial')"
                  >
                    Historial
                  </button>
                </div>
              </div>
            </section>

            <div class="maintenance-layout" *ngIf="!isEmergenciesLoading && maintenanceRequests.length">
              <div class="maintenance-list-column">
                <div
                  class="maintenance-request-card"
                  *ngFor="let request of maintenanceRequestsFiltered"
                  [class.is-selected]="request.id === selectedMaintenanceRequestId"
                  (click)="selectMaintenanceRequest(request)"
                >
                  <div class="maintenance-request-header">
                    <strong>{{ request.code }}</strong>
                    <span class="maintenance-priority" [attr.data-priority]="request.priority">
                      {{ request.priority }}
                    </span>
                  </div>
                  <div class="maintenance-request-body">
                    <p class="maintenance-request-title">{{ request.client }}</p>
                    <p class="maintenance-request-subtitle">Vehículo: {{ request.vehicle }}</p>
                    <p class="maintenance-request-location">
                      {{ request.location }} · {{ request.distance }}
                    </p>
                    <p class="maintenance-request-detail">{{ request.detail }}</p>
                  </div>

                  <div class="maintenance-request-media" (click)="$event.stopPropagation()">
                    <div class="maintenance-request-map-preview" *ngIf="request.mapEmbedUrl; else requestNoMap">
                      <iframe
                        [src]="request.mapEmbedUrl"
                        loading="lazy"
                        referrerpolicy="no-referrer-when-downgrade"
                        title="Mapa de la emergencia"
                      ></iframe>
                      <a
                        *ngIf="request.mapExternalUrl"
                        [href]="request.mapExternalUrl"
                        target="_blank"
                        rel="noreferrer"
                      >
                        Abrir mapa
                      </a>
                    </div>
                    <ng-template #requestNoMap>
                      <div class="maintenance-request-media-empty">
                        Mapa no disponible: esta solicitud no incluye coordenadas.
                      </div>
                    </ng-template>

                    <div class="maintenance-request-media-grid">
                      <div class="maintenance-request-audio-preview">
                        <strong>Audio</strong>
                        <audio
                          *ngIf="request.audioUrl; else requestNoAudio"
                          controls
                          [src]="request.audioUrl"
                        ></audio>
                        <ng-template #requestNoAudio>
                          <span>Sin audio enviado.</span>
                        </ng-template>
                      </div>

                      <div class="maintenance-request-photo-preview">
                        <strong>Imágenes enviadas por el cliente ({{ request.photoUrls.length }})</strong>
                        <div class="maintenance-request-photo-strip" *ngIf="request.photoUrls.length; else requestNoPhotos">
                          <a
                            *ngFor="let photoUrl of request.photoUrls"
                            [href]="photoUrl"
                            target="_blank"
                            rel="noreferrer"
                          >
                            <img [src]="photoUrl" alt="Foto de la emergencia" loading="lazy" />
                          </a>
                        </div>
                        <ng-template #requestNoPhotos>
                          <span>Sin fotos enviadas.</span>
                        </ng-template>
                      </div>
                    </div>
                  </div>

                  <div class="maintenance-request-footer">
                    <span class="maintenance-request-status" [attr.data-status]="statusFilterGroup(request.status)">
                      {{ emergencyStatusLabel(request.status) }}
                    </span>
                    <span>{{ request.reportedAt }}</span>
                  </div>
                </div>
              </div>
            </div>
          </article>

          <article
            class="dashboard-panel dashboard-panel-wide reports-print-area"
            *ngIf="selectedSection === 'reports'"
          >
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Reportes</p>
                <h2>Trabajos realizados</h2>
              </div>
              <div class="dashboard-toolbar">
                <button class="dashboard-refresh-button" type="button" (click)="loadEmergencies()">
                  Actualizar
                </button>
                <button class="dashboard-refresh-button" type="button" (click)="exportReportsPdf()">
                  Exportar PDF
                </button>
              </div>
            </div>

            <section class="report-summary-grid">
              <article class="report-summary-item">
                <span>Empresa / Taller</span>
                <strong>{{ reportWorkshopName }}</strong>
              </article>
              <article class="report-summary-item">
                <span>Trabajos</span>
                <strong>{{ reportWorkRequests.length }}</strong>
              </article>
              <article class="report-summary-item">
                <span>Servicio</span>
                <strong>{{ formatReportPrice(reportTotalServiceAmount) }}</strong>
              </article>
              <article class="report-summary-item">
                <span>Monto</span>
                <strong>{{ formatReportPrice(reportTotalNetAmount) }}</strong>
              </article>
              <article class="report-summary-item">
                <span>Generado</span>
                <strong>{{ reportGeneratedAt | date: 'short' }}</strong>
              </article>
            </section>

            <p class="dashboard-loading" *ngIf="isEmergenciesLoading">Cargando trabajos realizados...</p>
            <p class="dashboard-empty" *ngIf="!isEmergenciesLoading && !reportWorkRequests.length">
              No hay trabajos realizados para este taller.
            </p>

            <div class="dashboard-table-wrap report-table-wrap" *ngIf="!isEmergenciesLoading && reportWorkRequests.length">
              <table class="dashboard-table report-table">
                <thead>
                  <tr>
                    <th>Código</th>
                    <th>Fecha</th>
                    <th>Cliente</th>
                    <th>Vehículo</th>
                    <th>Problema</th>
                    <th>Técnico</th>
                    <th>Estado</th>
                    <th>Servicio</th>
                    <th>Monto</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let request of reportWorkRequests">
                    <td data-label="Código">
                      <span class="dashboard-id-chip">{{ request.code }}</span>
                    </td>
                    <td data-label="Fecha">{{ request.createdAt | date: 'short' }}</td>
                    <td data-label="Cliente">{{ request.client }}</td>
                    <td data-label="Vehículo">{{ request.vehicle }}</td>
                    <td data-label="Problema">
                      {{ request.standardizedProblemType || request.problemType }}
                    </td>
                    <td data-label="Técnico">
                      {{ request.assignedTechnicianName || 'Sin técnico asignado' }}
                    </td>
                    <td data-label="Estado">
                      <span class="maintenance-request-status" [attr.data-status]="statusFilterGroup(request.status)">
                        {{ emergencyStatusLabel(request.status) }}
                      </span>
                    </td>
                    <td data-label="Servicio">{{ formatReportPrice(calculateReportServiceAmount(request.price)) }}</td>
                    <td data-label="Monto">{{ formatReportPrice(calculateReportNetAmount(request.price)) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'audit'">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Bitacora</p>
                <h2>Actividad reciente</h2>
              </div>
              <div class="dashboard-toolbar">
                <button class="dashboard-refresh-button" type="button" (click)="refreshAudit()">
                  Actualizar
                </button>
              </div>
            </div>

            <section class="audit-summary-grid">
              <article class="audit-summary-item">
                <span>Eventos</span>
                <strong>{{ auditItems.length }}</strong>
              </article>
              <article class="audit-summary-item">
                <span>Emergencias</span>
                <strong>{{ maintenanceRequests.length }}</strong>
              </article>
              <article class="audit-summary-item">
                <span>Técnicos</span>
                <strong>{{ technicians.length }}</strong>
              </article>
              <article class="audit-summary-item">
                <span>Último evento</span>
                <strong>{{ auditLatestLabel }}</strong>
              </article>
            </section>

            <p class="dashboard-loading" *ngIf="isEmergenciesLoading || isTechniciansLoading || isLoading || isClientsLoading">
              Cargando actividad...
            </p>
            <p class="dashboard-empty" *ngIf="!isAuditLoading && !auditItems.length">
              Todavía no hay movimientos registrados para mostrar.
            </p>

            <div class="audit-timeline" *ngIf="!isAuditLoading && auditItems.length">
              <article class="audit-item" *ngFor="let item of auditItems" [attr.data-tone]="item.tone">
                <span class="audit-dot"></span>
                <div class="audit-card">
                  <div class="audit-card-head">
                    <strong>{{ item.title }}</strong>
                    <span>{{ item.createdAt | date: 'short' }}</span>
                  </div>
                  <p>{{ item.detail }}</p>
                  <small>{{ item.meta }}</small>
                </div>
              </article>
            </div>
          </article>

          <!-- ===== SECCIÓN SINCRONIZACIÓN OFFLINE ===== -->
          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'sync'">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Solicitudes &rsaquo; Sincronización</p>
                <h2>Gestión de sincronización</h2>
              </div>
              <div class="dashboard-toolbar">
                <span class="dashboard-toolbar-note">PLATAFORMA WEB – TALLER / ADMINISTRADOR</span>
                <button class="dashboard-refresh-button" type="button" (click)="loadEmergencies()">
                  Actualizar
                </button>
              </div>
            </div>

            <!-- 4 tarjetas de resumen -->
            <div class="sync-stat-grid">
              <article class="sync-stat-item" data-tone="gold">
                <span class="sync-stat-icon">⏳</span>
                <strong>{{ syncStats.pending }}</strong>
                <span>Pendientes</span>
              </article>
              <article class="sync-stat-item" data-tone="teal">
                <span class="sync-stat-icon">✅</span>
                <strong>{{ syncStats.syncedToday }}</strong>
                <span>Sincronizados hoy</span>
              </article>
              <article class="sync-stat-item" data-tone="red">
                <span class="sync-stat-icon">⚠</span>
                <strong>{{ syncStats.withErrors }}</strong>
                <span>Con errores</span>
              </article>
              <article class="sync-stat-item" data-tone="blue">
                <span class="sync-stat-icon">◫</span>
                <strong>{{ syncStats.total }}</strong>
                <span>Total procesados</span>
              </article>
            </div>

            <p class="dashboard-loading" *ngIf="isEmergenciesLoading">
              Cargando datos de sincronización...
            </p>

            <!-- Pestañas de navegación -->
            <div class="sync-tabs" *ngIf="!isEmergenciesLoading">
              <button
                class="sync-tab-btn"
                type="button"
                [class.is-active]="syncTab === 'queue'"
                (click)="selectSyncTab('queue')"
              >
                Cola de sincronización
                <span class="sync-tab-badge" *ngIf="syncStats.pending > 0">
                  {{ syncStats.pending }}
                </span>
              </button>
              <button
                class="sync-tab-btn"
                type="button"
                [class.is-active]="syncTab === 'errors'"
                (click)="selectSyncTab('errors')"
              >
                Con errores
                <span class="sync-tab-badge sync-tab-badge-error" *ngIf="syncStats.withErrors > 0">
                  {{ syncStats.withErrors }}
                </span>
              </button>
              <button
                class="sync-tab-btn"
                type="button"
                [class.is-active]="syncTab === 'history'"
                (click)="selectSyncTab('history')"
              >
                Historial
              </button>
            </div>

            <!-- ── TAB: Cola de sincronización ── -->
            <div *ngIf="!isEmergenciesLoading && syncTab === 'queue'">
              <div class="sync-note-box sync-note-box-info">
                <span class="sync-note-icon">ℹ</span>
                <div>
                  <strong>Visibilidad limitada en la plataforma web</strong>
                  <p>
                    Los pendientes y errores previos al envío permanecen en el dispositivo hasta que se sincronicen.
                    Esta vista solo muestra incidentes que ya llegaron al servidor con estado pendiente de atención.
                  </p>
                </div>
              </div>

              <p class="dashboard-empty" *ngIf="!syncQueueRequests.length">
                No hay incidentes offline pendientes de atención en el servidor.
              </p>

              <div class="dashboard-table-wrap" *ngIf="syncQueueRequests.length">
                <table class="dashboard-table">
                  <thead>
                    <tr>
                      <th>ID Local</th>
                      <th>ID Servidor</th>
                      <th>Tipo de incidente</th>
                      <th>Cliente</th>
                      <th>Fecha registro</th>
                      <th>Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr *ngFor="let req of syncQueueRequests">
                      <td data-label="ID Local">
                        <span class="dashboard-id-chip sync-local-id-chip" [title]="req.localId ?? ''">
                          {{ (req.localId ?? '') | slice:0:8 }}&hellip;
                        </span>
                      </td>
                      <td data-label="ID Servidor">
                        <span class="dashboard-id-chip">{{ req.code }}</span>
                      </td>
                      <td data-label="Tipo">{{ req.problemType }}</td>
                      <td data-label="Cliente">{{ req.client }}</td>
                      <td data-label="Fecha">{{ req.createdAt | date:'dd/MM/yy HH:mm' }}</td>
                      <td data-label="Estado">
                        <span class="maintenance-request-status"
                          [attr.data-status]="statusFilterGroup(req.status)">
                          {{ emergencyStatusLabel(req.status) }}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- ── TAB: Con errores ── -->
            <div *ngIf="!isEmergenciesLoading && syncTab === 'errors'">

              <div class="sync-note-box sync-note-box-info" *ngIf="!syncErrorRequests.length">
                <span class="sync-note-icon">ℹ</span>
                <div>
                  <strong>Sin errores registrados en el servidor</strong>
                  <p>
                    Los errores de sincronización detallados se gestionan localmente desde el dispositivo móvil.
                    Esta vista muestra incidentes que llegaron al servidor pero fueron rechazados o cancelados.
                  </p>
                </div>
              </div>

              <div class="sync-layout" *ngIf="syncErrorRequests.length">
                <!-- Tabla de errores -->
                <div class="sync-table-col">
                  <p class="sync-section-label">Errores de sincronización</p>

                  <div class="sync-note-box sync-note-box-warning" style="margin-bottom:0.85rem">
                    <span class="sync-note-icon">ℹ</span>
                    <p>
                      Los errores de sincronización detallados se gestionan localmente desde el dispositivo móvil.
                      Los pendientes y errores previos al envío permanecen en el dispositivo hasta que se sincronicen.
                    </p>
                  </div>

                  <div class="dashboard-table-wrap">
                    <table class="dashboard-table">
                      <thead>
                        <tr>
                          <th>ID Local</th>
                          <th>Tipo de incidente</th>
                          <th>Cliente</th>
                          <th>Fecha registro</th>
                          <th>Error</th>
                          <th>Intentos</th>
                          <th>Último intento</th>
                          <th>Acciones</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr
                          *ngFor="let req of syncErrorRequests"
                          [class.is-sync-selected]="(selectedSyncErrorRecordId ?? syncErrorRequests[0]?.id) === req.id"
                        >
                          <td data-label="ID Local">
                            <span class="dashboard-id-chip sync-local-id-chip" [title]="req.localId ?? ''">
                              {{ (req.localId ?? '') | slice:0:8 }}&hellip;
                            </span>
                          </td>
                          <td data-label="Tipo">{{ req.problemType }}</td>
                          <td data-label="Cliente">{{ req.client }}</td>
                          <td data-label="Fecha registro">{{ req.createdAt | date:'dd/MM/yy HH:mm' }}</td>
                          <td data-label="Error">
                            <span class="sync-error-reason">
                              {{ req.rejectionReason || syncErrorLabel(req.status) }}
                            </span>
                          </td>
                          <td data-label="Intentos">
                            <span class="sync-dash">—</span>
                          </td>
                          <td data-label="Último intento">
                            {{ (req.rejectedAt ?? req.createdAt) | date:'dd/MM/yy HH:mm' }}
                          </td>
                          <td data-label="Acciones">
                            <button
                              class="sync-detail-btn"
                              type="button"
                              (click)="selectSyncErrorRecord(req.id)"
                            >
                              Ver detalle
                            </button>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <!-- Panel detalle del error -->
                <aside class="sync-detail-panel" *ngIf="selectedSyncErrorRecord">
                  <p class="sync-section-label">Detalle del error seleccionado</p>

                  <dl class="sync-detail-list">
                    <dt>ID Local</dt>
                    <dd class="sync-id-mono">{{ selectedSyncErrorRecord.localId || '—' }}</dd>

                    <dt>Tipo</dt>
                    <dd>{{ selectedSyncErrorRecord.problemType }}</dd>

                    <dt>Cliente</dt>
                    <dd>{{ selectedSyncErrorRecord.client }}</dd>

                    <dt>Fecha</dt>
                    <dd>{{ selectedSyncErrorRecord.createdAt | date:'medium' }}</dd>

                    <dt>Estado</dt>
                    <dd>
                      <span
                        class="maintenance-request-status"
                        [attr.data-status]="statusFilterGroup(selectedSyncErrorRecord.status)"
                      >
                        {{ emergencyStatusLabel(selectedSyncErrorRecord.status) }}
                      </span>
                    </dd>

                    <dt>Mensaje</dt>
                    <dd>
                      {{ selectedSyncErrorRecord.rejectionReason || syncErrorLabel(selectedSyncErrorRecord.status) }}
                    </dd>

                    <dt>Acción</dt>
                    <dd class="sync-action-text">
                      {{ syncActionRecommendation(selectedSyncErrorRecord.status) }}
                    </dd>
                  </dl>

                  <div class="sync-result-msg sync-result-ok">
                    <span>✅</span>
                    <p>El incidente ya fue recibido por el servidor.</p>
                  </div>

                  <div class="sync-result-msg sync-result-error" style="margin-top:0.5rem">
                    <span>⚠</span>
                    <div>
                      <strong>Estado final con error</strong>
                      <p>
                        El incidente fue sincronizado, pero terminó en estado cancelado/rechazado.
                      </p>
                    </div>
                  </div>
                </aside>
              </div>
            </div>

            <!-- ── TAB: Historial ── -->
            <div *ngIf="!isEmergenciesLoading && syncTab === 'history'">
              <p class="dashboard-empty" *ngIf="!syncedRequests.length">
                No se encontraron incidentes registrados offline desde dispositivos móviles.
              </p>

              <div class="sync-layout" *ngIf="syncedRequests.length">
                <div class="sync-table-col">
                  <p class="sync-section-label">Historial completo de sincronización</p>
                  <div class="dashboard-table-wrap">
                    <table class="dashboard-table">
                      <thead>
                        <tr>
                          <th>ID Local</th>
                          <th>ID Servidor</th>
                          <th>Tipo de incidente</th>
                          <th>Fecha registro</th>
                          <th>Estado</th>
                          <th>Fecha sincronización</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr
                          *ngFor="let req of syncedRequests"
                          class="sync-table-row"
                          [class.is-sync-selected]="(selectedSyncRecordId ?? syncedRequests[0]?.id) === req.id"
                          (click)="selectSyncRecord(req.id)"
                        >
                          <td data-label="ID Local">
                            <span class="dashboard-id-chip sync-local-id-chip" [title]="req.localId ?? ''">
                              {{ (req.localId ?? '') | slice:0:8 }}&hellip;
                            </span>
                          </td>
                          <td data-label="ID Servidor">
                            <span class="dashboard-id-chip">{{ req.code }}</span>
                          </td>
                          <td data-label="Tipo">{{ req.problemType }}</td>
                          <td data-label="Fecha registro">{{ req.createdAt | date:'dd/MM/yy HH:mm' }}</td>
                          <td data-label="Estado">
                            <span class="maintenance-request-status"
                              [attr.data-status]="statusFilterGroup(req.status)">
                              {{ emergencyStatusLabel(req.status) }}
                            </span>
                          </td>
                          <td data-label="Fecha sync">{{ req.createdAt | date:'dd/MM/yy HH:mm' }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <aside class="sync-detail-panel" *ngIf="selectedSyncRecord">
                  <p class="sync-section-label">Detalle de sincronización</p>

                  <dl class="sync-detail-list">
                    <dt>ID Local</dt>
                    <dd class="sync-id-mono">{{ selectedSyncRecord.localId }}</dd>

                    <dt>Tipo</dt>
                    <dd>{{ selectedSyncRecord.problemType }}</dd>

                    <dt>Fecha</dt>
                    <dd>{{ selectedSyncRecord.createdAt | date:'medium' }}</dd>

                    <dt>Estado</dt>
                    <dd>
                      <span
                        class="maintenance-request-status"
                        [attr.data-status]="statusFilterGroup(selectedSyncRecord.status)"
                      >
                        {{ emergencyStatusLabel(selectedSyncRecord.status) }}
                      </span>
                    </dd>

                    <dt>Mensaje</dt>
                    <dd>{{ selectedSyncRecord.clientDescription || 'Sin descripción registrada.' }}</dd>

                    <dt>Reintentos</dt>
                    <dd>—</dd>
                  </dl>

                  <div
                    class="sync-result-msg sync-result-ok"
                    *ngIf="selectedSyncRecord.status !== 'rechazado' && selectedSyncRecord.status !== 'solicitud_cancelada'"
                  >
                    <span>✅</span>
                    <p>El incidente fue sincronizado correctamente.</p>
                  </div>

                  <div
                    class="sync-result-msg sync-result-error"
                    *ngIf="selectedSyncRecord.status === 'rechazado' || selectedSyncRecord.status === 'solicitud_cancelada'"
                  >
                    <span>⚠</span>
                    <div>
                      <strong>Estado con error</strong>
                      <p>
                        El incidente fue sincronizado, pero terminó en estado cancelado/rechazado.
                      </p>
                    </div>
                  </div>
                </aside>
              </div>
            </div>

          </article>
          <!-- ===== FIN SECCIÓN SINCRONIZACIÓN ===== -->

          <!-- ===== SECCIÓN COTIZACIONES — SOLICITUDES RECIBIDAS ===== -->
          <article class="dashboard-panel dashboard-panel-wide cot-panel" *ngIf="selectedSection === 'quotation_requests'">

            <!-- ── VISTA: lista ─────────────────────────────────────────────── -->
            <ng-container *ngIf="quotationView === 'list'">
              <div class="dashboard-panel-head">
                <div>
                  <p class="dashboard-panel-kicker">Solicitudes de cotización</p>
                  <h2>{{ isTenantQuotationSession ? 'Cotizaciones del tenant' : 'Solicitudes recibidas' }}</h2>
                </div>
                <div class="dashboard-toolbar">
                  <span class="dashboard-toolbar-note">{{ quotationRequests.length }} solicitudes</span>
                  <button class="dashboard-refresh-button" type="button" (click)="loadQuotationRequests()">Actualizar</button>
                </div>
              </div>

              <div *ngIf="isQuotationRequestsLoading" class="dashboard-loading-state">Cargando solicitudes...</div>

              <div *ngIf="!isQuotationRequestsLoading && quotationRequests.length === 0" class="dashboard-empty-state">
                {{ isTenantQuotationSession ? 'No hay solicitudes de cotización registradas.' : 'No hay solicitudes de cotización recibidas.' }}
              </div>

              <table *ngIf="!isQuotationRequestsLoading && quotationRequests.length > 0" class="dashboard-table cot-table-clickable">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Emergencia</th>
                    <th *ngIf="isTenantQuotationSession">Cliente</th>
                    <th *ngIf="isTenantQuotationSession">Sucursal / taller</th>
                    <th>Estado</th>
                    <th>Propuestas</th>
                    <th *ngIf="!isTenantQuotationSession">Invitación</th>
                    <th *ngIf="isTenantQuotationSession">Propuesta aceptada</th>
                    <th>Recibido</th>
                    <th>Fecha</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let req of quotationRequests" (click)="openQuotationDetail(req)" class="cot-row-clickable">
                    <td><strong>#{{ req.id }}</strong></td>
                    <td>{{ req.emergency_id ?? '—' }}</td>
                    <td *ngIf="isTenantQuotationSession">{{ req.client_name || 'Cliente no identificado' }}</td>
                    <td *ngIf="isTenantQuotationSession">{{ req.workshop_names || 'Sin taller asociado' }}</td>
                    <td>
                      <span class="dashboard-badge"
                        [class.dashboard-badge-green]="req.status === 'seleccionado'"
                        [class.dashboard-badge-yellow]="req.status === 'abierto' || req.status === 'con_propuestas' || req.status === 'en_evaluacion'"
                        [class.dashboard-badge-red]="req.status === 'cancelado' || req.status === 'expirado'">
                        {{ quotationRequestStateLabel(req) }}
                      </span>
                    </td>
                    <td>{{ req.received_offers_count }} / {{ req.requested_workshops_count }}</td>
                    <td *ngIf="!isTenantQuotationSession">
                      <span class="dashboard-badge"
                        [class.dashboard-badge-yellow]="req.workshop_invitation_status === 'notificado'"
                        [class.dashboard-badge-green]="req.workshop_invitation_status === 'respondido'">
                        {{ quotationInvitationStateLabel(req) }}
                      </span>
                    </td>
                    <td *ngIf="isTenantQuotationSession">
                      <span *ngIf="req.selected_workshop_name; else noAcceptedOffer">
                        {{ req.selected_workshop_name }}
                        <ng-container *ngIf="req.selected_offer_price != null"> · Bs. {{ req.selected_offer_price }}</ng-container>
                      </span>
                      <ng-template #noAcceptedOffer>—</ng-template>
                    </td>
                    <td>{{ req.requested_at | date: 'dd/MM/yy HH:mm' }}</td>
                    <td>{{ req.created_at | date: 'dd/MM/yy HH:mm' }}</td>
                    <td><button class="cot-btn-ver" type="button" (click)="$event.stopPropagation(); openQuotationDetail(req)">Ver detalle →</button></td>
                  </tr>
                </tbody>
              </table>
            </ng-container>

            <!-- ── VISTA: detalle ───────────────────────────────────────────── -->
            <ng-container *ngIf="quotationView === 'detail' && selectedQuotationRequest">
              <div class="dashboard-panel-head">
                <div class="cot-head-with-back">
                  <button class="cot-back-btn" type="button" (click)="resetQuotationView()">← Solicitudes</button>
                  <div>
                    <p class="dashboard-panel-kicker">Solicitud #{{ selectedQuotationRequest.id }}</p>
                    <h2>Detalle de solicitud</h2>
                  </div>
                </div>
                <div class="dashboard-toolbar">
                  <button
                    *ngIf="!isTenantQuotationSession"
                    class="cot-btn-primary"
                    type="button"
                    [disabled]="selectedQuotationRequest.status === 'seleccionado' || selectedQuotationRequest.status === 'cancelado' || selectedQuotationRequest.status === 'expirado' || selectedWorkshopOffer?.status === 'aceptada' || selectedWorkshopOffer?.status === 'rechazada' || selectedWorkshopOffer?.status === 'expirado'"
                    (click)="openQuotationOfferForm()"
                  >
                    {{ selectedWorkshopOffer ? 'Editar cotización' : '+ Registrar cotización' }}
                  </button>
                </div>
              </div>

              <!-- Estado de la solicitud -->
              <div class="cot-detail-status-bar">
                <span class="dashboard-badge dashboard-badge-lg"
                  [class.dashboard-badge-green]="selectedQuotationRequest.status === 'seleccionado'"
                  [class.dashboard-badge-yellow]="selectedQuotationRequest.status === 'abierto' || selectedQuotationRequest.status === 'con_propuestas' || selectedQuotationRequest.status === 'en_evaluacion'"
                  [class.dashboard-badge-red]="selectedQuotationRequest.status === 'cancelado' || selectedQuotationRequest.status === 'expirado'">
                  {{ quotationRequestStateLabel(selectedQuotationRequest) }}
                </span>
                <span class="cot-status-meta">
                  {{ selectedQuotationRequest.received_offers_count }} propuesta(s) recibida(s) de {{ selectedQuotationRequest.requested_workshops_count }} taller(es) notificado(s)
                </span>
                <span class="cot-status-meta" *ngIf="selectedQuotationRequest.expires_at">
                  Vence: {{ selectedQuotationRequest.expires_at | date: 'dd/MM/yyyy HH:mm' }}
                </span>
                <span class="cot-status-meta" *ngIf="isTenantQuotationSession && selectedQuotationRequest.client_name">
                  Cliente: {{ selectedQuotationRequest.client_name }}
                </span>
              </div>

              <!-- Cargando emergencia -->
              <div *ngIf="isQuotationEmergencyLoading" class="dashboard-loading-state">Cargando información de la emergencia...</div>

              <!-- Detalle de emergencia -->
              <div *ngIf="!isQuotationEmergencyLoading && selectedQuotationEmergency" class="cot-detail-grid">

                <!-- Columna izquierda: info del cliente/vehículo/problema -->
                <div class="cot-detail-col">
                  <div class="cot-info-card">
                    <h3 class="cot-info-card-title">Cliente y estado</h3>
                    <p class="cot-info-line">
                      <span class="cot-info-label">Cliente:</span>
                      <span>{{ selectedQuotationEmergency.client_name || 'Cliente no identificado' }}</span>
                    </p>
                    <p class="cot-info-line">
                      <span class="cot-info-label">Estado:</span>
                      <span>{{ selectedQuotationEmergency.emergency_status || '—' }}</span>
                    </p>
                    <p class="cot-info-line">
                      <span class="cot-info-label">Creada:</span>
                      <span>{{ selectedQuotationEmergency.created_at | date: 'dd/MM/yyyy HH:mm' }}</span>
                    </p>
                    <p class="cot-info-line" *ngIf="selectedQuotationEmergency.nearest_workshop_name">
                      <span class="cot-info-label">Taller asignado:</span>
                      <span>{{ selectedQuotationEmergency.nearest_workshop_name }}</span>
                    </p>
                    <p class="cot-info-line" *ngIf="selectedQuotationEmergency.assigned_technician_name">
                      <span class="cot-info-label">Técnico:</span>
                      <span>{{ selectedQuotationEmergency.assigned_technician_name }}</span>
                    </p>
                  </div>

                  <div class="cot-info-card">
                    <h3 class="cot-info-card-title">Vehículo</h3>
                    <p class="cot-info-line">
                      <span class="cot-info-label">Modelo:</span>
                      <span>{{ selectedQuotationEmergency.vehicle_name || '—' }}</span>
                    </p>
                    <p class="cot-info-line">
                      <span class="cot-info-label">Placa:</span>
                      <span>{{ selectedQuotationEmergency.vehicle_plate || '—' }}</span>
                    </p>
                  </div>

                  <div class="cot-info-card">
                    <h3 class="cot-info-card-title">Problema reportado</h3>
                    <p class="cot-info-line">
                      <span class="cot-info-label">Tipo:</span>
                      <span>{{ selectedQuotationEmergency.problem_type_standardized || selectedQuotationEmergency.problem_type || '—' }}</span>
                    </p>
                    <p class="cot-info-line" *ngIf="selectedQuotationEmergency.description">
                      <span class="cot-info-label">Descripción:</span>
                      <span>{{ selectedQuotationEmergency.description }}</span>
                    </p>
                  </div>

                  <div class="cot-info-card">
                    <h3 class="cot-info-card-title">Diagnóstico preliminar e IA</h3>
                    <p class="cot-info-line">
                      <span class="cot-info-label">Diagnóstico principal:</span>
                      <span>{{ selectedQuotationEmergency.problem_type_standardized || selectedQuotationEmergency.problem_type || '—' }}</span>
                    </p>
                    <p class="cot-info-line" *ngIf="selectedQuotationEmergency.photo_problem_type_standardized">
                      <span class="cot-info-label">Clasificación por foto:</span>
                      <span>{{ selectedQuotationEmergency.photo_problem_type_standardized }}</span>
                    </p>
                    <p class="cot-info-line" *ngIf="selectedQuotationEmergency.photo_classification_confidence != null">
                      <span class="cot-info-label">Confianza IA:</span>
                      <span>{{ (selectedQuotationEmergency.photo_classification_confidence * 100) | number: '1.0-0' }}%</span>
                    </p>
                    <p class="cot-info-line" *ngIf="selectedQuotationEmergency.audio_transcript">
                      <span class="cot-info-label">Transcripción:</span>
                      <span>{{ selectedQuotationEmergency.audio_transcript }}</span>
                    </p>
                    <p class="cot-info-line" *ngIf="selectedQuotationEmergency.audio_transcript_status">
                      <span class="cot-info-label">Estado transcripción:</span>
                      <span>{{ selectedQuotationEmergency.audio_transcript_status }}</span>
                    </p>
                    <p class="cot-info-line" *ngIf="selectedQuotationEmergency.photo_classification_error">
                      <span class="cot-info-label">Observación IA foto:</span>
                      <span>{{ selectedQuotationEmergency.photo_classification_error }}</span>
                    </p>
                    <p class="cot-info-line" *ngIf="selectedQuotationEmergency.audio_transcript_error">
                      <span class="cot-info-label">Observación IA audio:</span>
                      <span>{{ selectedQuotationEmergency.audio_transcript_error }}</span>
                    </p>
                  </div>

                  <div class="cot-info-card">
                    <h3 class="cot-info-card-title">Ubicación</h3>
                    <ng-container *ngIf="quotationEmergencyMapEmbedUrl; else cotNoMap">
                      <div class="cot-map-wrapper">
                        <iframe
                          [src]="quotationEmergencyMapEmbedUrl"
                          loading="lazy"
                          referrerpolicy="no-referrer-when-downgrade"
                          title="Ubicación de la emergencia"
                        ></iframe>
                      </div>
                      <a *ngIf="quotationEmergencyMapExternalUrl" [href]="quotationEmergencyMapExternalUrl" target="_blank" rel="noreferrer" class="cot-map-link">
                        Abrir en mapa externo
                      </a>
                    </ng-container>
                    <ng-template #cotNoMap>
                      <p class="cot-empty-note">Sin coordenadas registradas.</p>
                    </ng-template>
                  </div>
                </div>

                <!-- Columna derecha: evidencias -->
                <div class="cot-detail-col">
                  <div class="cot-info-card">
                    <h3 class="cot-info-card-title">Evidencias</h3>

                    <div class="cot-evidence-block">
                      <p class="cot-evidence-label">Audio</p>
                      <audio *ngIf="quotationEmergencyAudioUrl; else cotNoAudio" controls [src]="quotationEmergencyAudioUrl" class="cot-audio"></audio>
                      <ng-template #cotNoAudio><p class="cot-empty-note">Sin audio enviado.</p></ng-template>
                    </div>

                    <div class="cot-evidence-block">
                      <p class="cot-evidence-label">Fotos ({{ quotationEmergencyPhotoUrls.length }})</p>
                      <div *ngIf="quotationEmergencyPhotoUrls.length; else cotNoPhotos" class="cot-photo-strip">
                        <a
                          *ngFor="let photoUrl of quotationEmergencyPhotoUrls"
                          [href]="photoUrl"
                          target="_blank"
                          rel="noreferrer"
                          class="cot-photo-thumb"
                        >
                          <img [src]="photoUrl" alt="Evidencia fotográfica" loading="lazy" />
                        </a>
                      </div>
                      <ng-template #cotNoPhotos><p class="cot-empty-note">Sin fotos enviadas.</p></ng-template>
                    </div>
                  </div>

                  <div class="cot-info-card" *ngIf="selectedWorkshopOffer">
                    <h3 class="cot-info-card-title">Mi cotización</h3>
                    <p class="cot-info-line">
                      <span class="cot-info-label">Estado:</span>
                      <span>{{ quotationOfferStateLabel(selectedWorkshopOffer) }}</span>
                    </p>
                    <p class="cot-info-line" *ngIf="selectedWorkshopOffer.price != null">
                      <span class="cot-info-label">Precio:</span>
                      <span>Bs. {{ selectedWorkshopOffer.price }}</span>
                    </p>
                    <p class="cot-info-line" *ngIf="selectedWorkshopOffer.expires_at">
                      <span class="cot-info-label">Vence:</span>
                      <span>{{ selectedWorkshopOffer.expires_at | date: 'dd/MM/yyyy HH:mm' }}</span>
                    </p>
                  </div>

                  <div class="cot-info-card" *ngIf="isTenantQuotationSession">
                    <h3 class="cot-info-card-title">Propuestas del tenant</h3>
                    <div *ngIf="selectedQuotationOffers.length === 0" class="cot-empty-note">
                      No hay propuestas registradas para esta solicitud.
                    </div>
                    <div *ngIf="selectedQuotationOffers.length > 0" class="cot-history-list">
                      <div class="cot-history-card" *ngFor="let offer of selectedQuotationOffers">
                        <div class="cot-history-card-head">
                          <div class="cot-history-card-meta">
                            <strong class="cot-history-id">{{ offer.workshop_name || ('Taller #' + offer.workshop_id) }}</strong>
                            <span class="cot-history-sub">Cotización #{{ offer.id }}</span>
                          </div>
                          <div class="cot-history-badges">
                            <span class="dashboard-badge"
                              [class.dashboard-badge-green]="offer.status === 'aceptada' || offer.status === 'seleccionado'"
                              [class.dashboard-badge-yellow]="offer.status === 'enviada'"
                              [class.dashboard-badge-blue]="offer.status === 'actualizada'"
                              [class.dashboard-badge-red]="offer.status === 'rechazado' || offer.status === 'expirado'">
                              {{ quotationOfferStateLabel(offer) }}
                            </span>
                          </div>
                        </div>
                        <div class="cot-history-card-body">
                          <div class="cot-history-row">
                            <span class="cot-history-label">Precio</span>
                            <span class="cot-history-value cot-price-highlight">{{ offer.price != null ? 'Bs. ' + offer.price : '—' }}</span>
                          </div>
                          <div class="cot-history-row" *ngIf="offer.service_description">
                            <span class="cot-history-label">Servicio</span>
                            <span class="cot-history-value">{{ offer.service_description }}</span>
                          </div>
                          <div class="cot-history-row" *ngIf="offer.estimated_arrival_time">
                            <span class="cot-history-label">ETA llegada</span>
                            <span class="cot-history-value">{{ offer.estimated_arrival_time }}</span>
                          </div>
                          <div class="cot-history-row" *ngIf="offer.estimated_service_time">
                            <span class="cot-history-label">Tiempo reparación</span>
                            <span class="cot-history-value">{{ offer.estimated_service_time }}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Sin emergencia asociada -->
              <div *ngIf="!isQuotationEmergencyLoading && !selectedQuotationEmergency && selectedQuotationRequest.emergency_id" class="dashboard-empty-state">
                No se pudo cargar la información de la emergencia.
              </div>

              <div *ngIf="!selectedQuotationRequest.emergency_id" class="dashboard-empty-state">
                Esta solicitud no tiene emergencia asociada.
              </div>
            </ng-container>

            <!-- ── VISTA: formulario de cotización ─────────────────────────── -->
            <ng-container *ngIf="quotationView === 'offer_form' && selectedQuotationRequest">
              <div class="dashboard-panel-head">
                <div class="cot-head-with-back">
                  <button class="cot-back-btn" type="button" (click)="quotationView = 'detail'">← Detalle</button>
                  <div>
                    <p class="dashboard-panel-kicker">Solicitud #{{ selectedQuotationRequest.id }}</p>
                    <h2>{{ selectedWorkshopOffer ? 'Actualizar cotización' : 'Registrar cotización' }}</h2>
                  </div>
                </div>
              </div>

              <form class="cot-form" (ngSubmit)="submitQuotationOffer()" #cotForm="ngForm">
                <div class="cot-form-grid">

                  <div class="cot-form-field cot-field-full">
                    <label class="cot-form-label" for="cot-price">Precio (Bs.) <span class="cot-required">*</span></label>
                    <input
                      id="cot-price"
                      class="cot-form-input"
                      type="number"
                      min="0"
                      step="0.01"
                      placeholder="Ej. 350.00"
                      [(ngModel)]="quotationOfferForm.price"
                      name="cot_price"
                      required
                    />
                  </div>

                  <div class="cot-form-field cot-field-full">
                    <label class="cot-form-label" for="cot-desc">Descripción del servicio <span class="cot-required">*</span></label>
                    <textarea
                      id="cot-desc"
                      class="cot-form-textarea"
                      rows="4"
                      placeholder="Describe el trabajo a realizar, repuestos incluidos, procedimiento, etc."
                      [(ngModel)]="quotationOfferForm.service_description"
                      name="cot_desc"
                      required
                      minlength="3"
                    ></textarea>
                  </div>

                  <div class="cot-form-field cot-field-full">
                    <label class="cot-form-label" for="cot-spare-parts">Repuestos necesarios</label>
                    <textarea
                      id="cot-spare-parts"
                      class="cot-form-textarea"
                      rows="3"
                      placeholder="Ej. Batería 12V 75Ah, borne positivo, fusible principal..."
                      [(ngModel)]="quotationOfferForm.spare_parts"
                      name="cot_spare_parts"
                    ></textarea>
                  </div>

                  <div class="cot-form-field cot-field-full">
                    <label class="cot-form-label" for="cot-labor-detail">Detalle de mano de obra</label>
                    <textarea
                      id="cot-labor-detail"
                      class="cot-form-textarea"
                      rows="3"
                      placeholder="Ej. Diagnóstico eléctrico, desmontaje, instalación y prueba de carga."
                      [(ngModel)]="quotationOfferForm.labor_detail"
                      name="cot_labor_detail"
                    ></textarea>
                  </div>

                  <div class="cot-form-field">
                    <label class="cot-form-label" for="cot-labor-cost">Costo mano de obra (Bs.)</label>
                    <input
                      id="cot-labor-cost"
                      class="cot-form-input"
                      type="number"
                      min="0"
                      step="0.01"
                      placeholder="80.00"
                      [(ngModel)]="quotationOfferForm.labor_cost"
                      name="cot_labor_cost"
                    />
                  </div>

                  <div class="cot-form-field">
                    <label class="cot-form-label" for="cot-parts-cost">Costo repuestos (Bs.)</label>
                    <input
                      id="cot-parts-cost"
                      class="cot-form-input"
                      type="number"
                      min="0"
                      step="0.01"
                      placeholder="450.00"
                      [(ngModel)]="quotationOfferForm.spare_parts_cost"
                      name="cot_spare_parts_cost"
                    />
                  </div>

                  <div class="cot-form-field">
                    <label class="cot-form-label" for="cot-service-time">Tiempo estimado de reparación</label>
                    <input
                      id="cot-service-time"
                      class="cot-form-input"
                      type="text"
                      placeholder="Ej. 2 horas, 1 día"
                      [(ngModel)]="quotationOfferForm.estimated_service_time"
                      name="cot_service_time"
                    />
                  </div>

                  <div class="cot-form-field">
                    <label class="cot-form-label" for="cot-eta">ETA de llegada</label>
                    <input
                      id="cot-eta"
                      class="cot-form-input"
                      type="text"
                      placeholder="Ej. 30 minutos, 1 hora"
                      [(ngModel)]="quotationOfferForm.estimated_arrival_time"
                      name="cot_eta"
                    />
                  </div>

                  <div class="cot-form-field">
                    <label class="cot-form-label" for="cot-warranty">Garantía</label>
                    <input
                      id="cot-warranty"
                      class="cot-form-input"
                      type="text"
                      placeholder="Ej. 3 meses en mano de obra"
                      [(ngModel)]="quotationOfferForm.warranty"
                      name="cot_warranty"
                    />
                  </div>

                  <div class="cot-form-field">
                    <label class="cot-form-label" for="cot-validity">
                      Vigencia de la cotización (días)
                      <span class="cot-field-hint">máx. {{ maxValidityDays }} día(s)</span>
                    </label>
                    <input
                      id="cot-validity"
                      class="cot-form-input"
                      type="number"
                      min="1"
                      [max]="maxValidityDays"
                      [placeholder]="maxValidityDays >= 3 ? '3' : '1'"
                      [(ngModel)]="quotationOfferForm.validity_days"
                      name="cot_validity"
                    />
                  </div>

                  <div class="cot-form-field cot-field-full">
                    <label class="cot-form-label" for="cot-obs">Observaciones</label>
                    <textarea
                      id="cot-obs"
                      class="cot-form-textarea"
                      rows="3"
                      placeholder="Condiciones adicionales, exclusiones, notas para el cliente..."
                      [(ngModel)]="quotationOfferForm.observations"
                      name="cot_obs"
                    ></textarea>
                  </div>

                  <div class="cot-form-field cot-field-full">
                    <label class="cot-form-label" for="cot-conditions">Condiciones del servicio</label>
                    <textarea
                      id="cot-conditions"
                      class="cot-form-textarea"
                      rows="3"
                      placeholder="Ej. El servicio incluye traslado hasta el taller. No incluye piezas de origen no original."
                      [(ngModel)]="quotationOfferForm.condiciones_servicio"
                      name="cot_conditions"
                    ></textarea>
                  </div>
                </div>

                <div *ngIf="quotationOfferFeedback" class="cot-form-feedback cot-form-feedback-error">
                  {{ quotationOfferFeedback }}
                </div>

                <div class="cot-form-actions">
                  <button class="cot-back-btn" type="button" (click)="quotationView = 'detail'" [disabled]="isSubmittingOffer">
                    Cancelar
                  </button>
                  <button class="cot-btn-submit" type="submit" [disabled]="isSubmittingOffer">
                    <span *ngIf="!isSubmittingOffer">{{ selectedWorkshopOffer ? 'Actualizar cotización' : 'Enviar cotización' }}</span>
                    <span *ngIf="isSubmittingOffer">Enviando...</span>
                  </button>
                </div>
              </form>
            </ng-container>

            <!-- ── VISTA: confirmación ─────────────────────────────────────── -->
            <ng-container *ngIf="quotationView === 'confirmation' && lastSubmittedOffer">
              <div class="cot-confirmation">
                <div class="cot-confirmation-icon">✓</div>
                <h2 class="cot-confirmation-title">{{ lastSubmittedOffer.status === 'actualizada' ? 'Cotización actualizada exitosamente' : 'Cotización enviada exitosamente' }}</h2>
                <p class="cot-confirmation-sub">Tu propuesta fue registrada para la solicitud #{{ lastSubmittedOffer.quotation_request_id }}.</p>

                <div class="cot-confirmation-summary">
                  <div class="cot-summary-row">
                    <span class="cot-summary-label">Precio:</span>
                    <span class="cot-summary-value">Bs. {{ lastSubmittedOffer.price }}</span>
                  </div>
                  <div class="cot-summary-row" *ngIf="lastSubmittedOffer.service_description">
                    <span class="cot-summary-label">Servicio:</span>
                    <span class="cot-summary-value">{{ lastSubmittedOffer.service_description }}</span>
                  </div>
                  <div class="cot-summary-row" *ngIf="lastSubmittedOffer.spare_parts">
                    <span class="cot-summary-label">Repuestos:</span>
                    <span class="cot-summary-value">{{ lastSubmittedOffer.spare_parts }}</span>
                  </div>
                  <div class="cot-summary-row" *ngIf="lastSubmittedOffer.labor_detail">
                    <span class="cot-summary-label">Mano de obra:</span>
                    <span class="cot-summary-value">{{ lastSubmittedOffer.labor_detail }}</span>
                  </div>
                  <div class="cot-summary-row" *ngIf="lastSubmittedOffer.labor_cost != null">
                    <span class="cot-summary-label">Costo mano de obra:</span>
                    <span class="cot-summary-value">Bs. {{ lastSubmittedOffer.labor_cost }}</span>
                  </div>
                  <div class="cot-summary-row" *ngIf="lastSubmittedOffer.spare_parts_cost != null">
                    <span class="cot-summary-label">Costo repuestos:</span>
                    <span class="cot-summary-value">Bs. {{ lastSubmittedOffer.spare_parts_cost }}</span>
                  </div>
                  <div class="cot-summary-row" *ngIf="lastSubmittedOffer.estimated_service_time">
                    <span class="cot-summary-label">Tiempo reparación:</span>
                    <span class="cot-summary-value">{{ lastSubmittedOffer.estimated_service_time }}</span>
                  </div>
                  <div class="cot-summary-row" *ngIf="lastSubmittedOffer.estimated_arrival_time">
                    <span class="cot-summary-label">ETA llegada:</span>
                    <span class="cot-summary-value">{{ lastSubmittedOffer.estimated_arrival_time }}</span>
                  </div>
                  <div class="cot-summary-row" *ngIf="lastSubmittedOffer.warranty">
                    <span class="cot-summary-label">Garantía:</span>
                    <span class="cot-summary-value">{{ lastSubmittedOffer.warranty }}</span>
                  </div>
                  <div class="cot-summary-row" *ngIf="lastSubmittedOffer.validity_days">
                    <span class="cot-summary-label">Vigencia:</span>
                    <span class="cot-summary-value">{{ lastSubmittedOffer.validity_days }} días</span>
                  </div>
                  <div class="cot-summary-row" *ngIf="lastSubmittedOffer.observations">
                    <span class="cot-summary-label">Observaciones:</span>
                    <span class="cot-summary-value">{{ lastSubmittedOffer.observations }}</span>
                  </div>
                  <div class="cot-summary-row" *ngIf="lastSubmittedOffer.condiciones_servicio">
                    <span class="cot-summary-label">Condiciones:</span>
                    <span class="cot-summary-value">{{ lastSubmittedOffer.condiciones_servicio }}</span>
                  </div>
                </div>

                <div class="cot-confirmation-actions">
                  <button class="cot-btn-primary" type="button" (click)="resetQuotationView()">
                    Ver todas las solicitudes
                  </button>
                </div>
              </div>
            </ng-container>

          </article>
          <!-- ===== FIN SECCIÓN SOLICITUDES RECIBIDAS ===== -->

          <!-- ===== SECCIÓN COTIZACIONES — HISTORIAL ===== -->
          <article class="dashboard-panel dashboard-panel-wide cot-panel" *ngIf="selectedSection === 'quotation_history'">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Historial de propuestas</p>
                <h2>{{ isTenantQuotationSession ? 'Propuestas del tenant' : 'Mis cotizaciones' }}</h2>
              </div>
              <div class="dashboard-toolbar">
                <span class="dashboard-toolbar-note">{{ quotationOffers.length }} propuesta(s)</span>
                <button class="dashboard-refresh-button" type="button" (click)="loadQuotationHistory()">Actualizar</button>
              </div>
            </div>

            <div *ngIf="isQuotationHistoryLoading" class="dashboard-loading-state">Cargando historial...</div>

            <div *ngIf="!isQuotationHistoryLoading && quotationOffers.length === 0" class="dashboard-empty-state">
              No hay cotizaciones registradas aún.
            </div>

            <div *ngIf="!isQuotationHistoryLoading && quotationOffers.length > 0" class="cot-history-list">
              <div class="cot-history-card" *ngFor="let offer of quotationOffers">
                <div class="cot-history-card-head">
                  <div class="cot-history-card-meta">
                    <strong class="cot-history-id">Cotización #{{ offer.id }}</strong>
                    <span class="cot-history-sub">Solicitud #{{ offer.quotation_request_id }}
                      <ng-container *ngIf="offer.emergency_id"> · Emergencia #{{ offer.emergency_id }}</ng-container>
                    </span>
                  </div>
                  <div class="cot-history-badges">
                    <span class="dashboard-badge"
                      [class.dashboard-badge-green]="offer.status === 'aceptada' || offer.status === 'seleccionado'"
                      [class.dashboard-badge-yellow]="offer.status === 'enviada'"
                      [class.dashboard-badge-blue]="offer.status === 'actualizada'"
                      [class.dashboard-badge-red]="offer.status === 'rechazado' || offer.status === 'expirado'">
                      {{ quotationOfferStateLabel(offer) }}
                    </span>
                    <span *ngIf="offer.request_status" class="dashboard-badge"
                      [class.dashboard-badge-green]="offer.request_status === 'seleccionado'"
                      [class.dashboard-badge-yellow]="offer.request_status === 'abierto' || offer.request_status === 'con_propuestas'"
                      [class.dashboard-badge-red]="offer.request_status === 'cancelado' || offer.request_status === 'expirado'">
                      Solicitud: {{ offer.request_status }}
                    </span>
                  </div>
                </div>

                <div class="cot-history-card-body">
                  <div class="cot-history-row" *ngIf="isTenantQuotationSession">
                    <span class="cot-history-label">Taller</span>
                    <span class="cot-history-value">{{ offer.workshop_name || '—' }}</span>
                  </div>
                  <div class="cot-history-row" *ngIf="isTenantQuotationSession">
                    <span class="cot-history-label">Cliente</span>
                    <span class="cot-history-value">{{ offer.client_name || '—' }}</span>
                  </div>
                  <div class="cot-history-row">
                    <span class="cot-history-label">Precio</span>
                    <span class="cot-history-value cot-price-highlight">{{ offer.price != null ? 'Bs. ' + offer.price : '—' }}</span>
                  </div>
                  <div class="cot-history-row" *ngIf="offer.service_description">
                    <span class="cot-history-label">Servicio</span>
                    <span class="cot-history-value">{{ offer.service_description }}</span>
                  </div>
                  <div class="cot-history-row" *ngIf="offer.spare_parts">
                    <span class="cot-history-label">Repuestos</span>
                    <span class="cot-history-value">{{ offer.spare_parts }}</span>
                  </div>
                  <div class="cot-history-row" *ngIf="offer.labor_detail">
                    <span class="cot-history-label">Mano de obra</span>
                    <span class="cot-history-value">{{ offer.labor_detail }}</span>
                  </div>
                  <div class="cot-history-row" *ngIf="offer.labor_cost != null">
                    <span class="cot-history-label">Costo mano de obra</span>
                    <span class="cot-history-value">{{ 'Bs. ' + offer.labor_cost }}</span>
                  </div>
                  <div class="cot-history-row" *ngIf="offer.spare_parts_cost != null">
                    <span class="cot-history-label">Costo repuestos</span>
                    <span class="cot-history-value">{{ 'Bs. ' + offer.spare_parts_cost }}</span>
                  </div>
                  <div class="cot-history-row" *ngIf="offer.estimated_service_time">
                    <span class="cot-history-label">Tiempo reparación</span>
                    <span class="cot-history-value">{{ offer.estimated_service_time }}</span>
                  </div>
                  <div class="cot-history-row" *ngIf="offer.estimated_arrival_time">
                    <span class="cot-history-label">ETA llegada</span>
                    <span class="cot-history-value">{{ offer.estimated_arrival_time }}</span>
                  </div>
                  <div class="cot-history-row" *ngIf="offer.warranty">
                    <span class="cot-history-label">Garantía</span>
                    <span class="cot-history-value">{{ offer.warranty }}</span>
                  </div>
                  <div class="cot-history-row" *ngIf="offer.validity_days">
                    <span class="cot-history-label">Vigencia</span>
                    <span class="cot-history-value">{{ offer.validity_days }} días</span>
                  </div>
                  <div class="cot-history-row" *ngIf="offer.observations">
                    <span class="cot-history-label">Observaciones</span>
                    <span class="cot-history-value">{{ offer.observations }}</span>
                  </div>
                  <div class="cot-history-row" *ngIf="offer.condiciones_servicio">
                    <span class="cot-history-label">Condiciones</span>
                    <span class="cot-history-value">{{ offer.condiciones_servicio }}</span>
                  </div>
                </div>

                <!-- Banner resultado selección -->
                <div class="cot-result-banner cot-result-aceptada" *ngIf="offer.status === 'aceptada'">
                  <span class="cot-result-icon">✅</span>
                  <div>
                    <strong>¡Tu cotización fue aceptada!</strong>
                    <p>El cliente seleccionó tu propuesta. Ve a <a class="cot-banner-link" (click)="selectSection('contracted_services')">Servicios contratados</a> para gestionar la atención.</p>
                  </div>
                </div>

                <div class="cot-result-banner cot-result-rechazada" *ngIf="offer.status === 'rechazada'">
                  <span class="cot-result-icon">❌</span>
                  <div>
                    <strong>Cotización no seleccionada</strong>
                    <p>El cliente seleccionó otra propuesta (NO_SELECCIONADA). Esta cotización queda bloqueada.</p>
                  </div>
                </div>

                <div class="cot-result-banner cot-result-expirada" *ngIf="offer.status === 'expirado'">
                  <span class="cot-result-icon">⏰</span>
                  <div>
                    <strong>Cotización vencida</strong>
                    <p>La vigencia de esta cotización expiró sin ser seleccionada.</p>
                  </div>
                </div>

                <div class="cot-history-card-foot">
                  <span>Enviada: {{ offer.created_at | date: 'dd/MM/yyyy HH:mm' }}</span>
                  <span *ngIf="offer.expires_at">Vence: {{ offer.expires_at | date: 'dd/MM/yyyy HH:mm' }}</span>
                  <button *ngIf="offer.status === 'aceptada'" class="cot-btn-sm cot-btn-success" type="button" (click)="selectSection('contracted_services')">
                    Ver servicio contratado →
                  </button>
                </div>
              </div>
            </div>
          </article>
          <!-- ===== FIN SECCIÓN HISTORIAL ===== -->

          <!-- ===== SECCIÓN SERVICIOS CONTRATADOS (CU10-B) ===== -->
          <article class="dashboard-panel dashboard-panel-wide cot-panel" *ngIf="selectedSection === 'contracted_services'">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Cotizaciones aceptadas</p>
                <h2>{{ isTenantQuotationSession ? 'Servicios contratados del tenant' : 'Servicios contratados' }}</h2>
              </div>
              <div class="dashboard-toolbar">
                <span class="dashboard-toolbar-note">{{ contractedServices.length }} servicio(s)</span>
                <button class="dashboard-refresh-button" type="button" (click)="loadContractedServices()">Actualizar</button>
              </div>
            </div>

            <div *ngIf="isContractedServicesLoading" class="dashboard-loading-state">Cargando servicios contratados...</div>

            <!-- ── Vista lista ─────────────────────────────────────────────── -->
            <ng-container *ngIf="!isContractedServicesLoading && contractedServicesView === 'list'">

              <div *ngIf="contractedServices.length === 0" class="dashboard-empty-state">
                No hay servicios contratados aún. Cuando un cliente acepte tu cotización aparecerá aquí.
              </div>

              <div *ngIf="contractedServices.length > 0" class="svc-table-wrapper">
                <table class="svc-table">
                  <thead>
                    <tr>
                      <th>Código</th>
                      <th *ngIf="isTenantQuotationSession">Taller</th>
                      <th>Cliente</th>
                      <th>Vehículo</th>
                      <th>Tipo emergencia</th>
                      <th>Estado emergencia</th>
                      <th>Monto</th>
                      <th>Fecha contratación</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr *ngFor="let svc of contractedServices">
                      <td>
                        <span class="svc-code">
                          COT-{{ svc.id }}
                          <span class="svc-sub" *ngIf="svc.emergency_id">&nbsp;· EM-{{ svc.emergency_id }}</span>
                        </span>
                      </td>
                      <td *ngIf="isTenantQuotationSession">{{ svc.workshop_name || '—' }}</td>
                      <td>{{ svc.client_name || '—' }}</td>
                      <td>
                        <span *ngIf="svc.vehicle_name || svc.vehicle_plate">
                          {{ svc.vehicle_name }}
                          <span class="svc-plate" *ngIf="svc.vehicle_plate">{{ svc.vehicle_plate }}</span>
                        </span>
                        <span *ngIf="!svc.vehicle_name && !svc.vehicle_plate">—</span>
                      </td>
                      <td>{{ svc.problem_type || '—' }}</td>
                      <td>
                        <span class="dashboard-badge"
                          [class.dashboard-badge-green]="svc.emergency_status === 'servicio_finalizado'"
                          [class.dashboard-badge-blue]="svc.emergency_status === 'servicio_en_proceso' || svc.emergency_status === 'tecnico_en_sitio' || svc.emergency_status === 'auxilio_en_camino' || svc.emergency_status === 'auxilio_asignado'"
                          [class.dashboard-badge-yellow]="svc.emergency_status === 'solicitud_recibida' || svc.emergency_status === 'en_revision'"
                          [class.dashboard-badge-red]="svc.emergency_status === 'rechazado' || svc.emergency_status === 'solicitud_cancelada'">
                          {{ contractedServiceEmergencyStatusLabel(svc.emergency_status) }}
                        </span>
                      </td>
                      <td class="svc-price">{{ svc.price != null ? 'Bs. ' + svc.price : '—' }}</td>
                      <td>{{ svc.offer_created_at | date: 'dd/MM/yyyy HH:mm' }}</td>
                      <td>
                        <button class="cot-btn-sm" type="button" (click)="openContractedServiceDetail(svc)">Ver detalle</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </ng-container>

            <!-- ── Vista detalle ───────────────────────────────────────────── -->
            <ng-container *ngIf="!isContractedServicesLoading && contractedServicesView === 'detail' && selectedContractedService">
              <div class="cot-detail-header">
                <button class="cot-back-btn" type="button" (click)="closeContractedServiceDetail()">
                  ← Volver a la lista
                </button>
                <h3 class="cot-detail-title">
                  Servicio contratado COT-{{ selectedContractedService.id }}
                  <ng-container *ngIf="selectedContractedService.emergency_id">
                    · Emergencia EM-{{ selectedContractedService.emergency_id }}
                  </ng-container>
                </h3>
              </div>

              <!-- Banner ACEPTADA -->
              <div class="svc-status-banner svc-banner-aceptada">
                <span class="svc-banner-icon">✅</span>
                <div>
                  <strong>Cotización aceptada por el cliente</strong>
                  <p>Fecha de aceptación: {{ selectedContractedService.offer_created_at | date: 'dd/MM/yyyy · HH:mm' }}</p>
                </div>
              </div>

              <div class="svc-detail-grid">
                <!-- Información del cliente -->
                <div class="svc-detail-card">
                  <h4 class="svc-detail-card-title">👤 Cliente</h4>
                  <div class="svc-detail-row">
                    <span class="svc-detail-label">Nombre</span>
                    <span class="svc-detail-value">{{ selectedContractedService.client_name || '—' }}</span>
                  </div>
                  <div class="svc-detail-row">
                    <span class="svc-detail-label">Teléfono</span>
                    <span class="svc-detail-value">{{ selectedContractedService.client_phone || '—' }}</span>
                  </div>
                </div>

                <!-- Información del vehículo -->
                <div class="svc-detail-card">
                  <h4 class="svc-detail-card-title">🚗 Vehículo</h4>
                  <div class="svc-detail-row">
                    <span class="svc-detail-label">Modelo</span>
                    <span class="svc-detail-value">{{ selectedContractedService.vehicle_name || '—' }}</span>
                  </div>
                  <div class="svc-detail-row">
                    <span class="svc-detail-label">Placa</span>
                    <span class="svc-detail-value">{{ selectedContractedService.vehicle_plate || '—' }}</span>
                  </div>
                  <div class="svc-detail-row">
                    <span class="svc-detail-label">Tipo emergencia</span>
                    <span class="svc-detail-value">{{ selectedContractedService.problem_type || '—' }}</span>
                  </div>
                </div>

                <!-- Información de la emergencia -->
                <div class="svc-detail-card">
                  <h4 class="svc-detail-card-title">📍 Emergencia</h4>
                  <div class="svc-detail-row">
                    <span class="svc-detail-label">Dirección</span>
                    <span class="svc-detail-value">{{ selectedContractedService.address || '—' }}</span>
                  </div>
                  <div class="svc-detail-row" *ngIf="selectedContractedService.zone">
                    <span class="svc-detail-label">Zona</span>
                    <span class="svc-detail-value">{{ selectedContractedService.zone }}</span>
                  </div>
                  <div class="svc-detail-row" *ngIf="selectedContractedService.emergency_description">
                    <span class="svc-detail-label">Descripción</span>
                    <span class="svc-detail-value">{{ selectedContractedService.emergency_description }}</span>
                  </div>
                  <div class="svc-detail-row">
                    <span class="svc-detail-label">Fecha emergencia</span>
                    <span class="svc-detail-value">{{ selectedContractedService.emergency_created_at | date: 'dd/MM/yyyy HH:mm' }}</span>
                  </div>
                  <div class="svc-detail-row">
                    <span class="svc-detail-label">Estado actual</span>
                    <span class="dashboard-badge"
                      [class.dashboard-badge-green]="selectedContractedService.emergency_status === 'servicio_finalizado'"
                      [class.dashboard-badge-blue]="selectedContractedService.emergency_status === 'servicio_en_proceso' || selectedContractedService.emergency_status === 'tecnico_en_sitio' || selectedContractedService.emergency_status === 'auxilio_en_camino' || selectedContractedService.emergency_status === 'auxilio_asignado'"
                      [class.dashboard-badge-yellow]="selectedContractedService.emergency_status === 'solicitud_recibida' || selectedContractedService.emergency_status === 'en_revision'"
                      [class.dashboard-badge-red]="selectedContractedService.emergency_status === 'rechazado' || selectedContractedService.emergency_status === 'solicitud_cancelada'">
                      {{ contractedServiceEmergencyStatusLabel(selectedContractedService.emergency_status) }}
                    </span>
                  </div>
                  <div class="svc-detail-row" *ngIf="selectedContractedService.hora_llegada">
                    <span class="svc-detail-label">Llegada técnico</span>
                    <span class="svc-detail-value">{{ selectedContractedService.hora_llegada | date: 'dd/MM/yyyy HH:mm' }}</span>
                  </div>
                </div>

                <!-- Información de la cotización -->
                <div class="svc-detail-card">
                  <h4 class="svc-detail-card-title">💰 Cotización aceptada</h4>
                  <div class="svc-detail-row">
                    <span class="svc-detail-label">Monto total</span>
                    <span class="svc-detail-value svc-price-highlight">{{ selectedContractedService.price != null ? 'Bs. ' + selectedContractedService.price : '—' }}</span>
                  </div>
                  <div class="svc-detail-row" *ngIf="selectedContractedService.labor_cost != null">
                    <span class="svc-detail-label">Mano de obra</span>
                    <span class="svc-detail-value">Bs. {{ selectedContractedService.labor_cost }}</span>
                  </div>
                  <div class="svc-detail-row" *ngIf="selectedContractedService.spare_parts_cost != null">
                    <span class="svc-detail-label">Repuestos</span>
                    <span class="svc-detail-value">Bs. {{ selectedContractedService.spare_parts_cost }}</span>
                  </div>
                  <div class="svc-detail-row" *ngIf="selectedContractedService.estimated_service_time">
                    <span class="svc-detail-label">Tiempo estimado</span>
                    <span class="svc-detail-value">{{ selectedContractedService.estimated_service_time }}</span>
                  </div>
                  <div class="svc-detail-row" *ngIf="selectedContractedService.warranty">
                    <span class="svc-detail-label">Garantía</span>
                    <span class="svc-detail-value">{{ selectedContractedService.warranty }}</span>
                  </div>
                  <div class="svc-detail-row" *ngIf="selectedContractedService.service_description">
                    <span class="svc-detail-label">Descripción servicio</span>
                    <span class="svc-detail-value">{{ selectedContractedService.service_description }}</span>
                  </div>
                  <div class="svc-detail-row" *ngIf="selectedContractedService.spare_parts">
                    <span class="svc-detail-label">Repuestos</span>
                    <span class="svc-detail-value">{{ selectedContractedService.spare_parts }}</span>
                  </div>
                  <div class="svc-detail-row" *ngIf="selectedContractedService.labor_detail">
                    <span class="svc-detail-label">Mano de obra detalle</span>
                    <span class="svc-detail-value">{{ selectedContractedService.labor_detail }}</span>
                  </div>
                  <div class="svc-detail-row" *ngIf="selectedContractedService.observations">
                    <span class="svc-detail-label">Observaciones</span>
                    <span class="svc-detail-value">{{ selectedContractedService.observations }}</span>
                  </div>
                  <div class="svc-detail-row" *ngIf="selectedContractedService.condiciones_servicio">
                    <span class="svc-detail-label">Condiciones</span>
                    <span class="svc-detail-value">{{ selectedContractedService.condiciones_servicio }}</span>
                  </div>
                  <div class="svc-detail-row" *ngIf="selectedContractedService.request_expires_at">
                    <span class="svc-detail-label">Vigencia solicitud</span>
                    <span class="svc-detail-value">{{ selectedContractedService.request_expires_at | date: 'dd/MM/yyyy HH:mm' }}</span>
                  </div>
                </div>
              </div>

              <!-- Flujo operativo + Asignación de técnico -->
              <div class="svc-next-steps">
                <h4 class="svc-next-steps-title">Flujo operativo</h4>

                <!-- Timeline de pasos -->
                <div class="svc-next-steps-grid">
                  <div class="svc-next-step"
                    [class.svc-step-done]="(selectedContractedService.emergency_status && statusFilterGroup($any(selectedContractedService.emergency_status)) === 'activo') || selectedContractedService.emergency_status === 'servicio_finalizado'"
                    [class.svc-step-active]="selectedContractedService.emergency_status === 'solicitud_recibida' || selectedContractedService.emergency_status === 'en_revision'">
                    <span class="svc-step-icon">👷</span>
                    <span class="svc-step-label">Asignar técnico</span>
                    <span class="svc-step-hint">CU11</span>
                  </div>
                  <div class="svc-next-step"
                    [class.svc-step-done]="selectedContractedService.emergency_status === 'auxilio_en_camino' || selectedContractedService.emergency_status === 'tecnico_en_sitio' || selectedContractedService.emergency_status === 'servicio_en_proceso' || selectedContractedService.emergency_status === 'servicio_finalizado'"
                    [class.svc-step-active]="selectedContractedService.emergency_status === 'auxilio_asignado'">
                    <span class="svc-step-icon">🚗</span>
                    <span class="svc-step-label">En camino</span>
                    <span class="svc-step-hint">CU22</span>
                  </div>
                  <div class="svc-next-step"
                    [class.svc-step-done]="selectedContractedService.emergency_status === 'servicio_en_proceso' || selectedContractedService.emergency_status === 'servicio_finalizado'"
                    [class.svc-step-active]="selectedContractedService.emergency_status === 'tecnico_en_sitio'">
                    <span class="svc-step-icon">📍</span>
                    <span class="svc-step-label">Técnico en sitio</span>
                    <span class="svc-step-hint">CU22-B</span>
                  </div>
                  <div class="svc-next-step"
                    [class.svc-step-done]="selectedContractedService.emergency_status === 'servicio_finalizado'"
                    [class.svc-step-active]="selectedContractedService.emergency_status === 'servicio_en_proceso'">
                    <span class="svc-step-icon">🔧</span>
                    <span class="svc-step-label">En atención</span>
                    <span class="svc-step-hint">CU23</span>
                  </div>
                  <div class="svc-next-step"
                    [class.svc-step-done]="selectedContractedService.emergency_status === 'servicio_finalizado'"
                    [class.svc-step-active]="selectedContractedService.emergency_status === 'servicio_finalizado'">
                    <span class="svc-step-icon">✅</span>
                    <span class="svc-step-label">Finalizado</span>
                    <span class="svc-step-hint">CU24</span>
                  </div>
                </div>

                <!-- Panel asignación de técnico -->
                <div class="svc-assignment-panel" *ngIf="selectedContractedService.emergency_id">

                  <!-- Paso 1: aceptar emergencia si aún está en solicitud_recibida o en_revision -->
                  <ng-container *ngIf="selectedContractedService.emergency_status === 'solicitud_recibida' || selectedContractedService.emergency_status === 'en_revision' || selectedContractedService.emergency_status === null || selectedContractedService.emergency_status === 'pendiente'">
                    <p class="svc-assignment-hint">
                      Antes de asignar un técnico debes aceptar la emergencia. Esto inicia el proceso de atención.
                    </p>
                    <button
                      class="cot-btn-primary svc-accept-btn"
                      type="button"
                      [disabled]="isUpdatingContractedStatus"
                      (click)="acceptContractedEmergency()">
                      {{ isUpdatingContractedStatus ? 'Aceptando...' : 'Aceptar emergencia y habilitar asignación' }}
                    </button>
                  </ng-container>

                  <!-- Paso 2: asignar técnico — solo cuando status es exactamente 'activo' -->
                  <ng-container *ngIf="selectedContractedService.emergency_status === 'activo'">
                    <p class="svc-assignment-hint">Selecciona un técnico disponible de tu taller para esta emergencia:</p>

                    <div *ngIf="contractedServiceAssignableTechnicians.length === 0" class="svc-no-technicians">
                      No hay técnicos disponibles en este momento.
                      <a class="cot-banner-link" (click)="selectSection('technicians')">Gestionar técnicos</a>
                    </div>

                    <div *ngIf="contractedServiceAssignableTechnicians.length > 0" class="svc-assignment-controls">
                      <label class="technician-field">
                        <span>Técnico disponible</span>
                        <select [(ngModel)]="selectedContractedTechnicianId" name="selectedContractedTechnicianId">
                          <option [ngValue]="null">— Seleccionar técnico —</option>
                          <option *ngFor="let t of contractedServiceAssignableTechnicians" [ngValue]="t.id">
                            {{ t.full_name }}
                            <ng-container *ngIf="t.specialty"> · {{ t.specialty }}</ng-container>
                          </option>
                        </select>
                      </label>
                      <button
                        class="cot-btn-primary"
                        type="button"
                        [disabled]="isAssigningContractedTechnician || !selectedContractedTechnicianId"
                        (click)="assignContractedTechnician()">
                        {{ isAssigningContractedTechnician ? 'Asignando...' : 'Asignar técnico' }}
                      </button>
                    </div>
                  </ng-container>

                  <!-- Técnico ya en camino / en sitio / en proceso -->
                  <ng-container *ngIf="selectedContractedService.emergency_status === 'auxilio_asignado' || selectedContractedService.emergency_status === 'auxilio_en_camino' || selectedContractedService.emergency_status === 'tecnico_en_sitio' || selectedContractedService.emergency_status === 'servicio_en_proceso'">
                    <p class="svc-assignment-hint">
                      ✓ Técnico asignado. El servicio está en curso — sigue el avance desde la app móvil.
                    </p>
                  </ng-container>

                  <!-- Finalizado -->
                  <ng-container *ngIf="selectedContractedService.emergency_status === 'servicio_finalizado'">
                    <p class="svc-assignment-hint svc-finalized">Servicio finalizado exitosamente.</p>
                  </ng-container>

                  <!-- Feedback -->
                  <p class="svc-assignment-feedback" *ngIf="contractedAssignmentFeedback">
                    {{ contractedAssignmentFeedback }}
                  </p>
                </div>
              </div>

            </ng-container>
          </article>
          <!-- ===== FIN SECCIÓN SERVICIOS CONTRATADOS ===== -->

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'workshops' && !isTenantSession">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">{{ isGlobalAdminSession ? 'Empresas registradas' : 'Registros recibidos' }}</p>
                <h2>{{ isGlobalAdminSession ? 'Solicitudes de registro de empresas' : 'Registra tu taller mecánico' }}</h2>
              </div>
              <div class="dashboard-toolbar">
                <span class="dashboard-toolbar-note">{{ workshops.length }} registros cargados</span>
                <button class="dashboard-refresh-button" type="button" (click)="loadWorkshops()">
                  Actualizar
                </button>
              </div>
            </div>

            <p class="dashboard-loading" *ngIf="isLoading">
              {{ isGlobalAdminSession ? 'Cargando empresas registradas...' : 'Cargando talleres registrados...' }}
            </p>
            <p class="dashboard-empty" *ngIf="!isLoading && !workshops.length">
              {{ isGlobalAdminSession ? 'No hay solicitudes de registro de empresas.' : 'Aún no hay talleres registrados.' }}
            </p>

            <div class="dashboard-table-wrap" *ngIf="!isLoading && workshops.length">
              <table class="dashboard-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Taller</th>
                    <th>Responsable</th>
                    <th>Contacto</th>
                    <th>Zona</th>
                    <th>Especialidad</th>
                    <th>Registro</th>
                    <th>Aprobación</th>
                    <th>Opciones</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let workshop of paginatedWorkshops">
                    <td data-label="ID">
                      <span class="dashboard-id-chip">#{{ workshop.id }}</span>
                    </td>
                    <td data-label="Taller">
                      <div class="dashboard-table-primary">
                        <strong>{{ workshop.workshop_name }}</strong>
                        <span>{{ getWorkshopStatus(workshop.created_at) }}</span>
                      </div>
                    </td>
                    <td data-label="Responsable">{{ workshop.contact_name }}</td>
                    <td data-label="Contacto">
                      <div class="dashboard-table-contact">
                        <strong>{{ workshop.phone }}</strong>
                        <span>{{ workshop.email }}</span>
                      </div>
                    </td>
                    <td data-label="Zona">{{ workshop.zone }}</td>
                    <td data-label="Especialidad">{{ workshop.specialty }}</td>
                    <td data-label="Registro">{{ workshop.created_at | date: 'short' }}</td>
                    <td data-label="Aprobación">
                      <button
                        class="dashboard-status-pill dashboard-status-button"
                        type="button"
                        [attr.data-status]="workshop.approval_status"
                        (click)="cycleWorkshopApproval(workshop)"
                        [attr.aria-label]="'Cambiar aprobación de ' + workshop.workshop_name"
                      >
                        <span class="dashboard-status-dot"></span>
                        {{ workshopApprovalLabel(workshop.approval_status) }}
                      </button>
                    </td>
                    <td data-label="Opciones">
                      <div class="workshop-actions">
                        <button
                          class="technician-icon-button"
                          type="button"
                          (click)="editWorkshop(workshop)"
                          [attr.aria-label]="'Editar ' + workshop.workshop_name"
                          title="Editar"
                        >
                          ✎
                        </button>
                        <button
                          class="technician-icon-button workshop-delete-button"
                          type="button"
                          (click)="deleteWorkshop(workshop)"
                          [attr.aria-label]="'Eliminar ' + workshop.workshop_name"
                          title="Eliminar"
                        >
                          🗑
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="dashboard-pagination" *ngIf="!isLoading && workshops.length > workshopsPageSize">
              <p class="dashboard-pagination-info">
                Mostrando {{ workshopsRangeStart }}-{{ workshopsRangeEnd }} de {{ workshops.length }} registros
              </p>

              <div class="dashboard-pagination-actions">
                <button
                  class="dashboard-secondary-button"
                  type="button"
                  (click)="goToPreviousWorkshopsPage()"
                  [disabled]="workshopsPage === 1"
                >
                  Anterior
                </button>
                <span class="dashboard-pagination-page">Página {{ workshopsPage }} / {{ workshopsTotalPages }}</span>
                <button
                  class="dashboard-secondary-button"
                  type="button"
                  (click)="goToNextWorkshopsPage()"
                  [disabled]="workshopsPage === workshopsTotalPages"
                >
                  Siguiente
                </button>
              </div>
            </div>
          </article>

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'technicians' && !isGlobalAdminSession">
            <div class="technician-crud">
              <div class="technician-crud-head">
                <div>
                  <p class="dashboard-panel-kicker">Gestion del equipo</p>
                  <h2>Gestionar Tecnicos</h2>
                </div>
                <button class="technician-create-button" type="button" (click)="startCreate()">
                  <span>+</span>
                  <span>{{ showTechnicianForm ? (editingTechnicianId ? 'Editar Tecnico' : 'Crear Tecnico') : 'Crear Tecnico' }}</span>
                </button>
              </div>

              <div class="technician-filter-tabs">
                <button
                  type="button"
                  class="technician-filter-tab"
                  [class.is-active]="technicianFilter === 'activos'"
                  (click)="technicianFilter = 'activos'"
                >
                  Activos
                </button>
                <button
                  type="button"
                  class="technician-filter-tab"
                  [class.is-active]="technicianFilter === 'todos'"
                  (click)="technicianFilter = 'todos'"
                >
                  Todos
                </button>
                <button
                  type="button"
                  class="technician-filter-tab"
                  [class.is-active]="technicianFilter === 'historial'"
                  (click)="technicianFilter = 'historial'"
                >
                  Historial
                </button>
              </div>

              <section class="technician-form-card" *ngIf="showTechnicianForm">
                <div class="technician-form-head">
                  <div>
                    <p class="dashboard-panel-kicker">Formulario</p>
                    <h3>{{ editingTechnicianId ? 'Editar tecnico' : 'Agregar tecnico' }}</h3>
                  </div>
                  <button class="dashboard-secondary-button" type="button" (click)="cancelTechnicianForm()">
                    Cerrar
                  </button>
                </div>

                <!--
                  AQUI ESTA EL FORMULARIO DE REGISTRO Y EDICION DE TECNICOS
                -->
                <form class="technician-form technician-form-grid" (ngSubmit)="submitTechnician()">
                  <label class="technician-field">
                    <span>Nombre</span>
                    <input type="text" name="full_name" [(ngModel)]="technicianForm.full_name" required minlength="3" placeholder="Ej. Carlos Ramirez" />
                  </label>

                  <label class="technician-field">
                    <span>Telefono</span>
                    <input type="text" name="phone" [(ngModel)]="technicianForm.phone" required minlength="7" placeholder="Ej. 76324511" />
                  </label>

                  <label class="technician-field">
                    <span>Email</span>
                    <input type="email" name="email" [(ngModel)]="technicianForm.email" required placeholder="Ej. tecnico@correo.com" />
                  </label>

                  <label class="technician-field">
                    <span>Especialidad</span>
                    <select name="specialty" [(ngModel)]="technicianForm.specialty" required>
                      <option value="" disabled>Selecciona una especialidad</option>
                      <option *ngFor="let specialty of technicianSpecialtyOptions" [value]="specialty">
                        {{ specialty }}
                      </option>
                    </select>
                  </label>

                  <label class="technician-field" *ngIf="isTenantSession">
                    <span>Sucursal *</span>
                    <select
                      name="sucursal_id"
                      [(ngModel)]="technicianForm.sucursal_id"
                      [disabled]="isAdminSucursalSession"
                      required
                    >
                      <option [ngValue]="null" disabled>Selecciona una sucursal</option>
                      <option *ngFor="let sucursal of sucursales" [ngValue]="sucursal.id">
                        {{ sucursal.nombre }}
                      </option>
                    </select>
                  </label>

                  <label class="technician-field technician-field-wide">
                    <span>Estado del tecnico</span>
                    <select name="status" [(ngModel)]="technicianForm.status" required>
                      <option value="disponible">Disponible</option>
                      <option value="ocupado">Ocupado</option>
                      <option value="fuera_de_servicio">Fuera de servicio</option>
                    </select>
                  </label>

                  <p
                    class="technician-form-feedback technician-field-wide"
                    *ngIf="isTenantSession && isAdminSucursalSession"
                    style="margin-top:-0.25rem;"
                  >
                    El técnico quedará asignado automáticamente a tu sucursal.
                  </p>

                  <p class="technician-form-feedback technician-field-wide" *ngIf="technicianFeedback">
                    {{ technicianFeedback }}
                  </p>

                  <div class="technician-form-actions technician-field-wide">
                    <button class="dashboard-refresh-button" type="submit" [disabled]="isSavingTechnician">
                      {{ isSavingTechnician ? 'Guardando...' : editingTechnicianId ? 'Guardar cambios' : 'Agregar Tecnico' }}
                    </button>
                    <button class="dashboard-secondary-button" type="button" (click)="resetTechnicianForm()">
                      Limpiar
                    </button>
                  </div>
                </form>
              </section>

              <section class="technician-table-card">
                <p class="dashboard-loading" *ngIf="isTechniciansLoading">Cargando tecnicos...</p>
                <p class="dashboard-empty" *ngIf="!isTechniciansLoading && !filteredTechnicians.length">
                  No hay tecnicos para el filtro seleccionado.
                </p>

                <div class="dashboard-table-wrap technician-table-wrap" *ngIf="!isTechniciansLoading && filteredTechnicians.length">
                  <table class="dashboard-table dashboard-table-technicians">
                    <thead>
                      <tr>
                        <th>Nombre</th>
                        <th>Telefono</th>
                        <th>Email</th>
                        <th>Especialidad</th>
                        <th *ngIf="isTenantSession">Sucursal</th>
                        <th>Estado</th>
                        <th>Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let technician of filteredTechnicians">
                        <td data-label="Nombre">
                          <div class="dashboard-table-primary">
                            <strong>{{ technician.full_name }}</strong>
                            <span>Actualizado {{ technician.updated_at | date: 'shortDate' }}</span>
                          </div>
                        </td>
                        <td data-label="Telefono">{{ technician.phone }}</td>
                        <td data-label="Email">{{ technician.email }}</td>
                        <td data-label="Especialidad">{{ technician.specialty }}</td>
                        <td data-label="Sucursal" *ngIf="isTenantSession">
                          {{ technician.sucursal_nombre || 'Sin sucursal' }}
                        </td>
                        <td data-label="Estado">
                          <span class="dashboard-status-pill" [attr.data-status]="technician.status">
                            <span class="dashboard-status-dot"></span>
                            {{ statusLabel(technician.status) }}
                          </span>
                        </td>
                        <td data-label="Acciones">
                          <div class="technician-actions">
                            <button class="technician-inline-button" type="button" (click)="editTechnician(technician)">
                              Editar
                            </button>
                            <button class="technician-icon-button" type="button" (click)="deleteTechnician(technician)" aria-label="Eliminar tecnico">
                              🗑
                            </button>
                            <button class="technician-icon-button" type="button" (click)="toggleTechnicianStatus(technician)" aria-label="Cambiar estado">
                              ☰
                            </button>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          </article>

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'clients'">
            <div class="technician-crud">
              <div class="technician-crud-head">
                <div>
                  <p class="dashboard-panel-kicker">Usuarios registrados</p>
                  <h2>Lista de Clientes</h2>
                </div>
                <button class="dashboard-refresh-button" type="button" (click)="loadClients()">
                  Actualizar
                </button>
              </div>

              <section class="technician-table-card">
                <p class="dashboard-loading" *ngIf="isClientsLoading">Cargando clientes...</p>
                <p class="dashboard-empty" *ngIf="!isClientsLoading && !clients.length">
                  No hay clientes registrados.
                </p>

                <div class="dashboard-table-wrap technician-table-wrap" *ngIf="!isClientsLoading && clients.length">
                  <table class="dashboard-table dashboard-table-technicians">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Cliente</th>
                        <th>Carnet</th>
                        <th>Correo</th>
                        <th>Telefono</th>
                        <th>Rol</th>
                        <th>Estado</th>
                        <th>Registro</th>
                        <th>Opciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let client of clients">
                        <td data-label="ID">
                          <span class="dashboard-id-chip">#{{ client.id }}</span>
                        </td>
                        <td data-label="Cliente">
                          <div class="dashboard-table-primary">
                            <strong>{{ client.full_name }}</strong>
                            <span>{{ client.accepted_terms ? 'Terminos aceptados' : 'Pendiente de terminos' }}</span>
                          </div>
                        </td>
                        <td data-label="Carnet">{{ client.identity_card }}</td>
                        <td data-label="Correo">{{ client.email }}</td>
                        <td data-label="Telefono">{{ client.phone }}</td>
                        <td data-label="Rol">{{ client.role }}</td>
                        <td data-label="Estado">
                          <button
                            class="dashboard-status-pill dashboard-status-button"
                            type="button"
                            [attr.data-status]="client.status"
                            [attr.aria-label]="'Cambiar estado de ' + client.full_name"
                            (click)="toggleClientStatus(client)"
                          >
                            <span class="dashboard-status-dot"></span>
                            {{ clientStatusLabel(client.status) }}
                          </button>
                        </td>
                        <td data-label="Registro">{{ client.created_at | date: 'short' }}</td>
                        <td data-label="Opciones">
                          <div class="workshop-actions">
                            <button
                              class="technician-icon-button client-action-tooltip"
                              type="button"
                              (click)="editClient(client)"
                              [attr.aria-label]="'Editar ' + client.full_name"
                              data-tooltip="Editar"
                            >
                              ✎
                            </button>
                            <button
                              class="technician-icon-button workshop-delete-button client-action-tooltip"
                              type="button"
                              (click)="deleteClient(client)"
                              [attr.aria-label]="'Eliminar ' + client.full_name"
                              data-tooltip="Eliminar"
                            >
                              🗑
                            </button>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          </article>
      <div class="dashboard-modal-backdrop" *ngIf="showWorkshopEditModal" (click)="cancelWorkshopEdit()">
        <section class="dashboard-modal-card" (click)="$event.stopPropagation()">
          <div class="dashboard-modal-head">
            <div>
              <p class="dashboard-panel-kicker">Edición de registro</p>
              <h3>Actualizar taller</h3>
            </div>
          </div>

          <!--
            AQUI ESTA EL FORMULARIO DE EDICION DE TALLERES
          -->
          <form class="workshop-edit-form" (ngSubmit)="submitWorkshopEdit()">
            <label class="workshop-edit-field">
              <span>Taller</span>
              <input
                type="text"
                name="workshop_name"
                [(ngModel)]="workshopForm.workshop_name"
                required
                minlength="3"
              />
            </label>

            <label class="workshop-edit-field">
              <span>Responsable</span>
              <input
                type="text"
                name="contact_name"
                [(ngModel)]="workshopForm.contact_name"
                required
                minlength="3"
              />
            </label>

            <label class="workshop-edit-field">
              <span>Contacto</span>
              <input
                type="text"
                name="phone"
                [(ngModel)]="workshopForm.phone"
                required
                minlength="7"
              />
            </label>

            <label class="workshop-edit-field">
              <span>Correo Electrónico</span>
              <input
                type="email"
                name="email"
                [(ngModel)]="workshopForm.email"
                required
              />
            </label>

            <label class="workshop-edit-field">
              <span>Zona</span>
              <select name="zone" [(ngModel)]="workshopForm.zone" required>
                <option value="" disabled>Selecciona una zona</option>
                <option *ngFor="let zone of workshopZoneOptions" [value]="zone">{{ zone }}</option>
              </select>
            </label>

            <label class="workshop-edit-field workshop-edit-field-wide">
              <span>Especialidad</span>
              <select name="specialty" [(ngModel)]="workshopForm.specialty" required>
                <option value="" disabled>Selecciona una especialidad</option>
                <option *ngFor="let specialty of workshopSpecialtyOptions" [value]="specialty">
                  {{ specialty }}
                </option>
              </select>
            </label>

            <label class="workshop-edit-field workshop-edit-field-wide">
              <span>Ubicación del Taller</span>
              <div class="workshop-edit-map-field">
                <button
                  class="workshop-edit-map-locate-button"
                  type="button"
                  (click)="locateWorkshopEditCurrentPosition()"
                  [disabled]="isWorkshopLocationLocating"
                  [attr.aria-label]="
                    isWorkshopLocationLocating ? 'Obteniendo ubicación actual' : 'Usar ubicación actual'
                  "
                  [title]="
                    isWorkshopLocationLocating
                      ? 'Ubicando...'
                      : isSecureContext
                        ? 'Usar ubicación actual'
                        : 'La ubicación automática requiere HTTPS o localhost'
                  "
                >
                  ⌖
                </button>
                <div
                  #workshopEditMapCanvas
                  class="workshop-edit-map-canvas"
                  aria-label="Mapa interactivo de ubicación del taller"
                ></div>
              </div>
              <div class="workshop-edit-map-meta">
                <small>Haz clic en el mapa o arrastra el marcador para actualizar la ubicación.</small>
                <strong>
                  Lat: {{ formatCoordinate(workshopForm.latitude) }} | Lng: {{ formatCoordinate(workshopForm.longitude) }}
                </strong>
                <span class="workshop-edit-map-status error" *ngIf="workshopLocationMessage">
                  {{ workshopLocationMessage }}
                </span>
              </div>
            </label>

            <label class="workshop-edit-field workshop-edit-field-wide">
              <span>Nueva contraseña</span>
              <input
                type="password"
                name="password"
                [(ngModel)]="workshopForm.password"
                minlength="6"
                placeholder="Dejar vacio para mantener la actual"
              />
            </label>

            <p class="workshop-edit-feedback" *ngIf="workshopEditFeedback">
              {{ workshopEditFeedback }}
            </p>

            <div class="workshop-edit-actions">
              <button class="dashboard-refresh-button" type="submit" [disabled]="isSavingWorkshop">
                {{ isSavingWorkshop ? 'Actualizando...' : 'Actualizar' }}
              </button>
              <button class="dashboard-secondary-button" type="button" (click)="cancelWorkshopEdit()">
                Cancelar
              </button>
            </div>
          </form>
        </section>
      </div>

      <div class="dashboard-modal-backdrop" *ngIf="showClientEditModal" (click)="cancelClientEdit()">
        <section class="dashboard-modal-card" (click)="$event.stopPropagation()">
          <div class="dashboard-modal-head">
            <div>
              <p class="dashboard-panel-kicker">Edición de cliente</p>
              <h3>Actualizar cliente</h3>
            </div>
          </div>

          <!--
            AQUI ESTA EL FORMULARIO DE EDICION DE CLIENTES
          -->
          <form class="workshop-edit-form" (ngSubmit)="submitClientEdit()">
            <label class="workshop-edit-field">
              <span>Carnet</span>
              <input type="text" name="identity_card" [(ngModel)]="clientForm.identity_card" required minlength="5" />
            </label>

            <label class="workshop-edit-field">
              <span>Nombre completo</span>
              <input type="text" name="full_name" [(ngModel)]="clientForm.full_name" required minlength="3" />
            </label>

            <label class="workshop-edit-field">
              <span>Correo</span>
              <input type="email" name="email" [(ngModel)]="clientForm.email" required />
            </label>

            <label class="workshop-edit-field">
              <span>Telefono</span>
              <input type="text" name="phone" [(ngModel)]="clientForm.phone" required minlength="7" />
            </label>

            <label class="workshop-edit-field">
              <span>Nueva contraseña</span>
              <input
                type="password"
                name="password"
                [(ngModel)]="clientForm.password"
                minlength="6"
                placeholder="Dejar vacio para mantener la actual"
              />
            </label>

            <label class="workshop-edit-field">
              <span>Rol</span>
              <input type="text" name="role" [(ngModel)]="clientForm.role" required minlength="2" />
            </label>

            <label class="workshop-edit-field">
              <span>Estado</span>
              <select name="status" [(ngModel)]="clientForm.status" required>
                <option value="active">Activo</option>
                <option value="suspended">Desactivado</option>
              </select>
            </label>

            <label class="workshop-edit-field workshop-edit-field-wide">
              <span class="client-terms-row">
                <input type="checkbox" name="accepted_terms" [(ngModel)]="clientForm.accepted_terms" />
                <span>Terminos aceptados</span>
              </span>
            </label>

            <p class="workshop-edit-feedback" *ngIf="clientEditFeedback">
              {{ clientEditFeedback }}
            </p>

            <div class="workshop-edit-actions">
              <button class="dashboard-refresh-button" type="submit" [disabled]="isSavingClient">
                {{ isSavingClient ? 'Actualizando...' : 'Actualizar' }}
              </button>
              <button class="dashboard-secondary-button" type="button" (click)="cancelClientEdit()">
                Cancelar
              </button>
            </div>
          </form>
        </section>
      </div>

      <div class="dashboard-modal-backdrop" *ngIf="showClientDeleteModal" (click)="cancelClientDelete()">
        <section class="dashboard-modal-card" (click)="$event.stopPropagation()">
          <div class="dashboard-modal-head">
            <div>
              <p class="dashboard-panel-kicker">Edición de cliente</p>
              <h3>Eliminar cliente</h3>
            </div>
          </div>

          <div class="client-delete-modal-copy">
            <p>
              ¿Deseas eliminar a <strong>{{ clientPendingDelete?.full_name }}</strong>?
            </p>
            <p class="client-delete-modal-note">
              El registro se quitará de la lista de clientes, también se eliminarán sus vehículos registrados y esta acción no se podrá deshacer.
            </p>
          </div>

          <div class="workshop-edit-actions">
            <button class="client-delete-confirm-button" type="button" (click)="confirmClientDelete()">
              Eliminar cliente
            </button>
            <button class="dashboard-secondary-button" type="button" (click)="cancelClientDelete()">
              Cancelar
            </button>
          </div>
        </section>
      </div>

        <!-- ══════════════════════════════════════════════════════════════ -->
        <!-- SECCIÓN: ORGANIZACIONES / TENANTS (solo admin)                -->
        <!-- ══════════════════════════════════════════════════════════════ -->
        <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'tenants' && !isWorkshopSession">
          <div class="dashboard-panel-head">
            <div>
              <p class="dashboard-panel-kicker">Multi-tenant SaaS</p>
              <h2>Gestión de Organizaciones</h2>
            </div>
            <div class="dashboard-toolbar">
              <span class="dashboard-toolbar-note">{{ tenants.length }} organizaciones</span>
              <button class="dashboard-refresh-button" type="button" (click)="openNewTenantForm()">+ Nueva organización</button>
              <button class="dashboard-refresh-button" type="button" (click)="loadTenants()">Actualizar</button>
            </div>
          </div>

          <p class="dashboard-loading" *ngIf="isTenantsLoading">Cargando organizaciones...</p>
          <p class="dashboard-empty" *ngIf="!isTenantsLoading && !tenants.length && !showTenantForm">
            No hay organizaciones registradas. Usa "+ Nueva organización" para crear una.
          </p>

          <!-- Formulario inline para crear / editar tenant -->
          <div class="technician-form" *ngIf="showTenantForm">
            <h3 style="margin:0 0 1rem;font-size:1rem;">{{ editingTenantId ? 'Editar organización' : 'Nueva organización' }}</h3>
            <div class="technician-form-row">
              <label class="technician-field">
                <span>Nombre *</span>
                <input type="text" [(ngModel)]="tenantForm.nombre" placeholder="Ej: Mecánicos Express" maxlength="200" />
              </label>
              <label class="technician-field">
                <span>Estado</span>
                <select [(ngModel)]="tenantForm.estado">
                  <option value="activo">Activo</option>
                  <option value="inactivo">Inactivo</option>
                </select>
              </label>
            </div>
            <label class="technician-field">
              <span>Descripción</span>
              <textarea [(ngModel)]="tenantForm.descripcion" rows="2" placeholder="Descripción opcional" maxlength="1000" style="width:100%;resize:vertical;"></textarea>
            </label>
            <p class="technician-feedback" *ngIf="tenantFeedback">{{ tenantFeedback }}</p>
            <div class="technician-form-actions">
              <button class="dashboard-refresh-button" type="button" (click)="saveTenant()" [disabled]="isSavingTenant">
                {{ isSavingTenant ? 'Guardando...' : (editingTenantId ? 'Actualizar' : 'Crear') }}
              </button>
              <button class="dashboard-secondary-button" type="button" (click)="cancelTenantForm()">Cancelar</button>
            </div>
          </div>

          <!-- Tabla de tenants -->
          <div class="dashboard-table-wrap" *ngIf="!isTenantsLoading && tenants.length">
            <table class="dashboard-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre</th>
                  <th>Descripción</th>
                  <th>Estado</th>
                  <th>Creado</th>
                  <th>Opciones</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let tenant of tenants">
                  <td data-label="ID"><span class="dashboard-id-chip">#{{ tenant.id }}</span></td>
                  <td data-label="Nombre"><strong>{{ tenant.nombre }}</strong></td>
                  <td data-label="Descripción">{{ tenant.descripcion || '—' }}</td>
                  <td data-label="Estado">
                    <span class="dashboard-status-pill" [attr.data-status]="tenant.estado === 'activo' ? 'activo' : 'rechazado'">
                      {{ tenant.estado === 'activo' ? 'Activo' : 'Inactivo' }}
                    </span>
                  </td>
                  <td data-label="Creado">{{ tenant.created_at | date: 'short' }}</td>
                  <td data-label="Opciones">
                    <div class="dashboard-table-actions">
                      <button class="dashboard-refresh-button" type="button" (click)="editTenant(tenant)">Editar</button>
                      <button
                        class="dashboard-secondary-button"
                        type="button"
                        (click)="toggleTenantEstado(tenant)"
                        [disabled]="tenant.id === 1"
                        [title]="tenant.id === 1 ? 'El Tenant Principal no puede desactivarse' : ''"
                      >
                        {{ tenant.estado === 'activo' ? 'Desactivar' : 'Activar' }}
                      </button>
                      <button
                        class="dashboard-danger-button"
                        type="button"
                        (click)="deleteTenant(tenant)"
                        [disabled]="tenant.id === 1"
                        [title]="tenant.id === 1 ? 'El Tenant Principal no puede eliminarse' : ''"
                      >
                        Eliminar
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>

        <!-- ══════════════════════════════════════════════════════════════════
             PANEL: SUCURSALES (solo usuarios tenant)
             ══════════════════════════════════════════════════════════════════ -->
        <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'sucursales' && isTenantSession">
          <div class="dashboard-panel-head">
            <div>
              <p class="dashboard-panel-kicker">Mi empresa</p>
              <h2>Mis Sucursales</h2>
            </div>
            <div style="display:flex; gap:0.5rem; align-items:center;">
              <span class="dashboard-toolbar-note">{{ sucursales.length }} sucursal{{ sucursales.length !== 1 ? 'es' : '' }}</span>
              <button class="dashboard-refresh-button" type="button" (click)="loadSucursales()">Actualizar</button>
              <button
                class="dashboard-refresh-button"
                type="button"
                *ngIf="isSuperadminTenant"
                (click)="openNuevaSucursal()"
              >
                + Nueva
              </button>
            </div>
          </div>

          <p *ngIf="isSucursalesLoading" style="padding:1rem;color:#666;">Cargando sucursales...</p>
          <p *ngIf="!isSucursalesLoading && isAdminSucursalSession" style="padding:0 1rem 1rem;color:#666;">
            Vista de solo lectura para tu rol. Puedes consultar la sucursal dentro de tu alcance, pero la creación y edición queda reservada al SUPERADMIN_TENANT.
          </p>
          <p *ngIf="!isSucursalesLoading && sucursalesFeedback" style="padding:0 1rem 1rem;color:#9a2e23;">
            {{ sucursalesFeedback }}
          </p>
          <p *ngIf="!isSucursalesLoading && sucursales.length === 0" style="padding:1rem;color:#666;">
            {{ isSuperadminTenant ? 'No hay sucursales registradas. Crea la primera con el botón "+ Nueva".' : 'No hay sucursales disponibles para tu alcance.' }}
          </p>

          <!-- Formulario inline de sucursal -->
          <div class="technician-form" *ngIf="showSucursalForm">
            <h3 style="margin-bottom:0.75rem;">{{ editingSucursalId ? 'Editar sucursal' : 'Nueva sucursal' }}</h3>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
              <label class="technician-field">
                <span>Nombre *</span>
                <input type="text" [(ngModel)]="sucursalForm.nombre" placeholder="Nombre de la sucursal" maxlength="200" />
              </label>
              <label class="technician-field">
                <span>Ciudad</span>
                <input type="text" [(ngModel)]="sucursalForm.ciudad" placeholder="Santa Cruz" maxlength="120" />
              </label>
              <label class="technician-field">
                <span>Dirección</span>
                <input
                  type="text"
                  [(ngModel)]="sucursalForm.direccion"
                  placeholder="Dirección"
                  maxlength="400"
                  (input)="handleSucursalAddressManualInput()"
                />
              </label>
              <label class="technician-field">
                <span>Zona *</span>
                <select [(ngModel)]="sucursalForm.zona">
                  <option value="" disabled>Selecciona una zona</option>
                  <option *ngFor="let zone of sucursalZoneOptions" [value]="zone.value">
                    {{ zone.label }}
                  </option>
                </select>
              </label>
              <label class="technician-field">
                <span>Teléfono</span>
                <input type="tel" [(ngModel)]="sucursalForm.telefono" placeholder="Teléfono" maxlength="50" />
              </label>
              <label class="technician-field">
                <span>Responsable</span>
                <input type="text" [(ngModel)]="sucursalForm.responsable" placeholder="Responsable" maxlength="160" />
              </label>
            </div>
            <div style="margin-top:1rem;">
              <strong style="display:block;color:#0f172a;margin-bottom:0.55rem;">Servicios / Especialidades *</strong>
              <small style="display:block;color:#64748b;margin-bottom:0.75rem;">
                Selecciona las especialidades operativas que este taller puede atender.
              </small>
              <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:0.5rem;">
                <label
                  *ngFor="let specialty of sucursalSpecialtyOptions"
                  style="display:flex;align-items:center;gap:0.55rem;border:1px solid #d7dfeb;border-radius:12px;padding:0.7rem 0.85rem;background:#fff;"
                >
                  <input
                    type="checkbox"
                    [checked]="isSucursalSpecialtySelected(specialty)"
                    [disabled]="!isSuperadminTenant"
                    (change)="toggleSucursalSpecialty(specialty, $any($event.target).checked)"
                  />
                  <span>{{ specialty }}</span>
                </label>
              </div>
              <p style="margin:0.7rem 0 0;color:#64748b;font-size:0.9rem;">
                {{ sucursalForm.especialidades.length ? sucursalForm.especialidades.join(' · ') : 'Sin especialidades seleccionadas.' }}
              </p>
            </div>
            <div style="margin-top:1rem;">
              <p style="margin:0 0 0.75rem;color:#64748b;font-size:0.9rem;">
                Cada sucursal mantiene un taller operativo vinculado para emergencias y cotizaciones.
                La primera especialidad seleccionada se sincroniza como especialidad principal compatible.
              </p>
              <div style="display:flex;justify-content:space-between;gap:0.75rem;align-items:center;flex-wrap:wrap;margin-bottom:0.5rem;">
                <div>
                  <strong style="display:block;color:#0f172a;">Selecciona la ubicación exacta de la sucursal</strong>
                  <small style="color:#64748b;">Haz clic en el mapa o arrastra el marcador para elegir la ubicación exacta.</small>
                </div>
                <button
                  class="dashboard-secondary-button"
                  type="button"
                  (click)="locateSucursalCurrentPosition()"
                  [disabled]="isSucursalLocationLocating"
                  [title]="
                    isSucursalLocationLocating
                      ? 'Ubicando...'
                      : isSecureContext
                        ? 'Usar ubicación actual'
                        : 'La ubicación automática requiere HTTPS o localhost'
                  "
                >
                  {{ isSucursalLocationLocating ? 'Ubicando...' : 'Usar ubicación actual' }}
                </button>
              </div>
              <div
                #sucursalMapCanvas
                style="min-height:20rem;width:100%;border:1px solid #d7dfeb;border-radius:12px;overflow:hidden;background:#dfe7f2;"
                aria-label="Mapa interactivo para seleccionar la ubicación exacta de la sucursal"
              ></div>
              <div style="display:grid;gap:0.35rem;margin-top:0.7rem;color:#475569;">
                <strong style="color:#0f172a;font-size:0.92rem;">
                  Lat: {{ formatCoordinate(sucursalForm.latitud) }} | Lng: {{ formatCoordinate(sucursalForm.longitud) }}
                </strong>
                <span *ngIf="isSucursalReverseGeocoding" style="color:#475569;font-size:0.85rem;font-weight:600;">
                  Buscando dirección...
                </span>
                <span *ngIf="!isSucursalReverseGeocoding && sucursalDetectedAddress" style="color:#475569;font-size:0.85rem;font-weight:600;">
                  Dirección detectada: {{ sucursalDetectedAddress }}
                </span>
                <span *ngIf="sucursalLocationMessage" style="color:#9a2e23;font-size:0.85rem;font-weight:600;">
                  {{ sucursalLocationMessage }}
                </span>
                <button
                  *ngIf="canApplySucursalDetectedAddress"
                  class="dashboard-secondary-button"
                  type="button"
                  (click)="applySucursalDetectedAddress()"
                  style="justify-self:start;"
                >
                  Usar dirección del mapa
                </button>
              </div>
            </div>
            <p *ngIf="sucursalesFeedback" class="technician-form-feedback" style="margin-top:0.85rem;">
              {{ sucursalesFeedback }}
            </p>
            <p
              *ngIf="editingSucursalId"
              style="margin:0.85rem 0 0;color:#64748b;font-size:0.9rem;"
            >
              Revisa los datos y presiona Guardar cambios para aplicar la edición.
            </p>
            <div class="technician-form-actions">
              <button class="dashboard-refresh-button" type="button" (click)="saveSucursal()">
                {{ editingSucursalId ? 'Guardar cambios' : 'Crear sucursal' }}
              </button>
              <button class="dashboard-secondary-button" type="button" (click)="cancelSucursalForm()">Cancelar</button>
            </div>
          </div>

          <div class="dashboard-table-wrap" *ngIf="!isSucursalesLoading && sucursales.length > 0">
            <table class="dashboard-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre</th>
                  <th>Dirección / Zona</th>
                  <th>Teléfono</th>
                  <th>Responsable</th>
                  <th>Estado</th>
                  <th *ngIf="isSuperadminTenant">Opciones</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let suc of sucursales">
                  <td data-label="ID"><span class="dashboard-id-chip">#{{ suc.id }}</span></td>
                  <td data-label="Nombre"><strong>{{ suc.nombre }}</strong></td>
                  <td data-label="Dirección / Zona">
                    <div class="dashboard-table-primary">
                      <strong>{{ suc.direccion || suc.ciudad || '—' }}{{ suc.zona ? ' · ' + suc.zona : '' }}</strong>
                      <span>
                        {{ suc.workshop_name || 'Sin taller operativo vinculado' }}
                        {{ suc.workshop_specialty ? ' · ' + suc.workshop_specialty : '' }}
                      </span>
                      <span *ngIf="suc.especialidades.length; else noSucursalSpecialties" style="display:flex;flex-wrap:wrap;gap:0.35rem;margin-top:0.35rem;">
                        <span
                          *ngFor="let specialty of suc.especialidades"
                          class="dashboard-status-pill"
                          data-status="pendiente"
                          style="font-size:0.72rem;"
                        >
                          {{ specialty }}
                        </span>
                      </span>
                      <ng-template #noSucursalSpecialties>
                        <span>Sin especialidades registradas</span>
                      </ng-template>
                    </div>
                  </td>
                  <td data-label="Teléfono">{{ suc.telefono || '—' }}</td>
                  <td data-label="Responsable">
                    <div class="dashboard-table-primary">
                      <strong>{{ suc.responsable || '—' }}</strong>
                      <span>
                        {{ suc.technicians_count }} técnico{{ suc.technicians_count === 1 ? '' : 's' }}
                        {{ suc.workshop_availability_status ? ' · ' + suc.workshop_availability_status : '' }}
                      </span>
                    </div>
                  </td>
                  <td data-label="Estado">
                    <span class="dashboard-status-pill" [attr.data-status]="suc.estado === 'activo' ? 'activo' : 'rechazado'">
                      {{ suc.estado === 'activo' ? 'Activo' : 'Inactivo' }}
                    </span>
                  </td>
                  <td data-label="Opciones" *ngIf="isSuperadminTenant">
                    <div class="dashboard-table-actions">
                      <button class="dashboard-refresh-button" type="button" (click)="editSucursal(suc)">Editar</button>
                      <button class="dashboard-danger-button" type="button" (click)="deleteSucursal(suc.id)">Eliminar</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <section
            *ngIf="!isSucursalesLoading && sucursales.length > 0"
            style="margin:1.25rem 1rem 0;padding:1.25rem;border-radius:20px;background:#fff;box-shadow:0 14px 34px rgba(15,23,42,0.08);border:1px solid #e2e8f0;"
          >
            <div style="display:grid;gap:0.3rem;margin-bottom:1rem;">
              <h3 style="margin:0;color:#0f172a;font-size:1.2rem;">Mapa de sucursales</h3>
              <p style="margin:0;color:#64748b;font-size:0.95rem;">
                Visualiza la ubicación de todas las sucursales activas de tu empresa.
              </p>
            </div>

            <p *ngIf="sucursalesOverviewData.length === 0" style="margin:0;color:#64748b;">
              No hay sucursales con ubicación registrada.
            </p>

            <div
              *ngIf="sucursalesOverviewData.length > 0"
              #sucursalesOverviewMapCanvas
              style="height:360px;width:100%;border:1px solid #d7dfeb;border-radius:16px;overflow:hidden;background:#dfe7f2;"
              aria-label="Mapa general de sucursales activas del tenant"
            ></div>
          </section>
        </article>

        <!-- ══════════════════════════════════════════════════════════════════
             PANEL: USUARIOS DE MI EMPRESA (solo SUPERADMIN_TENANT)
             ══════════════════════════════════════════════════════════════════ -->
        <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'usuarios_empresa' && isTenantSession">
          <div class="dashboard-panel-head">
            <div>
              <p class="dashboard-panel-kicker">Mi empresa</p>
              <h2>Usuarios</h2>
            </div>
            <div style="display:flex; gap:0.5rem; align-items:center;">
              <span class="dashboard-toolbar-note">{{ usuariosEmpresa.length }} usuario{{ usuariosEmpresa.length !== 1 ? 's' : '' }}</span>
              <button class="dashboard-refresh-button" type="button" (click)="loadUsuariosEmpresa()">Actualizar</button>
              <button
                class="dashboard-refresh-button"
                type="button"
                *ngIf="isSuperadminTenant"
                (click)="openNuevoUsuarioEmpresa()"
              >
                + Nuevo
              </button>
            </div>
          </div>

          <p *ngIf="isUsuariosEmpresaLoading" style="padding:1rem;color:#666;">Cargando usuarios...</p>
          <p *ngIf="!isUsuariosEmpresaLoading && !isSuperadminTenant" style="padding:0 1rem 1rem;color:#666;">
            Vista de solo lectura para tu rol. La creación y edición de usuarios queda reservada al SUPERADMIN_TENANT.
          </p>
          <p *ngIf="!isUsuariosEmpresaLoading && usuariosEmpresa.length === 0" style="padding:1rem;color:#666;">
            {{ isSuperadminTenant ? 'No hay usuarios registrados en esta empresa. Crea el primero con "+ Nuevo".' : 'No hay usuarios registrados en esta empresa.' }}
          </p>

          <!-- Formulario inline de usuario -->
          <div class="technician-form" *ngIf="showUsuarioEmpresaForm && isSuperadminTenant">
            <h3 style="margin-bottom:0.75rem;">{{ editingUsuarioEmpresaId ? 'Editar usuario' : 'Nuevo usuario' }}</h3>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
              <label class="technician-field">
                <span>Nombre completo *</span>
                <input
                  type="text"
                  [(ngModel)]="usuarioEmpresaForm.full_name"
                  (ngModelChange)="handleUsuarioEmpresaNameInput()"
                  placeholder="Nombre completo"
                  maxlength="160"
                />
              </label>
              <label class="technician-field">
                <span>Correo *</span>
                <input
                  type="email"
                  [(ngModel)]="usuarioEmpresaForm.email"
                  (ngModelChange)="handleUsuarioEmpresaEmailInput()"
                  placeholder="correo@empresa.com"
                  maxlength="160"
                  [disabled]="!!editingUsuarioEmpresaId"
                />
              </label>
              <label class="technician-field">
                <span>Teléfono</span>
                <input type="tel" [(ngModel)]="usuarioEmpresaForm.phone" placeholder="Teléfono" maxlength="40" />
              </label>
              <label class="technician-field">
                <span>Rol *</span>
                <select [(ngModel)]="usuarioEmpresaForm.role" (ngModelChange)="handleUsuarioEmpresaRoleChange()">
                  <option value="SUPERADMIN_TENANT">SUPERADMIN_TENANT</option>
                  <option value="ADMIN_SUCURSAL">ADMIN_SUCURSAL</option>
                  <option value="TECNICO">TECNICO</option>
                  <option value="CLIENTE">CLIENTE</option>
                </select>
              </label>
              <label class="technician-field">
                <span>Sucursal{{ usuarioEmpresaForm.role === 'ADMIN_SUCURSAL' ? ' *' : '' }}</span>
                <select [(ngModel)]="usuarioEmpresaForm.sucursal_id" (ngModelChange)="handleUsuarioEmpresaSucursalChange()">
                  <option *ngIf="usuarioEmpresaForm.role !== 'ADMIN_SUCURSAL'" [ngValue]="null">— Sin sucursal —</option>
                  <option *ngFor="let s of sucursales" [ngValue]="s.id">{{ s.nombre }}</option>
                </select>
              </label>
              <label class="technician-field" *ngIf="!editingUsuarioEmpresaId">
                <span>Contraseña *</span>
                <input type="password" [(ngModel)]="usuarioEmpresaForm.password" placeholder="Mínimo 6 caracteres" minlength="6" />
              </label>
            </div>
            <p
              *ngIf="usuarioEmpresaForm.role === 'ADMIN_SUCURSAL'"
              style="margin:0.85rem 0 0;color:#64748b;font-size:0.9rem;"
            >
              Selecciona la sucursal que administrará este usuario.
            </p>
            <p class="technician-feedback" *ngIf="usuariosEmpresaFeedback">{{ usuariosEmpresaFeedback }}</p>
            <div class="technician-form-actions">
              <button class="dashboard-refresh-button" type="button" (click)="saveUsuarioEmpresa()">
                {{ editingUsuarioEmpresaId ? 'Actualizar' : 'Crear' }}
              </button>
              <button class="dashboard-secondary-button" type="button" (click)="cancelUsuarioEmpresaForm()">Cancelar</button>
            </div>
          </div>

          <div class="dashboard-table-wrap" *ngIf="!isUsuariosEmpresaLoading && usuariosEmpresa.length > 0">
            <table class="dashboard-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre</th>
                  <th>Correo</th>
                  <th>Rol</th>
                  <th>Sucursal</th>
                  <th>Estado</th>
                  <th *ngIf="isSuperadminTenant">Opciones</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let usr of usuariosEmpresa">
                  <td data-label="ID"><span class="dashboard-id-chip">#{{ usr.id }}</span></td>
                  <td data-label="Nombre"><strong>{{ usr.full_name }}</strong></td>
                  <td data-label="Correo">{{ usr.email }}</td>
                  <td data-label="Rol">
                    <span class="dashboard-status-pill" style="background:rgba(66,133,244,0.12);color:#1a73e8;">
                      {{ usr.role }}
                    </span>
                  </td>
                  <td data-label="Sucursal">{{ usuarioEmpresaSucursalName(usr.sucursal_id) }}</td>
                  <td data-label="Estado">
                    <span class="dashboard-status-pill" [attr.data-status]="usr.estado === 'activo' ? 'activo' : 'rechazado'">
                      {{ usr.estado === 'activo' ? 'Activo' : 'Inactivo' }}
                    </span>
                  </td>
                  <td data-label="Opciones" *ngIf="isSuperadminTenant">
                    <div class="dashboard-table-actions">
                      <button class="dashboard-refresh-button" type="button" (click)="editUsuarioEmpresa(usr)">Editar</button>
                      <button
                        class="dashboard-danger-button"
                        type="button"
                        (click)="deleteUsuarioEmpresa(usr.id)"
                        [disabled]="usr.id === currentUserId"
                      >Eliminar</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>

      </section>
    </section>

      <div class="dashboard-modal-backdrop" *ngIf="showEmergencyModal && selectedMaintenanceRequest" (click)="closeEmergencyModal()">
        <section class="dashboard-modal-card emergency-modal-card" (click)="$event.stopPropagation()">
          <div class="dashboard-panel-head">
            <div>
              <p class="dashboard-panel-kicker">Emergencia seleccionada</p>
              <h2>{{ selectedMaintenanceRequest.code }}</h2>
            </div>
            <button class="dashboard-secondary-button" type="button" (click)="closeEmergencyModal()">
              Cerrar
            </button>
          </div>

          <section class="maintenance-map-card">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Mapa</p>
                <h2>Ubicación</h2>
              </div>
            </div>
            <div class="maintenance-map-shell">
              <div #emergencyMapCanvas class="maintenance-map-canvas" aria-label="Mapa de la emergencia"></div>
              <div class="maintenance-map-overlay" *ngIf="!selectedEmergencyHasCoordinates">
                La emergencia seleccionada no tiene coordenadas disponibles.
              </div>
            </div>
            <p
              class="maintenance-map-legend"
              *ngIf="selectedMaintenanceRequest.nearestWorkshopName && selectedEmergencyHasCoordinates"
            >
              Ruta visual entre el cliente y el taller asignado:
              <strong>{{ selectedMaintenanceRequest.nearestWorkshopName }}</strong>
            </p>

            <div class="emergency-detail-block emergency-tracking-block" *ngIf="selectedEmergencyTracking; else emergencyTrackingFallback">
              <strong>Seguimiento del auxilio</strong>
              <p>Distancia aproximada: {{ selectedEmergencyTracking.route.distance_text }}</p>
              <p>Tiempo estimado de llegada: {{ selectedEmergencyTracking.route.duration_text }}</p>
              <p>
                Ubicación del auxilio:
                {{ formatCoordinatePair(selectedEmergencyAuxilioLatitude, selectedEmergencyAuxilioLongitude) }}
              </p>
              <p *ngIf="selectedEmergencyTracking.technician.name; else workshopTrackingLabel">
                Auxilio en ruta: {{ selectedEmergencyTracking.technician.name }}
              </p>
              <ng-template #workshopTrackingLabel>
                <p>Auxilio en ruta: {{ selectedEmergencyTracking.workshop.name || selectedMaintenanceRequest.nearestWorkshopName }}</p>
              </ng-template>
              <p>Última actualización: {{ selectedEmergencyTrackingLastUpdateLabel }}</p>
            </div>
            <ng-template #emergencyTrackingFallback>
              <div class="emergency-detail-block emergency-tracking-block" *ngIf="emergencyTrackingFeedback">
                <strong>Seguimiento del auxilio</strong>
                <p>{{ emergencyTrackingFeedback }}</p>
              </div>
            </ng-template>
          </section>

          <section class="maintenance-detail-card">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Detalle de emergencia</p>
                <h2>{{ selectedMaintenanceRequest.code }}</h2>
              </div>
            </div>
            <div class="emergency-detail-grid">
              <p><strong>Cliente:</strong> {{ selectedMaintenanceRequest.client }}</p>
              <p><strong>Vehículo:</strong> {{ selectedMaintenanceRequest.vehicle }}</p>
              <p><strong>Ubicación:</strong> {{ selectedMaintenanceRequest.location }}</p>
              <p *ngIf="selectedMaintenanceRequest.nearestWorkshopName">
                <strong>Taller asignado:</strong> {{ selectedMaintenanceRequest.nearestWorkshopName }}
              </p>
              <p><strong>Prioridad:</strong> {{ selectedMaintenanceRequest.priority }}</p>
              <p><strong>Estado:</strong> {{ emergencyStatusLabel(selectedMaintenanceRequest.status) }}</p>
              <p><strong>Tipo reportado:</strong> {{ selectedMaintenanceRequest.problemType }}</p>
              <p *ngIf="selectedMaintenanceRequest.standardizedProblemType">
                <strong>Tipo estandarizado:</strong> {{ selectedMaintenanceRequest.standardizedProblemType }}
              </p>
              <p><strong>Servicio:</strong> {{ formatReportPrice(calculateReportServiceAmount(selectedMaintenanceRequest.price)) }}</p>
              <p><strong>Monto:</strong> {{ formatReportPrice(calculateReportNetAmount(selectedMaintenanceRequest.price)) }}</p>
            </div>

            <div class="emergency-detail-block">
              <strong>Resumen operativo</strong>
              <p>{{ selectedMaintenanceRequest.detail }}</p>
            </div>

            <div class="emergency-detail-block" *ngIf="selectedMaintenanceRequest.rejectionReason">
              <strong>Motivo de rechazo</strong>
              <p>{{ selectedMaintenanceRequest.rejectionReason }}</p>
              <span class="emergency-rejection-meta" *ngIf="selectedMaintenanceRequest.rejectedAt">
                Rechazada el {{ selectedMaintenanceRequest.rejectedAt | date: 'dd/MM/yyyy · HH:mm' }}
              </span>
            </div>

            <!-- ── CU22-B: Panel Técnico en Sitio ─────────────────────────── -->
            <div class="emergency-detail-block cu22-arrival-block"
              [class.cu22-arrival-confirmed]="selectedMaintenanceRequest.horaLlegada">
              <strong class="cu22-arrival-title">
                <span class="cu22-arrival-icon">📍</span>
                Llegada del técnico
              </strong>
              <ng-container *ngIf="selectedMaintenanceRequest.horaLlegada; else noArrival">
                <p class="cu22-arrival-status cu22-confirmed">Técnico en sitio</p>
                <p class="cu22-arrival-time">
                  Llegada registrada a las
                  <strong>{{ selectedMaintenanceRequest.horaLlegada | date: 'HH:mm' }}</strong>
                  del {{ selectedMaintenanceRequest.horaLlegada | date: 'dd/MM/yyyy' }}
                </p>
                <p *ngIf="selectedMaintenanceRequest.latitudLlegada != null && selectedMaintenanceRequest.longitudLlegada != null"
                  class="cu22-arrival-coords">
                  Coordenadas de llegada:
                  {{ selectedMaintenanceRequest.latitudLlegada | number: '1.4-6' }},
                  {{ selectedMaintenanceRequest.longitudLlegada | number: '1.4-6' }}
                  &nbsp;
                  <a class="cu22-coords-link"
                    [href]="'https://www.google.com/maps?q=' + selectedMaintenanceRequest.latitudLlegada + ',' + selectedMaintenanceRequest.longitudLlegada"
                    target="_blank" rel="noopener">Ver en mapa</a>
                </p>
                <p *ngIf="selectedMaintenanceRequest.assignedTechnicianName" class="cu22-arrival-tech">
                  Técnico: <strong>{{ selectedMaintenanceRequest.assignedTechnicianName }}</strong>
                </p>
                <p class="cu22-notification-badge cu22-notified">
                  ✓ Cliente notificado
                </p>
              </ng-container>
              <ng-template #noArrival>
                <p class="cu22-arrival-status cu22-pending">El técnico aún no confirmó llegada</p>
                <p class="cu22-arrival-hint">La confirmación se registra desde la app móvil del técnico.</p>
              </ng-template>
            </div>
            <!-- ── FIN CU22-B ──────────────────────────────────────────────── -->

            <div class="emergency-detail-block" *ngIf="selectedEmergencyWasReassigned">
              <strong>Solicitud reasignada automáticamente</strong>
              <p>Nuevo taller: {{ selectedMaintenanceRequest.nearestWorkshopName || 'Taller disponible' }}</p>
              <p>Estado actual: {{ emergencyStatusLabel(timelineCurrentStatus || selectedMaintenanceRequest.status) }}</p>
            </div>

            <div class="emergency-detail-block" *ngIf="selectedEmergencyNoAlternativeWorkshop">
              <strong>No se encontró otro taller disponible.</strong>
              <p>El cliente puede crear otra solicitud.</p>
            </div>

            <div class="emergency-detail-block emergency-timeline-block">
              <div class="emergency-timeline-head">
                <div>
                  <strong>Línea de estados del proceso</strong>
                  <p>Seguimiento operativo de la solicitud desde el dashboard web.</p>
                </div>
                <span
                  class="emergency-timeline-current"
                  [attr.data-status]="
                    timelineCurrentStatus === 'solicitud_cancelada'
                      ? 'rechazado'
                      : statusFilterGroup(timelineCurrentStatus || selectedMaintenanceRequest.status)
                  "
                >
                  {{ emergencyStatusLabel(timelineCurrentStatus || selectedMaintenanceRequest.status) }}
                </span>
              </div>

              <p class="emergency-empty-media" *ngIf="isEmergencyTimelineLoading">Cargando línea de tiempo...</p>

              <div class="emergency-timeline-scroll" *ngIf="!isEmergencyTimelineLoading">
                <div class="emergency-timeline-track">
                  <article
                    class="emergency-timeline-step"
                    *ngFor="let step of emergencyTimelineSteps"
                    [class.is-completed]="step.isCompleted"
                    [class.is-current]="step.isCurrent"
                    [class.is-cancelled]="step.isCancelled"
                  >
                    <div class="emergency-timeline-node">
                      <span>{{ step.icon }}</span>
                    </div>
                    <div class="emergency-timeline-copy">
                      <strong>{{ step.label }}</strong>
                      <span *ngIf="step.entry; else noStepDate">{{ step.entry.created_at | date: 'dd/MM/yyyy · HH:mm' }}</span>
                      <ng-template #noStepDate>
                        <span>Pendiente</span>
                      </ng-template>
                    </div>
                  </article>
                </div>
              </div>

              <div class="emergency-timeline-controls">
                <div class="technician-field technician-field-wide">
                  <span>Cambiar estado de solicitud</span>
                  <p class="emergency-timeline-controls-note">
                    Selecciona el siguiente paso del flujo para actualizar el estado sin salir del detalle.
                  </p>
                  <div class="emergency-timeline-options">
                    <button
                      type="button"
                      class="emergency-timeline-option"
                      *ngFor="let option of availableTimelineStatusOptions"
                      [class.is-selected]="selectedEmergencyNextTimelineStatus === option.value"
                      [disabled]="isUpdatingEmergencyTimelineStatus"
                      (click)="selectEmergencyTimelineStatusOption(option.value)"
                    >
                      {{ option.label }}
                    </button>
                  </div>
                  <label class="workshop-edit-field workshop-edit-field-wide emergency-rejection-field">
                    <span>Motivo de rechazo</span>
                    <textarea
                      name="emergencyRejectionReason"
                      [(ngModel)]="emergencyRejectionReason"
                      rows="3"
                      placeholder="Ej. No hay técnicos disponibles en este momento"
                    ></textarea>
                  </label>
                </div>
                <div class="emergency-timeline-actions">
                  <button
                    class="dashboard-refresh-button"
                    type="button"
                    (click)="updateSelectedEmergencyTimelineStatus()"
                    [disabled]="isUpdatingEmergencyTimelineStatus || !selectedEmergencyNextTimelineStatus"
                  >
                    {{ isUpdatingEmergencyTimelineStatus ? 'Actualizando...' : 'Confirmar cambio' }}
                  </button>
                  <button
                    class="dashboard-danger-button"
                    type="button"
                    (click)="rejectSelectedEmergency()"
                    [disabled]="isRejectingEmergency || isEmergencyRejected"
                  >
                    {{ isRejectingEmergency ? 'Rechazando...' : 'Rechazar solicitud' }}
                  </button>
                </div>
              </div>

              <p class="technician-form-feedback" *ngIf="emergencyTimelineFeedback">
                {{ emergencyTimelineFeedback }}
              </p>

              <div class="emergency-timeline-history" *ngIf="selectedEmergencyTimeline?.timeline?.length; else emptyTimelineHistory">
                <strong>Historial del proceso</strong>
                <div class="emergency-timeline-history-list">
                  <article class="emergency-timeline-history-item" *ngFor="let item of selectedEmergencyTimeline?.timeline">
                    <div class="emergency-timeline-history-dot"></div>
                    <div class="emergency-timeline-history-copy">
                      <strong>{{ timelineHistoryTitle(item) }}</strong>
                      <span>{{ item.created_at | date: 'dd/MM/yyyy · HH:mm' }}</span>
                      <span *ngIf="item.observation">
                        {{ timelineHistoryObservationLabel(item) ? timelineHistoryObservationLabel(item) + ' ' : '' }}{{ item.observation }}
                      </span>
                      <span *ngIf="item.changed_by_role">
                        Responsable: {{ formatTimelineActor(item.changed_by_role, item.changed_by_user_id) }}
                      </span>
                    </div>
                  </article>
                </div>
              </div>
              <ng-template #emptyTimelineHistory>
                <div class="emergency-timeline-history is-empty">
                  <strong>Historial del proceso</strong>
                  <p class="emergency-empty-media">Aun no hay eventos adicionales registrados para esta solicitud.</p>
                </div>
              </ng-template>
            </div>

            <div class="emergency-detail-block" *ngIf="selectedMaintenanceRequest.clientDescription">
              <strong>Descripción escrita por el cliente</strong>
              <p>{{ selectedMaintenanceRequest.clientDescription }}</p>
            </div>

            <div class="emergency-detail-block" *ngIf="selectedMaintenanceRequest.audioTranscript">
              <strong>Transcripción del audio</strong>
              <p>{{ selectedMaintenanceRequest.audioTranscript }}</p>
            </div>

            <div class="emergency-detail-block">
              <strong>Audio enviado</strong>
              <audio
                *ngIf="selectedMaintenanceRequest.audioUrl; else noEmergencyAudio"
                controls
                [src]="selectedMaintenanceRequest.audioUrl"
                class="emergency-audio-player"
              ></audio>
              <ng-template #noEmergencyAudio>
                <p class="emergency-empty-media">Esta emergencia no incluye audio.</p>
              </ng-template>
            </div>

            <div class="emergency-detail-block">
              <strong>Imágenes enviadas por el cliente</strong>
              <div class="emergency-photo-grid" *ngIf="selectedMaintenancePhotoUrls.length; else noEmergencyPhotos">
                <a
                  class="emergency-photo-item"
                  *ngFor="let photoUrl of selectedMaintenancePhotoUrls"
                  [href]="photoUrl"
                  target="_blank"
                  rel="noreferrer"
                >
                  <img [src]="photoUrl" alt="Imagen enviada por el cliente para la emergencia" />
                </a>
              </div>
              <ng-template #noEmergencyPhotos>
                <p class="emergency-empty-media">Esta emergencia no incluye imágenes.</p>
              </ng-template>
            </div>

            <div class="emergency-detail-block emergency-assignment-block" *ngIf="isWorkshopSession">
              <strong>Asignación de técnico</strong>
              <div
                class="emergency-assigned-technician"
                *ngIf="selectedMaintenanceRequest.assignedTechnicianName; else noAssignedTechnician"
              >
                <p>
                  Técnico asignado:
                  <strong>{{ selectedMaintenanceRequest.assignedTechnicianName }}</strong>
                  <span *ngIf="selectedMaintenanceRequest.assignedTechnicianPhone">
                    · {{ selectedMaintenanceRequest.assignedTechnicianPhone }}
                  </span>
                </p>
                <button
                  class="technician-inline-button"
                  type="button"
                  *ngIf="statusFilterGroup(selectedMaintenanceRequest.status) === 'activo' && !isEditingEmergencyAssignment"
                  (click)="startEmergencyAssignmentEdit()"
                >
                  Editar
                </button>
              </div>
              <ng-template #noAssignedTechnician>
                <p>
                  {{
                    statusFilterGroup(selectedMaintenanceRequest.status) === 'activo'
                      ? 'Selecciona un técnico disponible para enviar asistencia.'
                      : 'Primero acepta la emergencia para habilitar la asignación.'
                  }}
                </p>
              </ng-template>

              <div
                class="emergency-assignment-controls"
                *ngIf="
                  statusFilterGroup(selectedMaintenanceRequest.status) === 'activo' &&
                  (!selectedMaintenanceRequest.assignedTechnicianId || isEditingEmergencyAssignment)
                "
              >
                <label class="technician-field">
                  <span>Técnico disponible</span>
                  <select [(ngModel)]="selectedEmergencyTechnicianId" name="selectedEmergencyTechnicianId">
                    <option [ngValue]="null">Seleccionar técnico</option>
                    <option *ngFor="let technician of assignableTechnicians" [ngValue]="technician.id">
                      {{ technician.full_name }} · {{ technician.specialty }} · {{ statusLabel(technician.status) }}
                    </option>
                  </select>
                </label>
                <button
                  class="dashboard-refresh-button"
                  type="button"
                  (click)="assignSelectedEmergencyTechnician()"
                  [disabled]="isAssigningEmergencyTechnician || !selectedEmergencyTechnicianId"
                >
                  {{ isAssigningEmergencyTechnician ? 'Asignando...' : 'Asignar técnico' }}
                </button>
                <button
                  class="dashboard-secondary-button"
                  type="button"
                  *ngIf="selectedMaintenanceRequest.assignedTechnicianId"
                  (click)="cancelEmergencyAssignmentEdit()"
                  [disabled]="isAssigningEmergencyTechnician"
                >
                  Cancelar
                </button>
              </div>

              <p class="technician-form-feedback" *ngIf="emergencyAssignmentFeedback">
                {{ emergencyAssignmentFeedback }}
              </p>
            </div>
          </section>

          <div class="emergency-modal-actions">
            <ng-container *ngIf="isWorkshopSession; else adminEmergencyActions">
              <button
                class="dashboard-refresh-button"
                type="button"
                *ngIf="statusFilterGroup(selectedMaintenanceRequest.status) === 'pendiente'"
                (click)="updateSelectedEmergencyStatus('activo')"
                [disabled]="isUpdatingEmergencyStatus"
              >
                {{ isUpdatingEmergencyStatus ? 'Actualizando...' : 'Aceptar' }}
              </button>
              <button
                class="client-delete-confirm-button"
                type="button"
                (click)="updateSelectedEmergencyStatus('rechazado')"
                [disabled]="isUpdatingEmergencyStatus"
              >
                Rechazar
              </button>
            </ng-container>
            <ng-template #adminEmergencyActions>
              <button
                class="client-delete-confirm-button"
                type="button"
                (click)="updateSelectedEmergencyStatus('rechazado')"
                [disabled]="isUpdatingEmergencyStatus"
              >
                Rechazar
              </button>
              <button
                class="dashboard-danger-button"
                type="button"
                (click)="deleteSelectedEmergency()"
                [disabled]="isUpdatingEmergencyStatus"
              >
                Eliminar
              </button>
            </ng-template>
            <button
              class="dashboard-secondary-button"
              type="button"
              (click)="closeEmergencyModal()"
              [disabled]="isUpdatingEmergencyStatus"
            >
              Cancelar
            </button>
          </div>
        </section>
      </div>
    </main>
  `,
  styleUrl: '../shared/shared-pages.css',
})
export class DashboardPageComponent implements OnDestroy {
  readonly technicianSpecialtyOptions = TECHNICIAN_SPECIALTY_OPTIONS;
  readonly workshopZoneOptions = WORKSHOP_ZONE_OPTIONS;
  readonly workshopSpecialtyOptions = WORKSHOP_SPECIALTY_OPTIONS;
  readonly sucursalZoneOptions = SUCURSAL_ZONE_OPTIONS;
  readonly sucursalSpecialtyOptions = SUCURSAL_SPECIALTY_OPTIONS;
  readonly isSecureContext = typeof window !== 'undefined' ? window.isSecureContext : false;
  private readonly http = inject(HttpClient);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly router = inject(Router);
  private readonly realtimeService = inject(RealtimeService);
  private readonly workshopsApiUrl = `${API_BASE_URL}/workshops`;
  private readonly techniciansApiUrl = `${API_BASE_URL}/technicians`;
  private readonly clientsApiUrl = `${API_BASE_URL}/clientes`;
  private readonly emergenciesApiUrl = `${API_BASE_URL}/emergencias`;
  private readonly dashboardOverviewApiUrl = `${API_BASE_URL}/dashboard/operational-overview`;
  private readonly tenantsApiUrl = `${API_BASE_URL}/tenants`;
  private readonly backendBaseUrl = BACKEND_BASE_URL;
  private readonly appSessionStorageKey = APP_SESSION_STORAGE_KEY;
  private readonly dashboardSidebarStorageKey = 'dashboard.sidebar.collapsed';
  private readonly emergencyRefreshMs = 15000;
  private readonly realtimeRefreshDebounceMs = 1000;
  private emergencyRefreshTimer: number | null = null;
  private realtimeRefreshTimer: number | null = null;
  private pendingRealtimeRefresh: Required<RealtimeRefreshRequest> = {
    overview: false,
    emergencies: false,
    quotationRequests: false,
    quotationHistory: false,
    contractedServices: false,
    tracking: false,
  };

  readonly requests: DashboardItem[] = [
    {
      title: 'Cambio de bateria',
      subtitle: 'Cliente en Equipetrol, Santa Cruz',
      meta: 'Hace 8 min',
      priority: 'Alta',
    },
    {
      title: 'Remolque urbano',
      subtitle: 'Vehiculo detenido en Av. Banzer',
      meta: 'Hace 12 min',
      priority: 'Media',
    },
    {
      title: 'Falta de combustible',
      subtitle: 'Solicitud desde zona sur',
      meta: 'Hace 21 min',
      priority: 'Seguimiento',
    },
  ];

  maintenanceRequests: MaintenanceRequest[] = [];
  emergenciesFeedback = '';
  lastSeenPendingEmergencyId = 0;

  maintenanceSearch = '';
  maintenanceFilter: MaintenanceFilter = 'todas';
  selectedMaintenanceRequestId: number | null = null;
  selectedEmergencyTechnicianId: number | null = null;
  selectedEmergencyTimeline: EmergencyTimelineResponse | null = null;
  selectedEmergencyTracking: EmergencyTrackingResponse | null = null;
  selectedEmergencyNextTimelineStatus: EmergencyTimelineStatus | null = null;
  isEditingEmergencyAssignment = false;

  selectedSection: DashboardSection = 'dashboard';
  isSidebarCollapsed = false;
  isExportingReport = false;
  workshops: WorkshopRegistration[] = [];
  technicians: Technician[] = [];
  clients: Client[] = [];
  tenants: TenantRecord[] = [];
  operationalOverview: DashboardOperationalOverview | null = null;
  isLoading = true;
  isTenantsLoading = false;
  isSavingTenant = false;
  showTenantForm = false;
  editingTenantId: number | null = null;
  tenantFeedback = '';
  tenantForm: { nombre: string; descripcion: string; estado: string } = { nombre: '', descripcion: '', estado: 'activo' };
  isTechniciansLoading = true;
  isClientsLoading = true;
  isEmergenciesLoading = true;
  isOperationalOverviewLoading = false;
  isEmergencyTimelineLoading = false;
  isEmergencyTrackingLoading = false;
  isUpdatingEmergencyStatus = false;
  isUpdatingEmergencyTimelineStatus = false;
  isRejectingEmergency = false;
  isAssigningEmergencyTechnician = false;
  isSavingTechnician = false;
  isSavingWorkshop = false;
  isUpdatingWorkshopApproval = false;
  isSavingClient = false;
  editingTechnicianId: number | null = null;
  editingWorkshopId: number | null = null;
  editingClientId: number | null = null;
  technicianFeedback = '';
  emergencyAssignmentFeedback = '';
  emergencyTimelineFeedback = '';
  emergencyTrackingFeedback = '';
  emergencyRejectionReason = '';
  workshopEditFeedback = '';
  clientEditFeedback = '';
  technicianFilter: TechnicianFilter = 'activos';
  showTechnicianForm = false;
  showWorkshopEditModal = false;
  showClientEditModal = false;
  showClientDeleteModal = false;
  workshopsPage = 1;
  readonly workshopsPageSize = 15;
  private readonly adminSession: AppSession | null = this.readAdminSession();
  private realtimeSubscriptions = new Subscription();
  realtimeConnectionState: ConnectionState = 'idle';
  realtimeEventCount = 0;
  private resolvedWorkshopId: number | null = null;
  private isResolvingWorkshopContext = false;
  clientPendingDelete: Client | null = null;
  showEmergencyModal = false;
  private emergencyMap?: any;
  private emergencyMapMarkersLayer?: any;
  private emergencyMapResizeTimer?: number;
  private workshopEditMap?: any;
  private workshopEditMapMarker?: any;
  private workshopEditMapResizeTimer?: number;
  private workshopEditMapHost?: HTMLDivElement;
  private sucursalMap?: any;
  private sucursalMapMarker?: any;
  private sucursalMapResizeTimer?: number;
  private sucursalMapHost?: HTMLDivElement;
  private sucursalesOverviewMap?: any;
  private sucursalesOverviewMarkers: any[] = [];
  private sucursalesOverviewMapResizeTimer?: number;
  private sucursalesOverviewMapHost?: HTMLDivElement;
  isWorkshopLocationLocating = false;
  workshopLocationMessage = '';
  selectedSyncRecordId: number | null = null;
  syncTab: SyncTab = 'errors';
  selectedSyncErrorRecordId: number | null = null;
  quotationRequests: QuotationRequest[] = [];
  quotationOffers: QuotationOffer[] = [];
  contractedServices: ContractedService[] = [];
  isQuotationRequestsLoading = false;
  isQuotationHistoryLoading = false;
  isContractedServicesLoading = false;
  selectedContractedService: ContractedService | null = null;
  contractedServicesView: 'list' | 'detail' = 'list';
  selectedContractedTechnicianId: number | null = null;
  isAssigningContractedTechnician = false;
  isUpdatingContractedStatus = false;
  contractedAssignmentFeedback = '';
  quotationView: 'list' | 'detail' | 'offer_form' | 'confirmation' = 'list';
  selectedQuotationRequest: QuotationRequest | null = null;
  selectedQuotationEmergency: EmergencyReport | null = null;
  isQuotationEmergencyLoading = false;
  quotationEmergencyPhotoUrls: string[] = [];
  quotationEmergencyAudioUrl: string | null = null;
  quotationEmergencyMapEmbedUrl: SafeResourceUrl | null = null;
  quotationEmergencyMapExternalUrl: string | null = null;
  quotationOfferForm: QuotationOfferFormModel = this.createEmptyQuotationOfferForm();
  isSubmittingOffer = false;
  quotationOfferFeedback = '';
  lastSubmittedOffer: QuotationOffer | null = null;
  selectedWorkshopOffer: QuotationOffer | null = null;
  selectedQuotationOffers: QuotationOffer[] = [];

  // ── TENANT: Sucursales ──────────────────────────────────────────────────────
  sucursales: SucursalRecord[] = [];
  isSucursalesLoading = false;
  sucursalesFeedback = '';
  showSucursalForm = false;
  editingSucursalId: number | null = null;
  sucursalForm: SucursalFormModel = this.createEmptySucursalForm();
  isSucursalLocationLocating = false;
  isSucursalReverseGeocoding = false;
  sucursalLocationMessage = '';
  sucursalDetectedAddress = '';
  private sucursalAddressTouchedManually = false;
  private sucursalLastAutofilledAddress = '';

  // ── TENANT: Usuarios de la empresa ─────────────────────────────────────────
  usuariosEmpresa: UsuarioEmpresaRecord[] = [];
  isUsuariosEmpresaLoading = false;
  usuariosEmpresaFeedback = '';
  showUsuarioEmpresaForm = false;
  editingUsuarioEmpresaId: number | null = null;
  usuarioEmpresaForm: UsuarioEmpresaFormModel = this.createEmptyUsuarioEmpresaForm();
  private usuarioEmpresaNameTouchedManually = false;
  private usuarioEmpresaEmailTouchedManually = false;

  @ViewChild('emergencyMapCanvas')
  set emergencyMapCanvas(element: ElementRef<HTMLDivElement> | undefined) {
    if (!element || typeof window === 'undefined') {
      return;
    }

    window.setTimeout(() => {
      this.initializeEmergencyMap(element.nativeElement);
      this.renderSelectedEmergencyMap();
    });
  }

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

  @ViewChild('sucursalMapCanvas')
  set sucursalMapCanvas(element: ElementRef<HTMLDivElement> | undefined) {
    if (!element || typeof window === 'undefined' || !this.showSucursalForm) {
      return;
    }

    window.setTimeout(() => {
      this.initializeSucursalMap(element.nativeElement);
      this.renderSucursalMap();
    });
  }

  @ViewChild('sucursalesOverviewMapCanvas')
  set sucursalesOverviewMapCanvas(element: ElementRef<HTMLDivElement> | undefined) {
    if (!element || typeof window === 'undefined' || this.selectedSection !== 'sucursales') {
      return;
    }

    window.setTimeout(() => {
      this.initializeSucursalesOverviewMap(element.nativeElement);
      this.renderSucursalesOverviewMap();
    });
  }

  technicianForm: TechnicianFormModel = this.createEmptyTechnicianForm();
  workshopForm: WorkshopFormModel = this.createEmptyWorkshopForm();
  clientForm: ClientFormModel = this.createEmptyClientForm();

  stats: DashboardStat[] = [
    {
      label: 'Solicitudes hoy',
      value: '0',
      detail: 'Pendiente de cargar desde PostgreSQL.',
      trend: 'Live',
      tone: 'gold',
    },
    {
      label: 'Talleres registrados',
      value: '0',
      detail: 'Registros creados desde el formulario publico.',
      trend: 'Actual',
      tone: 'blue',
    },
    {
      label: 'Tecnicos disponibles',
      value: '0',
      detail: 'Personal listo para atender solicitudes inmediatas.',
      trend: 'Equipo',
      tone: 'teal',
    },
    {
      label: 'Clientes activos',
      value: '0',
      detail: 'Usuarios listos para iniciar sesion desde la app movil.',
      trend: 'App',
      tone: 'blue',
    },
    {
      label: 'Cobertura',
      value: '0 zonas',
      detail: 'Ciudad, periferia y rutas con respuesta coordinada.',
      trend: 'Expandible',
      tone: 'slate',
    },
  ];

  constructor() {
    this.isSidebarCollapsed = this.readSidebarCollapsedState();
    this.selectedSection = this.defaultSection;

    if (this.isWorkshopSession) {
      this.maintenanceFilter = 'pendiente';
      this.resolveWorkshopContext();
    }

    this.loadOperationalOverview();
    this.loadWorkshops();
    this.loadTechnicians();
    this.loadClients();
    this.loadEmergencies();
    this.startEmergencyRefresh();
    this.initializeRealtime();
  }

  ngOnDestroy(): void {
    this.realtimeSubscriptions.unsubscribe();
    this.realtimeService.disconnect();
    this.stopEmergencyRefresh();
    this.clearRealtimeRefreshTimer();

    if (typeof window !== 'undefined' && this.emergencyMapResizeTimer !== undefined) {
      window.clearTimeout(this.emergencyMapResizeTimer);
    }

    if (typeof window !== 'undefined' && this.workshopEditMapResizeTimer !== undefined) {
      window.clearTimeout(this.workshopEditMapResizeTimer);
    }

    if (typeof window !== 'undefined' && this.sucursalMapResizeTimer !== undefined) {
      window.clearTimeout(this.sucursalMapResizeTimer);
    }

    if (typeof window !== 'undefined' && this.sucursalesOverviewMapResizeTimer !== undefined) {
      window.clearTimeout(this.sucursalesOverviewMapResizeTimer);
    }

    if (this.emergencyMap) {
      this.emergencyMap.remove();
      this.emergencyMap = undefined;
      this.emergencyMapMarkersLayer = undefined;
    }

    this.destroyWorkshopEditMap();
    this.destroySucursalMap();
    this.destroySucursalesOverviewMap();
  }

  get sectionTitle(): string {
    if (this.selectedSection === 'technicians') {
      return 'Gestion de Tecnicos';
    }

    if (this.selectedSection === 'clients') {
      return 'Gestion de Clientes';
    }

    if (this.selectedSection === 'workshops') {
      return this.isGlobalAdminSession ? 'Solicitudes de Empresas' : 'Gestion de Solicitudes';
    }

    if (this.selectedSection === 'maintenance') {
      return 'Mantenimiento';
    }

    if (this.selectedSection === 'emergencies') {
      return 'Solicitudes de emergencia';
    }

    if (this.selectedSection === 'reports') {
      return 'Reportes';
    }

    if (this.selectedSection === 'audit') {
      return 'Bitacora';
    }

    if (this.selectedSection === 'sync') {
      return 'Sincronización offline';
    }

    if (this.selectedSection === 'quotation_requests') {
      return this.isTenantQuotationSession ? 'Solicitudes de cotización' : 'Solicitudes recibidas';
    }

    if (this.selectedSection === 'quotation_history') {
      return this.isTenantQuotationSession ? 'Historial de cotizaciones' : 'Mis cotizaciones';
    }

    if (this.selectedSection === 'contracted_services') {
      return 'Servicios contratados';
    }

    if (this.selectedSection === 'tenants') {
      return 'Organizaciones';
    }

    if (this.selectedSection === 'sucursales') {
      return 'Mis Sucursales';
    }

    if (this.selectedSection === 'usuarios_empresa') {
      return 'Usuarios de mi Empresa';
    }

    return 'Resumen general';
  }

  get userDisplayName(): string {
    return this.adminSession?.fullName?.trim() || 'Administrador';
  }

  get isWorkshopSession(): boolean {
    return this.adminSession?.role === 'workshop';
  }

  get isGlobalAdminSession(): boolean {
    return isGlobalAdmin(this.adminSession?.role ?? '');
  }

  get isTenantSession(): boolean {
    return isTenantRole(this.adminSession?.role ?? '');
  }

  get isSuperadminTenant(): boolean {
    return isTenantSuperadmin(this.adminSession?.role ?? '');
  }

  get isAdminSucursalSession(): boolean {
    return isSucursalAdmin(this.adminSession?.role ?? '');
  }

  get isTecnicoSession(): boolean {
    return isTechnicianRole(this.adminSession?.role ?? '');
  }

  get currentUserId(): number | null {
    return this.adminSession?.id ?? null;
  }

  get tenantDisplayName(): string {
    return this.adminSession?.fullName?.trim() || 'Mi Empresa';
  }

  get defaultSection(): DashboardSection {
    return 'dashboard';
  }

  get tenantAuthHeaders(): Record<string, string> {
    const token = this.adminSession?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  get currentWorkshopId(): number | null {
    if (!this.isWorkshopSession) {
      return null;
    }

    return this.resolvedWorkshopId ?? this.adminSession?.id ?? null;
  }

  get isTenantQuotationSession(): boolean {
    return this.isSuperadminTenant || this.isAdminSucursalSession;
  }

  get sucursalesOverviewData(): SucursalRecord[] {
    return this.sucursales.filter((sucursal) => this.shouldIncludeSucursalInOverview(sucursal));
  }

  get isGlobalSaasOverview(): boolean {
    return this.operationalOverview?.scope === 'global_saas';
  }

  get showComparativeOperationalPanels(): boolean {
    const scope = this.operationalOverview?.scope ?? '';
    return !this.isWorkshopSession && ['tenant', 'sucursal', 'global'].includes(scope);
  }

  get showRecentOperationalPanel(): boolean {
    return this.operationalOverview?.scope !== 'global_saas';
  }

  get showOperationalAnalyticsPanel(): boolean {
    return this.showRecentOperationalPanel && !!this.operationalOverview?.analytics_summary?.length;
  }

  get overviewHeroKicker(): string {
    if (this.isWorkshopSession) {
      return 'Tenant operativo';
    }

    if (this.isGlobalSaasOverview) {
      return 'Control SaaS';
    }

    return 'Control multitenant';
  }

  get overviewHeroTitle(): string {
    if (this.isWorkshopSession) {
      return 'Operación del Taller';
    }

    if (this.isGlobalSaasOverview) {
      return 'Vista Global de Tenants';
    }

    return 'Vista Global del Sistema';
  }

  get statusPanelKicker(): string {
    return this.isGlobalSaasOverview ? 'Estado de tenants' : 'Estados del proceso';
  }

  get statusPanelTitle(): string {
    if (this.isWorkshopSession) {
      return 'Pipeline del Taller';
    }

    return this.isGlobalSaasOverview ? 'Distribución SaaS' : 'Distribución Global';
  }

  get statusPanelEmptyMessage(): string {
    return this.isGlobalSaasOverview
      ? 'Todavía no hay estados de tenants para mostrar.'
      : 'Todavía no hay estados operativos para mostrar.';
  }

  get recentPanelTitle(): string {
    return this.isWorkshopSession ? 'Solicitudes Recientes del Taller' : 'Últimas Emergencias del Sistema';
  }

  statusPanelItemDetail(count: number): string {
    return this.isGlobalSaasOverview
      ? `${count} tenants registrados en esta categoría.`
      : `${count} solicitudes registradas en este estado.`;
  }

  formatAnalyticsMinutes(value: number | null): string {
    return typeof value === 'number' ? `${Math.round(value)} min` : 'Sin datos';
  }

  formatAnalyticsPercent(value: number | null): string {
    return typeof value === 'number' ? `${value.toFixed(1)}%` : 'No disponible';
  }

  canAccessSection(section: DashboardSection): boolean {
    if (section === 'workshops') {
      return false;
    }

    if (this.isTenantSession) {
      if (this.isSuperadminTenant) {
        return [
          'dashboard',
          'sucursales',
          'usuarios_empresa',
          'technicians',
          'clients',
          'emergencies',
          'reports',
          'quotation_requests',
          'quotation_history',
          'contracted_services',
        ].includes(section);
      }

      if (this.isAdminSucursalSession) {
        return [
          'dashboard',
          'sucursales',
          'usuarios_empresa',
          'technicians',
          'clients',
          'emergencies',
          'reports',
          'quotation_requests',
          'quotation_history',
          'contracted_services',
        ].includes(section);
      }

      if (this.isTecnicoSession) {
        return ['dashboard', 'technicians', 'emergencies', 'reports'].includes(section);
      }

      return ['dashboard', 'emergencies', 'reports'].includes(section);
    }

    if (!this.isWorkshopSession) {
      // Admin global: accede a todo excepto secciones tenant
      return section !== 'technicians' && section !== 'tenants' && section !== 'sucursales' && section !== 'usuarios_empresa'
        ? true
        : section === 'tenants' && isGlobalAdmin(this.adminSession?.role ?? '');
    }

    // Sesión workshop legacy
    return section === 'dashboard' || section === 'technicians' || section === 'emergencies' || section === 'reports' || section === 'sync' || section === 'quotation_requests' || section === 'quotation_history' || section === 'contracted_services';
  }

  get maintenanceRequestsFiltered(): MaintenanceRequest[] {
    return this.maintenanceRequests.filter((request) => {
      const matchesSearch = [request.code, request.client, request.vehicle, request.location, request.detail]
        .some((value) => value.toLowerCase().includes(this.maintenanceSearch.toLowerCase()));
      const statusGroup = this.statusFilterGroup(request.status);
      const matchesFilter =
        this.maintenanceFilter === 'todas' ||
        (this.maintenanceFilter === 'historial' && statusGroup !== 'pendiente') ||
        statusGroup === this.maintenanceFilter;
      return matchesSearch && matchesFilter;
    });
  }

  get selectedMaintenanceRequest(): MaintenanceRequest | null {
    return this.maintenanceRequests.find((request) => request.id === this.selectedMaintenanceRequestId) ?? null;
  }

  get assignableTechnicians(): Technician[] {
    const assignedTechnicianId = this.selectedMaintenanceRequest?.assignedTechnicianId ?? null;

    return this.technicians.filter(
      (technician) => technician.status === 'disponible' || technician.id === assignedTechnicianId,
    );
  }

  get maintenanceSummaryCounts(): { label: string; value: number }[] {
    return [
      { label: 'Urgentes', value: this.maintenanceRequests.filter((request) => request.priority === 'Alta').length },
      {
        label: 'Pendientes',
        value: this.maintenanceRequests.filter((request) => this.statusFilterGroup(request.status) === 'pendiente').length,
      },
      {
        label: 'Activas',
        value: this.maintenanceRequests.filter((request) => this.statusFilterGroup(request.status) === 'activo').length,
      },
    ];
  }

  get pendingEmergencyNotifications(): number {
    return this.maintenanceRequests.filter(
      (request) => this.statusFilterGroup(request.status) === 'pendiente' && request.id > this.lastSeenPendingEmergencyId,
    ).length;
  }

  get reportWorkRequests(): MaintenanceRequest[] {
    return this.maintenanceRequests.filter((request) => this.statusFilterGroup(request.status) === 'activo');
  }

  get reportTotalServiceAmount(): number {
    return this.reportWorkRequests.reduce(
      (total, request) => total + (this.calculateReportServiceAmount(request.price) ?? 0),
      0,
    );
  }

  get reportTotalNetAmount(): number {
    return this.reportWorkRequests.reduce(
      (total, request) => total + (this.calculateReportNetAmount(request.price) ?? 0),
      0,
    );
  }

  get reportWorkshopName(): string {
    return this.isWorkshopSession ? this.userDisplayName : 'Todos los talleres';
  }

  get reportGeneratedAt(): Date {
    return new Date();
  }

  get isAuditLoading(): boolean {
    return this.isEmergenciesLoading || this.isTechniciansLoading || (!this.isWorkshopSession && (this.isLoading || this.isClientsLoading));
  }

  get auditItems(): AuditItem[] {
    const items: AuditItem[] = [];

    for (const request of this.maintenanceRequests) {
      items.push({
        title: `${request.code} registrada`,
        detail: `${request.client} solicito atencion para ${request.vehicle}.`,
        meta: `${request.problemType} · ${request.location}`,
        createdAt: request.createdAt,
        tone:
          this.statusFilterGroup(request.status) === 'rechazado'
            ? 'danger'
            : this.statusFilterGroup(request.status) === 'activo'
              ? 'success'
              : 'warning',
      });

      if (this.statusFilterGroup(request.status) === 'activo') {
        items.push({
          title: `${request.code} aceptada`,
          detail: `${request.nearestWorkshopName || this.reportWorkshopName} acepto la emergencia.`,
          meta: request.assignedTechnicianName
            ? `Tecnico asignado: ${request.assignedTechnicianName}`
            : 'Pendiente de asignacion tecnica',
          createdAt: request.createdAt,
          tone: 'success',
        });
      }

      if (this.statusFilterGroup(request.status) === 'rechazado') {
        items.push({
          title: `${request.code} rechazada`,
          detail: `${request.nearestWorkshopName || this.reportWorkshopName} rechazo la solicitud.`,
          meta: request.problemType,
          createdAt: request.createdAt,
          tone: 'danger',
        });
      }
    }

    for (const technician of this.technicians) {
      items.push({
        title: `Tecnico ${this.statusLabel(technician.status).toLowerCase()}`,
        detail: technician.full_name,
        meta: `${technician.specialty} · ${technician.phone}`,
        createdAt: technician.updated_at || technician.created_at,
        tone: technician.status === 'disponible' ? 'success' : technician.status === 'ocupado' ? 'warning' : 'info',
      });
    }

    if (!this.isWorkshopSession) {
      for (const workshop of this.workshops) {
        items.push({
          title: `Taller ${this.workshopApprovalLabel(workshop.approval_status).toLowerCase()}`,
          detail: workshop.workshop_name,
          meta: `${workshop.zone} · ${workshop.specialty}`,
          createdAt: workshop.created_at,
          tone:
            workshop.approval_status === 'activo'
              ? 'success'
              : workshop.approval_status === 'rechazado'
                ? 'danger'
                : 'warning',
        });
      }

      for (const client of this.clients) {
        items.push({
          title: `Cliente ${this.clientStatusLabel(client.status).toLowerCase()}`,
          detail: client.full_name,
          meta: `${client.email} · ${client.phone}`,
          createdAt: client.updated_at || client.created_at,
          tone: client.status === 'active' ? 'success' : 'warning',
        });
      }
    }

    return items
      .filter((item) => !Number.isNaN(new Date(item.createdAt).getTime()))
      .sort((first, second) => new Date(second.createdAt).getTime() - new Date(first.createdAt).getTime())
      .slice(0, 80);
  }

  get auditLatestLabel(): string {
    const latest = this.auditItems[0];

    if (!latest) {
      return 'Sin eventos';
    }

    return this.relativeTimeLabel(latest.createdAt);
  }

  selectMaintenanceRequest(request: MaintenanceRequest): void {
    this.selectedMaintenanceRequestId = request.id;
    this.selectedEmergencyTechnicianId = request.assignedTechnicianId;
    this.isEditingEmergencyAssignment = false;
    this.emergencyAssignmentFeedback = '';
    this.emergencyTimelineFeedback = '';
    this.emergencyRejectionReason = request.rejectionReason ?? '';
    this.showEmergencyModal = true;
    this.loadSelectedEmergencyTimeline();
    this.loadSelectedEmergencyTracking();
    this.renderSelectedEmergencyMap();
  }

  setMaintenanceFilter(filter: MaintenanceFilter): void {
    this.maintenanceFilter = filter;
  }

  clearMaintenanceSearch(): void {
    this.maintenanceSearch = '';
    this.maintenanceFilter = this.isWorkshopSession ? 'pendiente' : 'todas';
  }

  exportReportsPdf(): void {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      return;
    }

    const previousTitle = document.title;
    this.isExportingReport = true;
    document.title = `Reporte trabajos realizados - ${this.reportWorkshopName}`;

    window.setTimeout(() => {
      window.print();
      document.title = previousTitle;
      this.isExportingReport = false;
    });
  }

  refreshAudit(): void {
    this.loadEmergencies();
    this.loadTechnicians();

    if (!this.isWorkshopSession) {
      this.loadWorkshops();
      this.loadClients();
    }
  }

  closeEmergencyModal(): void {
    this.showEmergencyModal = false;
    this.selectedEmergencyTechnicianId = null;
    this.selectedEmergencyTimeline = null;
    this.selectedEmergencyTracking = null;
    this.selectedEmergencyNextTimelineStatus = null;
    this.isEditingEmergencyAssignment = false;
    this.emergencyAssignmentFeedback = '';
    this.emergencyTimelineFeedback = '';
    this.emergencyTrackingFeedback = '';
    this.emergencyRejectionReason = '';
  }

  startEmergencyAssignmentEdit(): void {
    this.selectedEmergencyTechnicianId = this.selectedMaintenanceRequest?.assignedTechnicianId ?? null;
    this.isEditingEmergencyAssignment = true;
    this.emergencyAssignmentFeedback = '';
  }

  cancelEmergencyAssignmentEdit(): void {
    this.selectedEmergencyTechnicianId = this.selectedMaintenanceRequest?.assignedTechnicianId ?? null;
    this.isEditingEmergencyAssignment = false;
    this.emergencyAssignmentFeedback = '';
  }

  updateSelectedEmergencyStatus(nextStatus: 'activo' | 'rechazado'): void {
    const selected = this.selectedMaintenanceRequest;

    if (!selected || this.isUpdatingEmergencyStatus) {
      return;
    }

    this.isUpdatingEmergencyStatus = true;

    this.http
      .put<EmergencyReport>(
        `${this.emergenciesApiUrl}/${selected.id}/status`,
        { emergency_status: nextStatus },
        this.buildAuthRequestOptions({
          workshop_id: this.currentWorkshopId,
        }),
      )
      .subscribe({
        next: (updatedReport) => {
          const updatedRequest = this.mapEmergencyReportToRequest(updatedReport);
          this.maintenanceRequests = this.maintenanceRequests.map((request) =>
            request.id === updatedRequest.id ? updatedRequest : request,
          );
          this.selectedMaintenanceRequestId = updatedRequest.id;
          this.selectedEmergencyTechnicianId = updatedRequest.assignedTechnicianId;
          this.loadSelectedEmergencyTimeline();
          this.loadSelectedEmergencyTracking(true);
          this.isUpdatingEmergencyStatus = false;
          this.emergencyAssignmentFeedback =
            nextStatus === 'activo'
              ? 'Emergencia aceptada. Ahora puedes asignar un tecnico disponible.'
              : '';

          if (nextStatus === 'activo') {
            this.maintenanceFilter = 'activo';
            this.closeEmergencyModal();
          }

          if (nextStatus === 'rechazado') {
            this.closeEmergencyModal();
            this.loadEmergencies();
          }
        },
        error: () => {
          this.isUpdatingEmergencyStatus = false;
          window.alert('No se pudo actualizar el estado de la emergencia.');
        },
      });
  }

  assignSelectedEmergencyTechnician(): void {
    const selected = this.selectedMaintenanceRequest;

    if (
      !selected ||
      !this.currentWorkshopId ||
      !this.selectedEmergencyTechnicianId ||
      this.isAssigningEmergencyTechnician
    ) {
      return;
    }

    if (this.statusFilterGroup(selected.status) !== 'activo') {
      this.emergencyAssignmentFeedback = 'Primero acepta la emergencia para asignar un tecnico.';
      return;
    }

    this.isAssigningEmergencyTechnician = true;
    this.emergencyAssignmentFeedback = '';

    this.http
      .put<EmergencyReport>(
        `${this.emergenciesApiUrl}/${selected.id}/technician-assignment`,
        { technician_id: this.selectedEmergencyTechnicianId },
        this.buildAuthRequestOptions({
          workshop_id: this.currentWorkshopId,
        }),
      )
      .subscribe({
        next: (updatedReport) => {
          const updatedRequest = this.mapEmergencyReportToRequest(updatedReport);
          this.maintenanceRequests = this.maintenanceRequests.map((request) =>
            request.id === updatedRequest.id ? updatedRequest : request,
          );
          this.selectedMaintenanceRequestId = updatedRequest.id;
          this.selectedEmergencyTechnicianId = updatedRequest.assignedTechnicianId;
          this.isEditingEmergencyAssignment = false;
          this.isAssigningEmergencyTechnician = false;
          this.emergencyAssignmentFeedback = 'Tecnico asignado correctamente.';
          this.loadSelectedEmergencyTimeline();
          this.loadSelectedEmergencyTracking(true);
          this.loadTechnicians();
        },
        error: () => {
          this.isAssigningEmergencyTechnician = false;
          this.emergencyAssignmentFeedback = 'No se pudo asignar el tecnico seleccionado.';
        },
      });
  }

  deleteSelectedEmergency(): void {
    const selected = this.selectedMaintenanceRequest;

    if (!selected || this.isUpdatingEmergencyStatus) {
      return;
    }

    const confirmed = window.confirm(`¿Deseas eliminar la solicitud ${selected.code}?`);

    if (!confirmed) {
      return;
    }

    this.isUpdatingEmergencyStatus = true;

    this.http
      .delete(
        `${this.emergenciesApiUrl}/${selected.id}`,
        this.buildAuthRequestOptions({
          workshop_id: this.currentWorkshopId,
        }),
      )
      .subscribe({
        next: () => {
          this.isUpdatingEmergencyStatus = false;
          this.closeEmergencyModal();
          this.loadEmergencies();
        },
        error: () => {
          this.isUpdatingEmergencyStatus = false;
          window.alert('No se pudo eliminar la emergencia.');
        },
      });
  }

  loadEmergencies(options?: { refreshSelectedTimeline?: boolean; silentTimelineRefresh?: boolean }): void {
    const refreshSelectedTimeline = options?.refreshSelectedTimeline ?? true;
    const silentTimelineRefresh = options?.silentTimelineRefresh ?? false;
    this.emergenciesFeedback = '';

    if (this.isGlobalAdminSession) {
      this.maintenanceRequests = [];
      this.selectedMaintenanceRequestId = null;
      this.isEmergenciesLoading = false;
      this.emergenciesFeedback = 'Las emergencias operativas por tenant no aplican para SUPERADMIN_GLOBAL.';
      this.renderSelectedEmergencyMap();
      return;
    }

    this.isEmergenciesLoading = true;

    this.http.get<EmergencyReport[]>(
      this.emergenciesApiUrl,
      this.buildAuthRequestOptions({
        nearest_workshop_id: this.currentWorkshopId,
      }),
    ).subscribe({
      next: (reports) => {
        const previousSelectedId = this.selectedMaintenanceRequestId;
        this.maintenanceRequests = reports.map((report) => this.mapEmergencyReportToRequest(report));
        const previousSelectionStillExists = this.maintenanceRequests.some((request) => request.id === previousSelectedId);
        this.selectedMaintenanceRequestId = previousSelectionStillExists
          ? previousSelectedId
          : this.maintenanceRequests[0]?.id ?? null;
        if (this.showEmergencyModal && this.selectedMaintenanceRequestId !== null && refreshSelectedTimeline) {
          this.loadSelectedEmergencyTimeline(silentTimelineRefresh);
          this.loadSelectedEmergencyTracking(silentTimelineRefresh);
        }
        this.isEmergenciesLoading = false;
        this.renderSelectedEmergencyMap();
      },
      error: (error) => {
        this.maintenanceRequests = [];
        this.selectedMaintenanceRequestId = null;
        this.isEmergenciesLoading = false;
        this.emergenciesFeedback = error?.status === 403
          ? 'No tienes acceso a esta lista de emergencias con el alcance actual.'
          : 'No se pudo cargar la lista de emergencias.';
        this.renderSelectedEmergencyMap();
      },
    });
  }

  openEmergencyNotifications(): void {
    this.markPendingEmergenciesAsSeen();
    this.maintenanceFilter = 'pendiente';
    this.maintenanceSearch = '';
    this.selectSection('emergencies');
    this.loadEmergencies();
  }

  private markPendingEmergenciesAsSeen(): void {
    const latestPendingEmergencyId = this.maintenanceRequests
      .filter((request) => this.statusFilterGroup(request.status) === 'pendiente')
      .reduce((latestId, request) => Math.max(latestId, request.id), this.lastSeenPendingEmergencyId);

    this.lastSeenPendingEmergencyId = latestPendingEmergencyId;
  }

  loadSelectedEmergencyTimeline(silent = false): void {
    const selected = this.selectedMaintenanceRequest;

    if (!selected) {
      this.selectedEmergencyTimeline = null;
      this.selectedEmergencyNextTimelineStatus = null;
      this.isEmergencyTimelineLoading = false;
      return;
    }

    if (!silent) {
      this.isEmergencyTimelineLoading = true;
      this.emergencyTimelineFeedback = '';
    }

    this.http
      .get<EmergencyTimelineResponse>(
        `${this.emergenciesApiUrl}/${selected.id}/timeline`,
        this.buildAuthRequestOptions({
          workshop_id: this.currentWorkshopId,
        }),
      )
      .subscribe({
        next: (timeline) => {
          this.selectedEmergencyTimeline = this.normalizeEmergencyTimeline(timeline, selected);
          this.selectedEmergencyNextTimelineStatus = this.nextTimelineStatusOption(this.selectedEmergencyTimeline.current_status);
          this.isEmergencyTimelineLoading = false;
          this.syncEmergencyStatusInView(this.selectedEmergencyTimeline.current_status, selected.id);
        },
        error: () => {
          this.selectedEmergencyTimeline = this.buildFallbackEmergencyTimeline(selected);
          this.selectedEmergencyNextTimelineStatus = this.nextTimelineStatusOption(this.selectedEmergencyTimeline.current_status);
          this.isEmergencyTimelineLoading = false;
        },
      });
  }

  loadSelectedEmergencyTracking(silent = false): void {
    const selected = this.selectedMaintenanceRequest;

    if (!selected) {
      this.selectedEmergencyTracking = null;
      this.isEmergencyTrackingLoading = false;
      return;
    }

    if (!silent) {
      this.isEmergencyTrackingLoading = true;
      this.emergencyTrackingFeedback = '';
    }

    this.http
      .get<EmergencyTrackingResponse>(
        `${this.emergenciesApiUrl}/${selected.id}/tracking`,
        this.buildAuthRequestOptions({
          workshop_id: this.currentWorkshopId,
        }),
      )
      .subscribe({
        next: (tracking) => {
          this.selectedEmergencyTracking = tracking;
          this.isEmergencyTrackingLoading = false;
          this.renderSelectedEmergencyMap();
        },
        error: (error) => {
          this.selectedEmergencyTracking = null;
          this.isEmergencyTrackingLoading = false;
          this.emergencyTrackingFeedback =
            typeof error?.error?.detail === 'string'
              ? error.error.detail
              : 'No se pudo obtener la ruta y ETA del auxilio.';
          this.renderSelectedEmergencyMap();
        },
      });
  }

  updateSelectedEmergencyTimelineStatus(): void {
    const selected = this.selectedMaintenanceRequest;
    const nextStatus = this.selectedEmergencyNextTimelineStatus;

    if (!selected || !nextStatus || this.isUpdatingEmergencyTimelineStatus) {
      return;
    }

    this.isUpdatingEmergencyTimelineStatus = true;
    this.emergencyTimelineFeedback = '';

    this.http
      .patch<EmergencyTimelineResponse>(
        `${this.emergenciesApiUrl}/${selected.id}/estado`,
        {
          estado: nextStatus,
          observacion: 'Cambio realizado desde dashboard web',
        },
        {
          ...this.buildAuthRequestOptions({
            workshop_id: this.currentWorkshopId,
          }),
        },
      )
      .subscribe({
        next: (timeline) => {
          this.selectedEmergencyTimeline = this.normalizeEmergencyTimeline(timeline, selected);
          this.selectedEmergencyNextTimelineStatus = this.nextTimelineStatusOption(this.selectedEmergencyTimeline.current_status);
          this.syncEmergencyStatusInView(this.selectedEmergencyTimeline.current_status, selected.id);
          this.isUpdatingEmergencyTimelineStatus = false;
          this.emergencyTimelineFeedback = 'Estado actualizado correctamente.';
          this.loadSelectedEmergencyTracking(true);
          this.loadEmergencies({ refreshSelectedTimeline: false });
        },
        error: () => {
          this.isUpdatingEmergencyTimelineStatus = false;
          this.emergencyTimelineFeedback = 'No se pudo actualizar el estado del proceso.';
        },
      });
  }

  selectEmergencyTimelineStatusOption(status: EmergencyTimelineStatus): void {
    if (this.isUpdatingEmergencyTimelineStatus) {
      return;
    }

    this.selectedEmergencyNextTimelineStatus = status;
  }

  rejectSelectedEmergency(): void {
    const selected = this.selectedMaintenanceRequest;
    const motivo = this.emergencyRejectionReason.trim();

    if (!selected || this.isRejectingEmergency) {
      return;
    }

    if (!motivo) {
      this.emergencyTimelineFeedback = 'Debes ingresar el motivo del rechazo.';
      return;
    }

    this.isRejectingEmergency = true;
    this.emergencyTimelineFeedback = '';

    this.http
      .patch<EmergencyRejectionResponse>(
        `${this.emergenciesApiUrl}/${selected.id}/rechazar`,
        {
          motivo,
          changed_by_role: this.isWorkshopSession ? 'workshop' : 'admin',
          changed_by_user_id: typeof this.adminSession?.id === 'number' ? this.adminSession.id : null,
        },
        {
          ...this.buildAuthRequestOptions({
            workshop_id: this.currentWorkshopId,
          }),
        },
      )
      .subscribe({
        next: (response) => {
          this.applyEmergencyReportUpdate(response.emergency);
          this.selectedEmergencyTimeline = this.normalizeEmergencyTimeline(response.timeline, this.selectedMaintenanceRequest ?? selected);
          this.selectedEmergencyNextTimelineStatus = this.nextTimelineStatusOption(this.selectedEmergencyTimeline.current_status);
          this.emergencyRejectionReason = response.emergency.rejection_reason ?? motivo;
          this.isRejectingEmergency = false;
          this.loadSelectedEmergencyTracking(true);
          this.emergencyTimelineFeedback =
            response.emergency.emergency_status === 'en_revision'
              ? 'Solicitud rechazada y reasignada correctamente.'
              : 'Solicitud rechazada correctamente.';
          this.loadOperationalOverview();
          this.loadEmergencies({ refreshSelectedTimeline: false });
        },
        error: () => {
          this.isRejectingEmergency = false;
          this.emergencyTimelineFeedback = 'No se pudo rechazar la solicitud.';
        },
      });
  }

  private startEmergencyRefresh(): void {
    if (typeof window === 'undefined' || this.emergencyRefreshTimer !== null || this.realtimeConnectionState === 'connected') {
      return;
    }

    this.emergencyRefreshTimer = window.setInterval(() => {
      this.runEmergencyRefreshCycle();
    }, this.emergencyRefreshMs);
  }

  private runEmergencyRefreshCycle(): void {
    this.loadOperationalOverview();
    this.loadEmergencies({
      refreshSelectedTimeline: this.showEmergencyModal,
      silentTimelineRefresh: this.showEmergencyModal,
    });
    if (this.selectedSection === 'quotation_history' || this.selectedSection === 'quotation_requests') {
      this.loadQuotationHistory();
    }
    if (this.selectedSection === 'contracted_services') {
      this.loadContractedServices();
    }
  }

  private ensureFallbackPolling(immediate = false): void {
    const shouldRunImmediately = immediate && this.emergencyRefreshTimer === null;
    this.startEmergencyRefresh();
    if (shouldRunImmediately) {
      this.runEmergencyRefreshCycle();
    }
  }

  private stopEmergencyRefresh(): void {
    if (typeof window === 'undefined' || this.emergencyRefreshTimer === null) {
      return;
    }

    window.clearInterval(this.emergencyRefreshTimer);
    this.emergencyRefreshTimer = null;
  }

  private updateRealtimePollingMode(state: ConnectionState): void {
    if (state === 'connected') {
      this.stopEmergencyRefresh();
      return;
    }

    if (state === 'idle' || state === 'connecting') {
      this.startEmergencyRefresh();
      return;
    }

    if (state === 'reconnecting' || state === 'disconnected' || state === 'error') {
      this.ensureFallbackPolling(true);
    }
  }

  private mapRealtimeEventToRefreshRequest(
    event: { type: string; entity_id?: number | null; payload?: { emergency_id?: number } | undefined },
  ): RealtimeRefreshRequest | null {
    if (DASHBOARD_EMERGENCY_REFRESH_EVENT_TYPES.has(event.type)) {
      return {
        overview: true,
        emergencies: true,
      };
    }

    if (event.type === 'tracking_location_updated') {
      const selectedEmergencyId = this.selectedMaintenanceRequestId;
      const eventEmergencyId = event.entity_id ?? event.payload?.emergency_id ?? null;
      if (selectedEmergencyId !== null && eventEmergencyId === selectedEmergencyId) {
        return {
          tracking: true,
        };
      }
      return null;
    }

    if (DASHBOARD_QUOTATION_REFRESH_EVENT_TYPES.has(event.type)) {
      return {
        overview: true,
        quotationRequests: this.isWorkshopSession,
        quotationHistory: this.isWorkshopSession,
        contractedServices: this.isWorkshopSession,
      };
    }

    return null;
  }

  private scheduleRealtimeRefresh(request: RealtimeRefreshRequest): void {
    this.pendingRealtimeRefresh = {
      overview: this.pendingRealtimeRefresh.overview || Boolean(request.overview),
      emergencies: this.pendingRealtimeRefresh.emergencies || Boolean(request.emergencies),
      quotationRequests: this.pendingRealtimeRefresh.quotationRequests || Boolean(request.quotationRequests),
      quotationHistory: this.pendingRealtimeRefresh.quotationHistory || Boolean(request.quotationHistory),
      contractedServices: this.pendingRealtimeRefresh.contractedServices || Boolean(request.contractedServices),
      tracking: this.pendingRealtimeRefresh.tracking || Boolean(request.tracking),
    };

    if (typeof window === 'undefined') {
      this.flushRealtimeRefresh();
      return;
    }

    if (this.realtimeRefreshTimer !== null) {
      return;
    }

    this.realtimeRefreshTimer = window.setTimeout(() => {
      this.realtimeRefreshTimer = null;
      this.flushRealtimeRefresh();
    }, this.realtimeRefreshDebounceMs);
  }

  private flushRealtimeRefresh(): void {
    const request = this.pendingRealtimeRefresh;
    this.pendingRealtimeRefresh = {
      overview: false,
      emergencies: false,
      quotationRequests: false,
      quotationHistory: false,
      contractedServices: false,
      tracking: false,
    };

    if (request.overview) {
      this.loadOperationalOverview();
    }

    if (request.emergencies) {
      this.loadEmergencies({
        refreshSelectedTimeline: this.showEmergencyModal,
        silentTimelineRefresh: this.showEmergencyModal,
      });
    }

    if (request.quotationRequests) {
      this.loadQuotationRequests();
    }

    if (request.quotationHistory) {
      this.loadQuotationHistory();
    }

    if (request.contractedServices) {
      this.loadContractedServices();
    }

    if (request.tracking && this.showEmergencyModal && this.selectedMaintenanceRequestId !== null) {
      this.loadSelectedEmergencyTracking(true);
    }
  }

  private clearRealtimeRefreshTimer(): void {
    if (typeof window !== 'undefined' && this.realtimeRefreshTimer !== null) {
      window.clearTimeout(this.realtimeRefreshTimer);
    }
    this.realtimeRefreshTimer = null;
    this.pendingRealtimeRefresh = {
      overview: false,
      emergencies: false,
      quotationRequests: false,
      quotationHistory: false,
      contractedServices: false,
      tracking: false,
    };
  }

  private syncEmergencyStatusInView(status: EmergencyStatus | null | undefined, emergencyId: number): void {
    if (!status) {
      return;
    }

    this.maintenanceRequests = this.maintenanceRequests.map((request) =>
      request.id === emergencyId ? { ...request, status } : request,
    );
  }

  private applyEmergencyReportUpdate(report: EmergencyReport): void {
    const mappedRequest = this.mapEmergencyReportToRequest(report);
    this.maintenanceRequests = this.maintenanceRequests.map((request) =>
      request.id === mappedRequest.id ? mappedRequest : request,
    );
  }

  private mapEmergencyReportToRequest(report: EmergencyReport): MaintenanceRequest {
    const addressParts = [report.address?.trim(), report.zone?.trim()].filter(Boolean);
    const vehicleLabel = [report.vehicle_name?.trim(), report.vehicle_plate?.trim()].filter(Boolean).join(' · ');
    const detail =
      report.description?.trim() ||
      report.problem_type_standardized?.trim() ||
      report.problem_type?.trim() ||
      'Emergencia reportada desde la app movil.';

    return {
      id: report.id,
      localId: report.local_id ?? null,
      code: `EMG-${String(report.id).padStart(6, '0')}`,
      client: report.client_name?.trim() || `Cliente #${report.client_id ?? report.id}`,
      vehicle: vehicleLabel || 'Vehiculo sin detalle',
      location: addressParts.join(' · ') || 'Ubicacion pendiente',
      priority: this.priorityFromProblemType(report.problem_type_standardized || report.problem_type),
      status: report.emergency_status ?? 'pendiente',
      price: report.price,
      distance: this.formatDistance(report.nearest_workshop_distance_meters),
      detail,
      reportedAt: this.relativeTimeLabel(report.created_at),
      createdAt: report.created_at,
      latitude: report.latitude,
      longitude: report.longitude,
      nearestWorkshopId: report.nearest_workshop_id,
      nearestWorkshopName: report.nearest_workshop_name,
      problemType: report.problem_type,
      standardizedProblemType: report.problem_type_standardized,
      clientDescription: report.description?.trim() || null,
      audioTranscript: report.audio_transcript?.trim() || null,
      photoUrls: this.getEmergencyPhotoUrls(report),
      audioUrl: this.normalizeBackendAssetUrl(report.audio_url),
      mapEmbedUrl: this.buildEmergencyMapEmbedUrl(report.latitude, report.longitude),
      mapExternalUrl: this.buildEmergencyMapExternalUrl(report.latitude, report.longitude),
      assignmentId: report.assignment_id,
      assignmentStatus: report.assignment_status,
      assignedTechnicianId: report.assigned_technician_id,
      assignedTechnicianName: report.assigned_technician_name,
      assignedTechnicianPhone: report.assigned_technician_phone,
      assignedTechnicianSpecialty: report.assigned_technician_specialty,
      rejectionReason: report.rejection_reason?.trim() || null,
      rejectedAt: report.rejected_at,
      horaLlegada: report.hora_llegada ?? null,
      latitudLlegada: report.latitud_llegada ?? null,
      longitudLlegada: report.longitud_llegada ?? null,
    };
  }

  get emergencyTimelineSteps() {
    const timeline = this.selectedEmergencyTimeline;
    const currentStatus = this.timelineCurrentStatus;
    const currentIndex = currentStatus ? this.timelineStepIndex(currentStatus) : -1;
    const isCancelled = currentStatus === 'solicitud_cancelada';

    return EMERGENCY_TIMELINE_STEPS.map((step, index) => {
      const entry = timeline?.timeline.find((item) => item.status === step.status) ?? null;
      const isCurrent = currentStatus === step.status;
      const isCompleted = isCancelled
        ? step.status === 'solicitud_cancelada' || Boolean(entry)
        : currentIndex >= index || Boolean(entry);

      return {
        ...step,
        entry,
        isCompleted,
        isCurrent,
        isCancelled: step.status === 'solicitud_cancelada' && (isCurrent || Boolean(entry)),
      };
    });
  }

  get timelineCurrentStatus(): EmergencyTimelineStatus | null {
    if (this.selectedEmergencyTimeline?.current_status) {
      return this.normalizeTimelineStatus(this.selectedEmergencyTimeline.current_status);
    }

    if (this.selectedMaintenanceRequest?.status) {
      return this.normalizeTimelineStatus(this.selectedMaintenanceRequest.status);
    }

    return null;
  }

  get availableTimelineStatusOptions(): Array<{ value: EmergencyTimelineStatus; label: string }> {
    return EMERGENCY_TIMELINE_STEPS
      .filter((step) => step.status !== 'solicitud_recibida' && step.status !== 'solicitud_cancelada')
      .map((step) => ({ value: step.status, label: step.label }));
  }

  get isEmergencyRejected(): boolean {
    return this.timelineCurrentStatus === 'solicitud_cancelada';
  }

  get selectedEmergencyWasReassigned(): boolean {
    return Boolean(
      this.selectedEmergencyTimeline?.timeline.some((item) => this.isEmergencyReassignmentEntry(item)) &&
        this.timelineCurrentStatus === 'en_revision',
    );
  }

  get selectedEmergencyNoAlternativeWorkshop(): boolean {
    return Boolean(this.selectedEmergencyTimeline?.timeline.some((item) => this.isEmergencyNoAlternativeEntry(item)));
  }

  timelineHistoryTitle(item: EmergencyTimelineEntry): string {
    if (this.isEmergencyReassignmentEntry(item)) {
      return 'Solicitud reasignada automáticamente';
    }

    if (this.isEmergencyNoAlternativeEntry(item)) {
      return 'No se encontró otro taller disponible';
    }

    if (item.status === 'solicitud_cancelada') {
      return 'Solicitud rechazada';
    }

    return this.emergencyStatusLabel(item.status);
  }

  timelineHistoryObservationLabel(item: EmergencyTimelineEntry): string {
    if (this.isEmergencyReassignmentEntry(item)) {
      return 'Nuevo taller:';
    }

    if (this.isEmergencyNoAlternativeEntry(item)) {
      return '';
    }

    return 'Motivo:';
  }

  private getEmergencyPhotoUrls(report: EmergencyReport): string[] {
    const rawPhotoUrls = this.parseMediaList(report.photo_urls);
    const rawPhotoPaths = this.parseMediaList(report.photo_paths);
    const normalizedPhotoUrls = rawPhotoUrls
      .map((photoUrl) => this.normalizeBackendAssetUrl(photoUrl))
      .filter((photoUrl): photoUrl is string => Boolean(photoUrl));
    const normalizedPhotoPaths = rawPhotoPaths
      .map((photoPath) => this.normalizeBackendAssetUrl(photoPath))
      .filter((photoUrl): photoUrl is string => Boolean(photoUrl));

    return Array.from(new Set([...normalizedPhotoUrls, ...normalizedPhotoPaths]));
  }

  private parseMediaList(value: string[] | string | null | undefined): string[] {
    if (Array.isArray(value)) {
      return value.filter((item): item is string => typeof item === 'string' && Boolean(item.trim()));
    }

    if (typeof value !== 'string') {
      return [];
    }

    const trimmed = value.trim();

    if (!trimmed) {
      return [];
    }

    try {
      const parsed = JSON.parse(trimmed);

      if (Array.isArray(parsed)) {
        return parsed.filter((item): item is string => typeof item === 'string' && Boolean(item.trim()));
      }
    } catch {
      return [trimmed];
    }

    return [trimmed];
  }

  private buildEmergencyMapEmbedUrl(latitude: number | null, longitude: number | null): SafeResourceUrl | null {
    if (!this.hasValidCoordinates(latitude, longitude)) {
      return null;
    }

    const lat = Number(latitude);
    const lng = Number(longitude);
    const zoomOffset = 0.006;
    const left = lng - zoomOffset;
    const right = lng + zoomOffset;
    const bottom = lat - zoomOffset;
    const top = lat + zoomOffset;
    const url =
      'https://www.openstreetmap.org/export/embed.html' +
      `?bbox=${left}%2C${bottom}%2C${right}%2C${top}` +
      '&layer=mapnik' +
      `&marker=${lat}%2C${lng}`;

    return this.sanitizer.bypassSecurityTrustResourceUrl(url);
  }

  private buildEmergencyMapExternalUrl(latitude: number | null, longitude: number | null): string | null {
    if (!this.hasValidCoordinates(latitude, longitude)) {
      return null;
    }

    const lat = Number(latitude);
    const lng = Number(longitude);
    return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=16/${lat}/${lng}`;
  }

  private hasValidCoordinates(latitude: number | null, longitude: number | null): boolean {
    return (
      typeof latitude === 'number' &&
      Number.isFinite(latitude) &&
      latitude >= -90 &&
      latitude <= 90 &&
      typeof longitude === 'number' &&
      Number.isFinite(longitude) &&
      longitude >= -180 &&
      longitude <= 180
    );
  }

  private normalizeBackendAssetUrl(value: string | null | undefined): string | null {
    const normalized = value?.trim();

    if (!normalized) {
      return null;
    }

    if (/^https?:\/\//i.test(normalized)) {
      return normalized;
    }

    if (normalized.startsWith('/')) {
      return `${this.backendBaseUrl}${normalized}`;
    }

    if (normalized.startsWith('uploads/') || normalized.startsWith('emergencias/') || normalized.startsWith('vehicles/')) {
      return `${this.backendBaseUrl}/uploads/${normalized.replace(/^uploads\//, '')}`;
    }

    return `${this.backendBaseUrl}/${normalized}`;
  }

  private priorityFromProblemType(problemType: string | null | undefined): 'Alta' | 'Media' | 'Baja' {
    switch ((problemType || '').trim()) {
      case 'Accidente':
      case 'Motor':
        return 'Alta';
      case 'Batería':
      case 'Neumático':
      case 'Sistema eléctrico':
        return 'Media';
      default:
        return 'Baja';
    }
  }

  private formatDistance(distanceMeters: number | null): string {
    if (distanceMeters === null || Number.isNaN(distanceMeters)) {
      return 'Sin distancia';
    }

    if (distanceMeters < 1000) {
      return `${Math.round(distanceMeters)} m`;
    }

    return `${(distanceMeters / 1000).toFixed(1).replace('.', ',')} km`;
  }

  formatReportPrice(price: number | null): string {
    if (price === null || Number.isNaN(price)) {
      return 'A cotizar';
    }

    return `Bs ${price.toLocaleString('es-BO', { maximumFractionDigits: 0 })}`;
  }

  calculateReportServiceAmount(price: number | null): number | null {
    if (price === null || Number.isNaN(price)) {
      return null;
    }

    return Math.round(price * 0.1);
  }

  calculateReportNetAmount(price: number | null): number | null {
    if (price === null || Number.isNaN(price)) {
      return null;
    }

    return price - this.calculateReportServiceAmount(price)!;
  }

  private relativeTimeLabel(createdAt: string): string {
    const created = new Date(createdAt).getTime();

    if (Number.isNaN(created)) {
      return 'Reciente';
    }

    const diffMinutes = Math.max(1, Math.round((Date.now() - created) / (1000 * 60)));

    if (diffMinutes < 60) {
      return `Hace ${diffMinutes} min`;
    }

    const diffHours = Math.round(diffMinutes / 60);
    if (diffHours < 24) {
      return `Hace ${diffHours} h`;
    }

    const diffDays = Math.round(diffHours / 24);
    return `Hace ${diffDays} d`;
  }

  get selectedMaintenancePhotoUrls(): string[] {
    return this.selectedMaintenanceRequest?.photoUrls ?? [];
  }

  get selectedEmergencyHasCoordinates(): boolean {
    return (
      this.selectedMaintenanceRequest?.latitude !== null &&
      this.selectedMaintenanceRequest?.latitude !== undefined &&
      this.selectedMaintenanceRequest?.longitude !== null &&
      this.selectedMaintenanceRequest?.longitude !== undefined
    );
  }

  get selectedEmergencyAuxilioLatitude(): number | null {
    return this.selectedEmergencyTracking?.technician.latitude ?? this.selectedEmergencyTracking?.workshop.latitude ?? null;
  }

  get selectedEmergencyAuxilioLongitude(): number | null {
    return this.selectedEmergencyTracking?.technician.longitude ?? this.selectedEmergencyTracking?.workshop.longitude ?? null;
  }

  get selectedEmergencyTrackingLastUpdateLabel(): string {
    if (this.selectedEmergencyTracking?.technician.last_location_at) {
      return this.relativeTimeLabel(this.selectedEmergencyTracking.technician.last_location_at);
    }
    return 'Usando ubicación inicial del taller';
  }

  formatCoordinatePair(latitude: number | null, longitude: number | null): string {
    if (!this.hasValidCoordinates(latitude, longitude)) {
      return 'Sin coordenadas disponibles';
    }
    return `${Number(latitude).toFixed(5)}, ${Number(longitude).toFixed(5)}`;
  }

  private initializeEmergencyMap(element: HTMLDivElement): void {
    if (typeof L === 'undefined') {
      return;
    }

    if (!this.emergencyMap) {
      this.emergencyMap = L.map(element, {
        zoomControl: true,
        scrollWheelZoom: true,
      }).setView([-17.7833, -63.1821], 12);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(this.emergencyMap);

      this.emergencyMapMarkersLayer = L.layerGroup().addTo(this.emergencyMap);
    }

    this.scheduleEmergencyMapResize();
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

      this.workshopEditMap.on('click', (event: { latlng: { lat: number; lng: number } }) => {
        this.updateWorkshopEditLocation(event.latlng.lat, event.latlng.lng);
      });
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

  private renderSelectedEmergencyMap(): void {
    if (!this.emergencyMap || !this.emergencyMapMarkersLayer) {
      return;
    }

    this.emergencyMapMarkersLayer.clearLayers();

    const request = this.selectedMaintenanceRequest;

    if (!request || request.latitude === null || request.longitude === null) {
      this.emergencyMap.setView([-17.7833, -63.1821], 12);
      this.scheduleEmergencyMapResize();
      return;
    }

    const bounds: [number, number][] = [];
    const emergencyMarker = L.marker([request.latitude, request.longitude], {
      icon: this.createEmergencyMarkerIcon(),
    }).addTo(this.emergencyMapMarkersLayer);
    emergencyMarker.bindPopup(`
      <strong>${this.escapeHtml(request.code)}</strong><br>
      ${this.escapeHtml(request.client)}<br>
      ${this.escapeHtml(request.location)}
    `);
    bounds.push([request.latitude, request.longitude]);

    const tracking = this.selectedEmergencyTracking;
    const trackingLatitude = this.selectedEmergencyAuxilioLatitude;
    const trackingLongitude = this.selectedEmergencyAuxilioLongitude;
    const trackingLabel =
      tracking?.technician.name || tracking?.workshop.name || request.nearestWorkshopName || 'Auxilio asignado';
    const trackingDetail = tracking?.technician.name ? 'Técnico asignado' : 'Ubicación base del taller';

    if (this.hasValidCoordinates(trackingLatitude, trackingLongitude)) {
      const auxilioMarker = L.marker([trackingLatitude!, trackingLongitude!], {
        icon: this.createAuxilioMarkerIcon(),
      }).addTo(this.emergencyMapMarkersLayer);
      auxilioMarker.bindPopup(`
        <strong>${this.escapeHtml(trackingLabel)}</strong><br>
        ${this.escapeHtml(trackingDetail)}<br>
        ETA: ${this.escapeHtml(tracking?.route.duration_text || 'Sin ETA')}
      `);

      const polylinePoints = tracking?.route.polyline?.length
        ? tracking.route.polyline.map((point) => [point[0], point[1]])
        : [
            [trackingLatitude!, trackingLongitude!],
            [request.latitude, request.longitude],
          ];
      L.polyline(polylinePoints, {
        color: '#1e5aa8',
        weight: 4,
        opacity: 0.82,
        dashArray: tracking?.route.provider === 'haversine_fallback' ? '10 8' : undefined,
      }).addTo(this.emergencyMapMarkersLayer);
      bounds.push([trackingLatitude!, trackingLongitude!]);
    } else {
      const assignedWorkshop =
        request.nearestWorkshopId === null
          ? null
          : this.workshops.find((workshop) => workshop.id === request.nearestWorkshopId) ?? null;
      if (
        assignedWorkshop &&
        assignedWorkshop.latitude !== null &&
        assignedWorkshop.longitude !== null
      ) {
        const workshopMarker = L.marker([assignedWorkshop.latitude, assignedWorkshop.longitude], {
          icon: this.createAuxilioMarkerIcon(),
        }).addTo(this.emergencyMapMarkersLayer);
        workshopMarker.bindPopup(`
          <strong>${this.escapeHtml(assignedWorkshop.workshop_name)}</strong><br>
          ${this.escapeHtml(assignedWorkshop.specialty)}<br>
          ${this.escapeHtml(assignedWorkshop.zone)}
        `);
        L.polyline(
          [
            [request.latitude, request.longitude],
            [assignedWorkshop.latitude, assignedWorkshop.longitude],
          ],
          {
            color: '#1e5aa8',
            weight: 4,
            opacity: 0.8,
            dashArray: '10 8',
          },
        ).addTo(this.emergencyMapMarkersLayer);
        bounds.push([assignedWorkshop.latitude, assignedWorkshop.longitude]);
      }
    }

    if (bounds.length === 1) {
      this.emergencyMap.setView(bounds[0], 15, { animate: true });
      emergencyMarker.openPopup();
      this.scheduleEmergencyMapResize();
      return;
    }

    this.emergencyMap.fitBounds(bounds, {
      padding: [30, 30],
      maxZoom: 15,
    });
    this.scheduleEmergencyMapResize();
  }

  private createEmergencyMarkerIcon(): any {
    if (typeof L === 'undefined') {
      return undefined;
    }

    return L.divIcon({
      className: 'maintenance-emergency-marker',
      html:
        '<span style="position:relative;display:block;width:26px;height:26px;border-radius:50% 50% 50% 0;background:linear-gradient(180deg,#ff6c63,#d92f2f);border:2px solid rgba(255,255,255,0.96);box-shadow:0 10px 18px rgba(185,31,31,0.28);transform:rotate(-45deg);"><span style="position:absolute;inset:6px;border-radius:50%;background:#fff7f7;"></span></span>',
      iconSize: [26, 38],
      iconAnchor: [13, 38],
      popupAnchor: [0, -34],
    });
  }

  private createAuxilioMarkerIcon(): any {
    if (typeof L === 'undefined') {
      return undefined;
    }

    return L.divIcon({
      className: 'maintenance-auxilio-marker',
      html:
        '<span style="display:grid;place-items:center;width:24px;height:24px;border-radius:50%;background:linear-gradient(180deg,#1e7f6f,#0d5f53);border:2px solid rgba(255,255,255,0.96);box-shadow:0 8px 18px rgba(10,88,77,0.22);color:#fff;font-size:12px;font-weight:800;">A</span>',
      iconSize: [24, 24],
      iconAnchor: [12, 12],
      popupAnchor: [0, -14],
    });
  }

  private scheduleEmergencyMapResize(): void {
    if (typeof window === 'undefined' || !this.emergencyMap) {
      return;
    }

    if (this.emergencyMapResizeTimer !== undefined) {
      window.clearTimeout(this.emergencyMapResizeTimer);
    }

    this.emergencyMapResizeTimer = window.setTimeout(() => {
      this.emergencyMap?.invalidateSize();
    }, 120);
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
      typeof this.workshopForm.latitude === 'number' && Number.isFinite(this.workshopForm.latitude)
        ? this.workshopForm.latitude
        : -17.7833;
    const longitude =
      typeof this.workshopForm.longitude === 'number' && Number.isFinite(this.workshopForm.longitude)
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
    if (typeof window !== 'undefined' && this.workshopEditMapResizeTimer !== undefined) {
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

  private initializeSucursalMap(element: HTMLDivElement): void {
    if (typeof L === 'undefined') {
      return;
    }

    if (this.sucursalMapHost && this.sucursalMapHost !== element) {
      this.destroySucursalMap();
    }

    this.sucursalMapHost = element;

    if (!this.sucursalMap) {
      const [latitude, longitude] = this.getSucursalCoordinates();

      this.sucursalMap = L.map(element, {
        zoomControl: true,
        scrollWheelZoom: true,
      }).setView([latitude, longitude], 13);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(this.sucursalMap);

      this.sucursalMapMarker = L.marker([latitude, longitude], {
        draggable: true,
      }).addTo(this.sucursalMap);

      this.sucursalMapMarker.on('dragend', () => {
        const position = this.sucursalMapMarker.getLatLng();
        this.updateSucursalSelectedLocation(position.lat, position.lng);
      });

      this.sucursalMap.on('click', (event: { latlng: { lat: number; lng: number } }) => {
        this.updateSucursalSelectedLocation(event.latlng.lat, event.latlng.lng);
      });
    }

    this.scheduleSucursalMapResize();
  }

  private renderSucursalMap(animate = false): void {
    if (!this.sucursalMap || !this.sucursalMapMarker) {
      return;
    }

    const [latitude, longitude] = this.getSucursalCoordinates();
    this.sucursalMapMarker.setLatLng([latitude, longitude]);
    this.sucursalMap.setView([latitude, longitude], 15, { animate });
    this.scheduleSucursalMapResize();
  }

  private updateSucursalSelectedLocation(latitude: number, longitude: number): void {
    this.sucursalForm = {
      ...this.sucursalForm,
      latitud: latitude,
      longitud: longitude,
    };
    this.sucursalLocationMessage = '';

    if (this.sucursalMapMarker) {
      this.sucursalMapMarker.setLatLng([latitude, longitude]);
    }

    this.reverseGeocodeSucursal(latitude, longitude);
  }

  private getSucursalCoordinates(): [number, number] {
    const latitude =
      typeof this.sucursalForm.latitud === 'number' && Number.isFinite(this.sucursalForm.latitud)
        ? this.sucursalForm.latitud
        : SANTA_CRUZ_DEFAULT_COORDINATES.latitud;
    const longitude =
      typeof this.sucursalForm.longitud === 'number' && Number.isFinite(this.sucursalForm.longitud)
        ? this.sucursalForm.longitud
        : SANTA_CRUZ_DEFAULT_COORDINATES.longitud;

    return [latitude, longitude];
  }

  private scheduleSucursalMapResize(): void {
    if (typeof window === 'undefined' || !this.sucursalMap) {
      return;
    }

    if (this.sucursalMapResizeTimer !== undefined) {
      window.clearTimeout(this.sucursalMapResizeTimer);
    }

    this.sucursalMapResizeTimer = window.setTimeout(() => {
      this.sucursalMap?.invalidateSize();
    }, 120);
  }

  private reverseGeocodeSucursal(latitude: number, longitude: number): void {
    this.isSucursalReverseGeocoding = true;
    this.sucursalLocationMessage = '';

    this.http.get<ReverseGeocodeResponse>('https://nominatim.openstreetmap.org/reverse', {
      params: {
        format: 'jsonv2',
        lat: latitude.toFixed(6),
        lon: longitude.toFixed(6),
        'accept-language': 'es',
      },
    }).subscribe({
      next: (response) => {
        this.isSucursalReverseGeocoding = false;
        const detectedAddress = this.buildSucursalDetectedAddress(response);

        if (!detectedAddress) {
          this.sucursalDetectedAddress = '';
          this.sucursalLocationMessage =
            'No se pudo obtener dirección exacta. Puedes escribirla manualmente.';
          return;
        }

        this.sucursalDetectedAddress = detectedAddress;

        if (!this.sucursalAddressTouchedManually || !this.sucursalForm.direccion.trim()) {
          this.sucursalForm = {
            ...this.sucursalForm,
            direccion: detectedAddress,
          };
          this.sucursalLastAutofilledAddress = detectedAddress;
          this.sucursalAddressTouchedManually = false;
        }

        const detectedCity = response.address?.city || response.address?.town || response.address?.village || '';
        if (!this.sucursalForm.ciudad.trim() && detectedCity) {
          this.sucursalForm = {
            ...this.sucursalForm,
            ciudad: detectedCity,
          };
        }
      },
      error: () => {
        this.isSucursalReverseGeocoding = false;
        this.sucursalDetectedAddress = '';
        this.sucursalLocationMessage =
          'No se pudo obtener la dirección automáticamente. Puedes escribirla manualmente.';
      },
    });
  }

  private buildSucursalDetectedAddress(response: ReverseGeocodeResponse): string {
    const road = response.address?.road || response.address?.pedestrian || '';
    const suburb = response.address?.suburb || response.address?.neighbourhood || '';
    const city = response.address?.city || response.address?.town || response.address?.village || '';
    const shortAddress = [road, suburb, city].filter(Boolean).join(', ');

    if (shortAddress.length >= 8) {
      return shortAddress;
    }

    return (response.display_name || '').trim();
  }

  private normalizeSucursalZoneValue(zone: string | null): string {
    const normalized = (zone || '').trim().toLowerCase();
    const match = this.sucursalZoneOptions.find(
      (option) => option.value.toLowerCase() === normalized || option.label.toLowerCase() === normalized,
    );

    return match?.value ?? '';
  }

  private resetSucursalLocationState(): void {
    this.isSucursalLocationLocating = false;
    this.isSucursalReverseGeocoding = false;
    this.sucursalLocationMessage = '';
    this.sucursalDetectedAddress = '';
    this.sucursalAddressTouchedManually = false;
    this.sucursalLastAutofilledAddress = '';
  }

  private destroySucursalMap(): void {
    if (typeof window !== 'undefined' && this.sucursalMapResizeTimer !== undefined) {
      window.clearTimeout(this.sucursalMapResizeTimer);
      this.sucursalMapResizeTimer = undefined;
    }

    if (this.sucursalMap) {
      this.sucursalMap.remove();
      this.sucursalMap = undefined;
      this.sucursalMapMarker = undefined;
    }

    this.sucursalMapHost = undefined;
  }

  private shouldIncludeSucursalInOverview(sucursal: SucursalRecord): boolean {
    if (sucursal.estado !== 'activo') {
      return false;
    }

    if (!this.hasValidCoordinates(sucursal.latitud, sucursal.longitud)) {
      return false;
    }

    if (this.isAdminSucursalSession) {
      return sucursal.id === (this.adminSession?.sucursalId ?? null);
    }

    return true;
  }

  private initializeSucursalesOverviewMap(element: HTMLDivElement): void {
    if (typeof L === 'undefined') {
      return;
    }

    if (this.sucursalesOverviewMapHost && this.sucursalesOverviewMapHost !== element) {
      this.destroySucursalesOverviewMap();
    }

    this.sucursalesOverviewMapHost = element;

    if (!this.sucursalesOverviewMap) {
      this.sucursalesOverviewMap = L.map(element, {
        zoomControl: true,
        scrollWheelZoom: true,
      }).setView(
        [SANTA_CRUZ_DEFAULT_COORDINATES.latitud, SANTA_CRUZ_DEFAULT_COORDINATES.longitud],
        11,
      );

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(this.sucursalesOverviewMap);
    }

    this.scheduleSucursalesOverviewMapResize();
  }

  private renderSucursalesOverviewMap(): void {
    if (!this.sucursalesOverviewMap) {
      return;
    }

    this.clearSucursalesOverviewMarkers();

    const sucursales = this.sucursalesOverviewData;
    if (!sucursales.length) {
      return;
    }

    const bounds = L.latLngBounds([]);

    for (const sucursal of sucursales) {
      const latitude = sucursal.latitud as number;
      const longitude = sucursal.longitud as number;
      const marker = L.marker([latitude, longitude]).addTo(this.sucursalesOverviewMap);

      marker.bindPopup(this.buildSucursalOverviewPopup(sucursal));
      marker.bindTooltip(this.escapeHtml(sucursal.nombre), {
        direction: 'top',
      });

      this.sucursalesOverviewMarkers.push(marker);
      bounds.extend([latitude, longitude]);
    }

    if (sucursales.length === 1) {
      const sucursal = sucursales[0];
      this.sucursalesOverviewMap.setView([sucursal.latitud as number, sucursal.longitud as number], 14, {
        animate: false,
      });
    } else {
      this.sucursalesOverviewMap.fitBounds(bounds, {
        padding: [30, 30],
        maxZoom: 14,
      });
    }

    this.scheduleSucursalesOverviewMapResize();
  }

  private buildSucursalOverviewPopup(sucursal: SucursalRecord): string {
    const especialidades = sucursal.especialidades.length
      ? sucursal.especialidades.join(', ')
      : sucursal.workshop_specialty || 'Sin especialidades registradas';
    const direccion = sucursal.direccion?.trim() || sucursal.ciudad?.trim() || 'Sin dirección registrada';
    const zona = sucursal.zona?.trim() || 'Sin zona registrada';
    const responsable = sucursal.responsable?.trim() || 'Sin responsable asignado';
    const tecnicos =
      typeof sucursal.technicians_count === 'number'
        ? `${sucursal.technicians_count} técnico${sucursal.technicians_count === 1 ? '' : 's'}`
        : 'Sin técnicos registrados';

    return `
      <div style="min-width:220px;display:grid;gap:0.2rem;">
        <strong>${this.escapeHtml(sucursal.nombre)}</strong>
        <span>${this.escapeHtml(direccion)}</span>
        <span><strong>Zona:</strong> ${this.escapeHtml(zona)}</span>
        <span><strong>Responsable:</strong> ${this.escapeHtml(responsable)}</span>
        <span><strong>Especialidades:</strong> ${this.escapeHtml(especialidades)}</span>
        <span><strong>Técnicos:</strong> ${this.escapeHtml(tecnicos)}</span>
      </div>
    `;
  }

  private clearSucursalesOverviewMarkers(): void {
    for (const marker of this.sucursalesOverviewMarkers) {
      marker.remove();
    }

    this.sucursalesOverviewMarkers = [];
  }

  private scheduleSucursalesOverviewMapResize(): void {
    if (typeof window === 'undefined' || !this.sucursalesOverviewMap) {
      return;
    }

    if (this.sucursalesOverviewMapResizeTimer !== undefined) {
      window.clearTimeout(this.sucursalesOverviewMapResizeTimer);
    }

    this.sucursalesOverviewMapResizeTimer = window.setTimeout(() => {
      this.sucursalesOverviewMap?.invalidateSize();
    }, 120);
  }

  private refreshSucursalesOverviewMap(): void {
    if (typeof window === 'undefined') {
      return;
    }

    if (!this.sucursalesOverviewData.length) {
      this.destroySucursalesOverviewMap();
      return;
    }

    window.setTimeout(() => this.renderSucursalesOverviewMap(), 0);
  }

  private destroySucursalesOverviewMap(): void {
    if (typeof window !== 'undefined' && this.sucursalesOverviewMapResizeTimer !== undefined) {
      window.clearTimeout(this.sucursalesOverviewMapResizeTimer);
      this.sucursalesOverviewMapResizeTimer = undefined;
    }

    this.clearSucursalesOverviewMarkers();

    if (this.sucursalesOverviewMap) {
      this.sucursalesOverviewMap.remove();
      this.sucursalesOverviewMap = undefined;
    }

    this.sucursalesOverviewMapHost = undefined;
  }

  private escapeHtml(value: string): string {
    return value
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  get userInitials(): string {
    const parts = this.userDisplayName
      .split(' ')
      .map((part) => part.trim())
      .filter(Boolean)
      .slice(0, 2);

    if (!parts.length) {
      return 'AD';
    }

    return parts.map((part) => part.charAt(0).toUpperCase()).join('');
  }

  get recentWorkshops(): WorkshopRegistration[] {
    return this.workshops.slice(0, 4);
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

  get recentTechnicians(): Technician[] {
    return this.technicians.slice(0, 4);
  }

  private isActiveTechnician(technician: Technician): boolean {
    return ACTIVE_TECHNICIAN_STATUSES.includes(technician.status);
  }

  get filteredTechnicians(): Technician[] {
    if (this.technicianFilter === 'todos') {
      return this.technicians;
    }

    if (this.technicianFilter === 'historial') {
      return this.technicians.filter((technician) => technician.status === 'fuera_de_servicio');
    }

    return this.technicians.filter((technician) => this.isActiveTechnician(technician));
  }

  get uniqueZonesCount(): number {
    return new Set(this.workshops.map((workshop) => workshop.zone).filter(Boolean)).size;
  }

  get latestWorkshopLabel(): string {
    const latest = this.workshops[0];
    return latest ? latest.workshop_name : 'Sin ingresos';
  }

  get latestWorkshopDetail(): string {
    const latest = this.workshops[0];
    return latest
      ? `${latest.contact_name} · ${latest.created_at ? new Date(latest.created_at).toLocaleString() : 'Reciente'}`
      : 'Aun no se ha recibido una nueva afiliacion.';
  }

  createEmptyTechnicianForm(): TechnicianFormModel {
    return {
      full_name: '',
      phone: '',
      email: '',
      specialty: '',
      status: 'disponible',
      sucursal_id: this.isAdminSucursalSession ? this.adminSession?.sucursalId ?? null : null,
    };
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

  createEmptySucursalForm(): SucursalFormModel {
    return {
      nombre: '',
      direccion: '',
      zona: '',
      ciudad: 'Santa Cruz',
      latitud: SANTA_CRUZ_DEFAULT_COORDINATES.latitud,
      longitud: SANTA_CRUZ_DEFAULT_COORDINATES.longitud,
      telefono: '',
      responsable: '',
      especialidades: [],
    };
  }

  createEmptyUsuarioEmpresaForm(): UsuarioEmpresaFormModel {
    return {
      email: '',
      full_name: '',
      phone: '',
      password: '',
      role: 'TECNICO',
      sucursal_id: null,
    };
  }

  isSucursalSpecialtySelected(specialty: string): boolean {
    return this.sucursalForm.especialidades.includes(specialty);
  }

  toggleSucursalSpecialty(specialty: string, checked: boolean): void {
    if (!this.isSuperadminTenant) {
      return;
    }

    const next = checked
      ? [...this.sucursalForm.especialidades, specialty]
      : this.sucursalForm.especialidades.filter((value) => value !== specialty);

    this.sucursalForm = {
      ...this.sucursalForm,
      especialidades: Array.from(new Set(next)),
    };
  }

  formatCoordinate(value: number | null): string {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      return '-';
    }

    return value.toFixed(6);
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

  private refreshTechnicianViews(): void {
    this.loadTechnicians();
    this.loadOperationalOverview();
    if (this.isTenantSession) {
      this.loadSucursales();
    }
  }

  selectSection(section: DashboardSection): void {
    if (!this.canAccessSection(section)) {
      this.selectedSection = this.defaultSection;
      return;
    }

    this.selectedSection = section;

    if (section === 'dashboard' && !this.operationalOverview) {
      this.loadOperationalOverview();
    }

    if ((section === 'emergencies' || section === 'reports' || section === 'audit' || section === 'sync') && !this.maintenanceRequests.length) {
      this.loadEmergencies();
    }

    if (section === 'sync') {
      this.selectedSyncRecordId = null;
    }

    if (section === 'emergencies') {
      if (typeof window !== 'undefined') {
        window.setTimeout(() => this.renderSelectedEmergencyMap());
      }
    }

    if (section === 'quotation_requests') {
      this.resetQuotationView();
      this.loadQuotationRequests();
    }

    if (section === 'quotation_history') {
      this.loadQuotationHistory();
    }

    if (section === 'contracted_services') {
      this.contractedServicesView = 'list';
      this.selectedContractedService = null;
      this.contractedAssignmentFeedback = '';
      this.loadContractedServices();
      if (!this.technicians.length) {
        this.loadTechnicians();
      }
    }

    if (section === 'tenants') {
      this.loadTenants();
    }

    if (section === 'sucursales') {
      this.loadSucursales();
      if (typeof window !== 'undefined') {
        window.setTimeout(() => this.refreshSucursalesOverviewMap(), 0);
      }
    }

    if (section === 'usuarios_empresa') {
      if (!this.sucursales.length) this.loadSucursales();
      this.loadUsuariosEmpresa();
    }
  }

  toggleSidebar(): void {
    this.isSidebarCollapsed = !this.isSidebarCollapsed;
    this.persistSidebarCollapsedState();
  }

  logout(): void {
    const confirmed = window.confirm('¿Quieres cerrar sesión?');

    if (!confirmed) {
      return;
    }

    if (typeof window !== 'undefined') {
      this.stopEmergencyRefresh();
      this.clearRealtimeRefreshTimer();
      this.realtimeService.disconnect();
      window.localStorage.removeItem(this.appSessionStorageKey);
      window.sessionStorage.removeItem(this.appSessionStorageKey);
    }

    void this.router.navigate(['/login']);
  }

  private initializeRealtime(): void {
    if (!this.adminSession?.accessToken) {
      return;
    }

    this.realtimeSubscriptions.add(
      this.realtimeService.connectionState$.subscribe((state) => {
        this.realtimeConnectionState = state;
        this.updateRealtimePollingMode(state);
        console.log('[realtime] connectionState', state);
      }),
    );

    this.realtimeSubscriptions.add(
      this.realtimeService.events$.subscribe((event) => {
        this.realtimeEventCount += 1;
        console.log('[realtime]', event);
        if (event.type === 'ws_connected') {
          this.realtimeService.sendPing();
          return;
        }

        const refreshRequest = this.mapRealtimeEventToRefreshRequest(event);
        if (refreshRequest) {
          this.scheduleRealtimeRefresh(refreshRequest);
        }
      }),
    );

    this.realtimeService.connect();
  }

  goToPreviousWorkshopsPage(): void {
    this.workshopsPage = Math.max(1, this.workshopsPage - 1);
  }

  goToNextWorkshopsPage(): void {
    this.workshopsPage = Math.min(this.workshopsTotalPages, this.workshopsPage + 1);
  }

  techniciansByStatus(status: TechnicianStatus): number {
    return this.technicians.filter((technician) => technician.status === status).length;
  }

  activeTechniciansCount(): number {
    return this.technicians.filter((technician) => this.isActiveTechnician(technician)).length;
  }

  statusLabel(status: TechnicianStatus): string {
    if (status === 'fuera_de_servicio') {
      return 'Fuera de servicio';
    }

    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  emergencyStatusLabel(status: EmergencyStatus | null | undefined): string {
    const normalizedStatus = this.normalizeTimelineStatus(status ?? null);
    const step = normalizedStatus
      ? EMERGENCY_TIMELINE_STEPS.find((item) => item.status === normalizedStatus)
      : null;

    if (step) {
      return step.label;
    }

    if (!status) {
      return 'Sin estado';
    }

    return status
      .replaceAll('_', ' ')
      .replace(/\b\w/g, (match) => match.toUpperCase());
  }

  statusFilterGroup(status: EmergencyStatus): MaintenanceFilter {
    if (status === 'rechazado' || status === 'solicitud_cancelada') {
      return 'rechazado';
    }

    if (
      status === 'activo' ||
      status === 'auxilio_asignado' ||
      status === 'auxilio_en_camino' ||
      status === 'tecnico_en_sitio' ||
      status === 'servicio_en_proceso' ||
      status === 'servicio_finalizado'
    ) {
      return 'activo';
    }

    return 'pendiente';
  }

  timelineStepIndex(status: EmergencyTimelineStatus): number {
    return EMERGENCY_TIMELINE_STEPS.findIndex((step) => step.status === status);
  }

  normalizeTimelineStatus(status: EmergencyStatus | null): EmergencyTimelineStatus | null {
    if (!status) {
      return null;
    }

    if (status in LEGACY_TO_TIMELINE_STATUS_MAP) {
      return LEGACY_TO_TIMELINE_STATUS_MAP[status as LegacyEmergencyStatus];
    }

    return status as EmergencyTimelineStatus;
  }

  private isEmergencyReassignmentEntry(item: EmergencyTimelineEntry): boolean {
    return item.status === 'en_revision' && (item.observation ?? '').toLowerCase().includes('solicitud reasignada');
  }

  private isEmergencyNoAlternativeEntry(item: EmergencyTimelineEntry): boolean {
    return (item.observation ?? '').toLowerCase().includes('no se encontro taller alternativo disponible');
  }

  normalizeEmergencyTimeline(
    timeline: EmergencyTimelineResponse,
    request: MaintenanceRequest,
  ): EmergencyTimelineResponse {
    const normalizedTimeline = timeline.timeline.map((entry) => ({
      ...entry,
      status: this.normalizeTimelineStatus(entry.status) ?? 'solicitud_recibida',
    }));

    if (!normalizedTimeline.length) {
      return this.buildFallbackEmergencyTimeline(request);
    }

    return {
      emergency_id: timeline.emergency_id,
      current_status: timeline.current_status,
      timeline: normalizedTimeline,
    };
  }

  buildFallbackEmergencyTimeline(request: MaintenanceRequest): EmergencyTimelineResponse {
    return {
      emergency_id: request.id,
      current_status: request.status,
      timeline: [
        {
          status: this.normalizeTimelineStatus(request.status) ?? 'solicitud_recibida',
          created_at: request.createdAt,
        },
      ],
    };
  }

  nextTimelineStatusOption(status: EmergencyStatus | null | undefined): EmergencyTimelineStatus | null {
    const normalizedStatus = this.normalizeTimelineStatus(status ?? null);

    if (!normalizedStatus || normalizedStatus === 'solicitud_cancelada' || normalizedStatus === 'servicio_finalizado') {
      return null;
    }

    if (normalizedStatus === 'solicitud_recibida') {
      return 'en_revision';
    }

    if (normalizedStatus === 'en_revision') {
      return 'auxilio_asignado';
    }

    if (normalizedStatus === 'auxilio_asignado') {
      return 'auxilio_en_camino';
    }

    if (normalizedStatus === 'auxilio_en_camino') {
      return 'servicio_en_proceso';
    }

    return 'servicio_finalizado';
  }

  formatTimelineActor(role: string | null | undefined, userId: number | null | undefined): string {
    const normalizedRole = (role || '').trim();
    if (!normalizedRole) {
      return 'Sin responsable';
    }

    const label = normalizedRole === 'workshop'
      ? 'Empresa / Taller'
      : normalizedRole === 'admin' || normalizedRole === 'SUPERADMIN_GLOBAL'
        ? 'SUPERADMIN_GLOBAL'
        : normalizedRole;

    return userId ? `${label} #${userId}` : label;
  }

  clientStatusLabel(status: ClientStatus): string {
    return status === 'active' ? 'Activo' : 'Desactivado';
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

  startCreate(): void {
    this.selectedSection = 'technicians';
    if (this.isTenantSession && !this.sucursales.length) {
      this.loadSucursales();
    }
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
    this.selectedSection = 'technicians';
    if (this.isTenantSession && !this.sucursales.length) {
      this.loadSucursales();
    }
    this.showTechnicianForm = true;
    this.editingTechnicianId = technician.id;
    this.technicianFeedback = '';
    this.technicianForm = {
      full_name: technician.full_name,
      phone: technician.phone,
      email: technician.email,
      specialty: technician.specialty,
      status: technician.status,
      sucursal_id: technician.sucursal_id ?? (this.isAdminSucursalSession ? this.adminSession?.sucursalId ?? null : null),
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
      sucursal_id: this.technicianForm.sucursal_id,
    };

    if (!payload.full_name || !payload.phone || !payload.email || !payload.specialty) {
      this.technicianFeedback = 'Completa todos los campos del tecnico antes de guardar.';
      return;
    }

    if (this.isTenantSession && !payload.sucursal_id) {
      this.technicianFeedback = 'Selecciona una sucursal para el técnico.';
      return;
    }

    this.isSavingTechnician = true;
    this.technicianFeedback = '';

    if (this.editingTechnicianId) {
      this.http
        .put<Technician>(`${this.techniciansApiUrl}/${this.editingTechnicianId}`, payload, {
          ...this.buildAuthRequestOptions({
            workshop_id: this.currentWorkshopId,
          }),
        })
        .subscribe({
          next: () => {
            this.isSavingTechnician = false;
            this.technicianFeedback = 'Tecnico actualizado correctamente.';
            this.resetTechnicianForm();
            this.showTechnicianForm = false;
            this.refreshTechnicianViews();
          },
          error: () => {
            this.isSavingTechnician = false;
            this.technicianFeedback = 'No se pudo actualizar el tecnico.';
          },
        });
      return;
    }

    this.http
      .post<Technician>(
        this.techniciansApiUrl,
        payload,
        this.buildAuthRequestOptions({
          workshop_id: this.currentWorkshopId,
        }),
      )
      .subscribe({
        next: () => {
          this.isSavingTechnician = false;
          this.technicianFeedback = 'Tecnico registrado correctamente.';
          this.resetTechnicianForm();
          this.showTechnicianForm = false;
          this.refreshTechnicianViews();
        },
        error: () => {
          this.isSavingTechnician = false;
          this.technicianFeedback = 'No se pudo registrar el tecnico.';
        },
      });
  }

  deleteTechnician(technician: Technician): void {
    const confirmed = window.confirm(`¿Deseas eliminar a ${technician.full_name}?`);

    if (!confirmed) {
      return;
    }

    this.http
      .delete(
        `${this.techniciansApiUrl}/${technician.id}`,
        this.buildAuthRequestOptions({
          workshop_id: this.currentWorkshopId,
        }),
      )
      .subscribe({
        next: () => {
          this.technicianFeedback = 'Tecnico eliminado correctamente.';
          this.refreshTechnicianViews();
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

    this.http
      .put<Technician>(`${this.techniciansApiUrl}/${technician.id}`, {
        workshop_id: technician.workshop_id ?? this.currentWorkshopId,
        full_name: technician.full_name,
        phone: technician.phone,
        email: technician.email,
        specialty: technician.specialty,
        status: nextStatus,
        sucursal_id: technician.sucursal_id,
      }, {
        ...this.buildAuthRequestOptions({
          workshop_id: this.currentWorkshopId,
        }),
      })
      .subscribe({
        next: () => {
          this.refreshTechnicianViews();
        },
      });
  }

  cycleWorkshopApproval(workshop: WorkshopRegistration): void {
    if (this.isUpdatingWorkshopApproval) {
      return;
    }

    const nextStatus: WorkshopApprovalStatus =
      workshop.approval_status === 'pendiente'
        ? 'activo'
        : 'rechazado';

    this.isUpdatingWorkshopApproval = true;

    this.http
      .put<WorkshopRegistration>(`${this.workshopsApiUrl}/${workshop.id}/approval-status`, {
        approval_status: nextStatus,
      }, this.buildAuthRequestOptions())
      .subscribe({
        next: () => {
          this.isUpdatingWorkshopApproval = false;
          this.loadWorkshops();
        },
        error: () => {
          this.isUpdatingWorkshopApproval = false;
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
    const confirmed = window.confirm(`¿Deseas eliminar el taller ${workshop.workshop_name}?`);

    if (!confirmed) {
      return;
    }

    this.http.delete(`${this.workshopsApiUrl}/${workshop.id}`, this.buildAuthRequestOptions()).subscribe({
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
        this.updateWorkshopEditLocation(position.coords.latitude, position.coords.longitude);
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

    const target = this.workshops.find((item) => item.id === this.editingWorkshopId);

    if (!target) {
      this.workshopEditFeedback = 'No se encontró el taller que intentas actualizar.';
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
      this.workshopEditFeedback = 'La nueva contraseña del taller debe tener al menos 6 caracteres.';
      return;
    }

    this.isSavingWorkshop = true;
    this.workshopEditFeedback = '';

    this.http.put<WorkshopRegistration>(`${this.workshopsApiUrl}/${this.editingWorkshopId}`, payload, this.buildAuthRequestOptions()).subscribe({
      next: () => {
        this.isSavingWorkshop = false;
        this.cancelWorkshopEdit();
        this.loadWorkshops();
      },
      error: () => {
        this.isSavingWorkshop = false;
        this.workshopEditFeedback = 'No se pudo actualizar el taller.';
      },
    });
  }

  // ── Tenant CRUD ────────────────────────────────────────────────────────────

  loadTenants(): void {
    if (this.isWorkshopSession) {
      return;
    }
    this.isTenantsLoading = true;
    this.tenantFeedback = '';
    this.http.get<TenantRecord[]>(this.tenantsApiUrl, this.buildAuthRequestOptions()).subscribe({
      next: (rows) => { this.tenants = rows; this.isTenantsLoading = false; },
      error: (err) => {
        this.tenants = [];
        this.isTenantsLoading = false;
        if (err?.status === 401 || err?.status === 403 || err?.error?.detail === 'TOKEN_SIN_TENANT') {
          this.tenantFeedback = 'Tu sesión no tiene JWT válido. Cierra sesión y vuelve a ingresar para ver las organizaciones.';
          this.showTenantForm = true;
        }
      },
    });
  }

  openNewTenantForm(): void {
    this.editingTenantId = null;
    this.tenantForm = { nombre: '', descripcion: '', estado: 'activo' };
    this.tenantFeedback = '';
    this.showTenantForm = true;
  }

  editTenant(tenant: TenantRecord): void {
    this.editingTenantId = tenant.id;
    this.tenantForm = { nombre: tenant.nombre, descripcion: tenant.descripcion ?? '', estado: tenant.estado };
    this.tenantFeedback = '';
    this.showTenantForm = true;
  }

  cancelTenantForm(): void {
    this.showTenantForm = false;
    this.editingTenantId = null;
    this.tenantFeedback = '';
  }

  saveTenant(): void {
    if (!this.tenantForm.nombre.trim()) {
      this.tenantFeedback = 'El nombre es obligatorio.';
      return;
    }
    this.isSavingTenant = true;
    this.tenantFeedback = '';
    const body = { nombre: this.tenantForm.nombre.trim(), descripcion: this.tenantForm.descripcion.trim() || null, estado: this.tenantForm.estado };
    const req = this.editingTenantId
      ? this.http.put<TenantRecord>(`${this.tenantsApiUrl}/${this.editingTenantId}`, body, this.buildAuthRequestOptions())
      : this.http.post<TenantRecord>(this.tenantsApiUrl, body, this.buildAuthRequestOptions());
    req.subscribe({
      next: () => {
        this.isSavingTenant = false;
        this.showTenantForm = false;
        this.editingTenantId = null;
        this.loadTenants();
      },
      error: (err) => {
        this.isSavingTenant = false;
        this.tenantFeedback = err?.error?.detail ?? 'Error al guardar la organización.';
      },
    });
  }

  toggleTenantEstado(tenant: TenantRecord): void {
    if (tenant.id === 1) {
      return;
    }
    const nuevoEstado = tenant.estado === 'activo' ? 'inactivo' : 'activo';
    this.http.patch<TenantRecord>(`${this.tenantsApiUrl}/${tenant.id}/estado?estado=${nuevoEstado}`, {}, this.buildAuthRequestOptions()).subscribe({
      next: () => this.loadTenants(),
      error: (err) => { alert(err?.error?.detail ?? 'Error al cambiar el estado.'); },
    });
  }

  deleteTenant(tenant: TenantRecord): void {
    if (tenant.id === 1) {
      return;
    }
    if (!window.confirm(`¿Eliminar la organización "${tenant.nombre}"? Esta acción no se puede deshacer.`)) {
      return;
    }
    this.http.delete(`${this.tenantsApiUrl}/${tenant.id}`, this.buildAuthRequestOptions()).subscribe({
      next: () => this.loadTenants(),
      error: (err) => { alert(err?.error?.detail ?? 'Error al eliminar la organización.'); },
    });
  }

  private authHeaders(): Record<string, string> {
    const token = this.adminSession?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  private buildAuthRequestOptions(
    params?: Record<string, string | number | null | undefined>,
  ): {
    headers?: Record<string, string>;
    params?: Record<string, string>;
  } {
    const normalizedParams = Object.entries(params ?? {}).reduce<Record<string, string>>((acc, [key, value]) => {
      if (value !== null && value !== undefined && value !== '') {
        acc[key] = String(value);
      }
      return acc;
    }, {});
    const headers = this.authHeaders();

    return {
      ...(Object.keys(headers).length ? { headers } : {}),
      ...(Object.keys(normalizedParams).length ? { params: normalizedParams } : {}),
    };
  }

  // ── Workshops load ─────────────────────────────────────────────────────────

  loadWorkshops(): void {
    if (this.isWorkshopSession) {
      this.workshops = [];
      this.workshopsPage = 1;
      this.isLoading = false;
      this.refreshStats();
      return;
    }

    this.isLoading = true;

    this.http.get<WorkshopRegistration[]>(this.workshopsApiUrl, this.buildAuthRequestOptions()).subscribe({
      next: (workshops) => {
        this.workshops = workshops;
        this.workshopsPage = 1;
        this.isLoading = false;
        this.refreshStats();
      },
      error: () => {
        this.workshops = [];
        this.workshopsPage = 1;
        this.isLoading = false;
        this.refreshStats();
      },
    });
  }

  loadTechnicians(): void {
    if (this.isGlobalAdminSession) {
      this.technicians = [];
      this.isTechniciansLoading = false;
      this.refreshStats();
      return;
    }

    if (this.isTenantSession && !this.sucursales.length) {
      this.loadSucursales();
    }

    this.isTechniciansLoading = true;

    this.http
      .get<Technician[]>(this.techniciansApiUrl, {
        ...this.buildAuthRequestOptions({
          workshop_id: this.currentWorkshopId,
        }),
      })
      .subscribe({
        next: (technicians) => {
          this.technicians = technicians;
          this.isTechniciansLoading = false;
          this.refreshStats();
        },
        error: () => {
          this.technicians = [];
          this.isTechniciansLoading = false;
          this.refreshStats();
        },
      });
  }

  loadClients(): void {
    if (this.isWorkshopSession) {
      this.clients = [];
      this.isClientsLoading = false;
      this.refreshStats();
      return;
    }

    this.isClientsLoading = true;

    this.http.get<Client[]>(this.clientsApiUrl, this.buildAuthRequestOptions()).subscribe({
      next: (clients) => {
        this.clients = clients;
        this.isClientsLoading = false;
        this.refreshStats();
      },
      error: () => {
        this.clients = [];
        this.isClientsLoading = false;
        this.refreshStats();
      },
    });
  }

  loadOperationalOverview(): void {
    this.isOperationalOverviewLoading = true;

    this.http
      .get<DashboardOperationalOverview>(this.dashboardOverviewApiUrl, {
        ...this.buildAuthRequestOptions({
          workshop_id: this.currentWorkshopId,
        }),
      })
      .subscribe({
        next: (overview) => {
          this.operationalOverview = overview;
          this.isOperationalOverviewLoading = false;
          this.refreshStats();
        },
        error: () => {
          this.operationalOverview = null;
          this.isOperationalOverviewLoading = false;
          this.refreshStats();
        },
      });
  }

  toggleClientStatus(client: Client): void {
    const nextStatus: ClientStatus = client.status === 'active' ? 'suspended' : 'active';

    this.http
      .put<Client>(`${this.clientsApiUrl}/${client.id}/status`, {
        status: nextStatus,
      }, this.buildAuthRequestOptions())
      .subscribe({
        next: () => {
          this.loadClients();
        },
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

    const payload = {
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

    this.http.put<Client>(`${this.clientsApiUrl}/${this.editingClientId}`, payload, this.buildAuthRequestOptions()).subscribe({
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

    this.http.delete(`${this.clientsApiUrl}/${this.clientPendingDelete.id}`, this.buildAuthRequestOptions()).subscribe({
      next: () => {
        this.cancelClientDelete();
        this.loadClients();
      },
      error: () => {
        window.alert('No se pudo eliminar el cliente.');
      },
    });
  }

  private readAdminSession(): AppSession | null {
    if (typeof window === 'undefined') {
      return null;
    }

    const raw =
      window.localStorage.getItem(this.appSessionStorageKey) ||
      window.sessionStorage.getItem(this.appSessionStorageKey);

    if (!raw) {
      return null;
    }

    const session = parseStoredSession(raw);

    if (!session) {
      clearStoredSession();
      return null;
    }

    return session;
  }

  private readSidebarCollapsedState(): boolean {
    if (typeof window === 'undefined') {
      return false;
    }

    return window.localStorage.getItem(this.dashboardSidebarStorageKey) === 'true';
  }

  private persistSidebarCollapsedState(): void {
    if (typeof window === 'undefined') {
      return;
    }

    window.localStorage.setItem(this.dashboardSidebarStorageKey, String(this.isSidebarCollapsed));
  }

  private refreshStats(): void {
    if (this.operationalOverview?.kpis?.length) {
      this.stats = this.operationalOverview.kpis.map((item) => ({
        label: item.label,
        value: item.value,
        detail: item.detail,
        trend: item.trend,
        tone: item.tone,
      }));
      return;
    }

    this.stats = this.stats.map((stat) => {
      if (stat.label === 'Talleres registrados') {
        return {
          ...stat,
          value: String(this.workshops.length),
          detail: this.workshops.length
            ? 'Solicitudes recibidas desde el formulario de afiliacion.'
            : 'Aun no se recibieron solicitudes de taller.',
        };
      }

      if (stat.label === 'Tecnicos disponibles') {
        return {
          ...stat,
          value: String(this.activeTechniciansCount()),
          detail: this.technicians.length
            ? 'Estado actualizado segun el tecnico registrado en el panel.'
            : 'Aun no se registraron tecnicos en el sistema.',
        };
      }

      if (stat.label === 'Clientes activos') {
        const activeClients = this.clients.filter((client) => client.status === 'active').length;
        return {
          ...stat,
          value: String(activeClients),
          detail: this.clients.length
            ? 'Clientes con acceso habilitado para autenticacion movil.'
            : 'Aun no se registraron clientes en el sistema.',
        };
      }

      if (stat.label === 'Cobertura') {
        return {
          ...stat,
          value: `${this.uniqueZonesCount || 0} zonas`,
          detail: this.uniqueZonesCount
            ? 'Cobertura detectada en zonas con alta circulacion y demanda.'
            : 'Sin zonas activas registradas todavia.',
        };
      }

      return stat;
    });
  }

  // ── Sincronización offline ──────────────────────────────────────────────

  get syncedRequests(): MaintenanceRequest[] {
    return this.maintenanceRequests.filter((r) => r.localId != null);
  }

  get syncQueueRequests(): MaintenanceRequest[] {
    return this.syncedRequests.filter((r) => this.statusFilterGroup(r.status) === 'pendiente');
  }

  get syncErrorRequests(): MaintenanceRequest[] {
    return this.syncedRequests.filter(
      (r) => r.status === 'rechazado' || r.status === 'solicitud_cancelada',
    );
  }

  get syncStats(): { pending: number; syncedToday: number; withErrors: number; total: number } {
    const all = this.syncedRequests;
    const todayStr = new Date().toDateString();
    return {
      pending: all.filter((r) => this.statusFilterGroup(r.status) === 'pendiente').length,
      syncedToday: all.filter((r) => new Date(r.createdAt).toDateString() === todayStr).length,
      withErrors: all.filter((r) => r.status === 'rechazado' || r.status === 'solicitud_cancelada').length,
      total: all.length,
    };
  }

  get selectedSyncRecord(): MaintenanceRequest | null {
    const all = this.syncedRequests;
    if (!all.length) return null;
    if (this.selectedSyncRecordId != null) {
      return all.find((r) => r.id === this.selectedSyncRecordId) ?? all[0];
    }
    return all[0];
  }

  get selectedSyncErrorRecord(): MaintenanceRequest | null {
    const all = this.syncErrorRequests;
    if (!all.length) return null;
    if (this.selectedSyncErrorRecordId != null) {
      return all.find((r) => r.id === this.selectedSyncErrorRecordId) ?? all[0];
    }
    return all[0];
  }

  selectSyncRecord(id: number): void {
    this.selectedSyncRecordId = id;
  }

  selectSyncErrorRecord(id: number): void {
    this.selectedSyncErrorRecordId = id;
  }

  selectSyncTab(tab: SyncTab): void {
    this.syncTab = tab;
    this.selectedSyncErrorRecordId = null;
    this.selectedSyncRecordId = null;
  }

  syncErrorLabel(status: EmergencyStatus | null | undefined): string {
    if (status === 'solicitud_cancelada') return 'Solicitud cancelada por el taller';
    if (status === 'rechazado') return 'Solicitud rechazada por el taller';
    return 'Error de procesamiento en el servidor';
  }

  syncActionRecommendation(status: EmergencyStatus | null | undefined): string {
    if (status === 'solicitud_cancelada' || status === 'rechazado') {
      return 'Verificar con el taller el motivo del rechazo. El cliente puede registrar una nueva solicitud desde la app móvil.';
    }
    return 'Contactar soporte técnico si el problema persiste.';
  }

  get quotationRequestsBadgeCount(): number {
    return this.quotationRequests.filter((r) => r.status === 'abierto').length;
  }

  get quotationActiveOffersCount(): number {
    return this.quotationOffers.filter((o) => o.status === 'enviada' || o.status === 'actualizada').length;
  }

  get contractedServicesBadgeCount(): number {
    return this.contractedServices.filter((s) => s.emergency_status === 'solicitud_recibida' || s.emergency_status === 'en_revision').length;
  }

  loadQuotationRequests(): void {
    if (this.isTenantQuotationSession) {
      this.isQuotationRequestsLoading = true;
      this.http.get<QuotationRequest[]>(
        `${API_BASE_URL}/cotizaciones/tenant/solicitudes`,
        this.buildAuthRequestOptions(),
      ).subscribe({
        next: (rows) => {
          this.quotationRequests = rows;
          this.isQuotationRequestsLoading = false;
        },
        error: () => {
          this.quotationRequests = [];
          this.isQuotationRequestsLoading = false;
        },
      });
      return;
    }

    const workshopId = this.currentWorkshopId;
    if (!workshopId) {
      this.resolveWorkshopContext(() => this.loadQuotationRequests());
      return;
    }
    this.isQuotationRequestsLoading = true;
    this.http.get<QuotationRequest[]>(
      `${API_BASE_URL}/cotizaciones/taller/${workshopId}`,
      this.buildAuthRequestOptions(),
    ).subscribe({
      next: (rows) => {
        this.quotationRequests = rows;
        this.isQuotationRequestsLoading = false;
        if (!rows.length && this.resolvedWorkshopId == null) {
          this.resolveWorkshopContext(() => this.loadQuotationRequests(), true);
        }
      },
      error: () => {
        this.isQuotationRequestsLoading = false;
      },
    });
  }

  loadQuotationHistory(): void {
    if (this.isTenantQuotationSession) {
      this.isQuotationHistoryLoading = true;
      this.http.get<QuotationOffer[]>(
        `${API_BASE_URL}/cotizaciones/tenant/historial`,
        this.buildAuthRequestOptions(),
      ).subscribe({
        next: (rows) => {
          this.quotationOffers = rows;
          this.isQuotationHistoryLoading = false;
        },
        error: () => {
          this.quotationOffers = [];
          this.isQuotationHistoryLoading = false;
        },
      });
      return;
    }

    const workshopId = this.currentWorkshopId;
    if (!workshopId) {
      this.resolveWorkshopContext(() => this.loadQuotationHistory());
      return;
    }
    this.isQuotationHistoryLoading = true;
    this.http.get<QuotationOffer[]>(
      `${API_BASE_URL}/cotizaciones/taller/${workshopId}/historial`,
      this.buildAuthRequestOptions(),
    ).subscribe({
      next: (rows) => {
        this.quotationOffers = rows;
        this.isQuotationHistoryLoading = false;
      },
      error: () => {
        this.isQuotationHistoryLoading = false;
      },
    });
  }

  loadContractedServices(): void {
    if (this.isTenantQuotationSession) {
      this.isContractedServicesLoading = true;
      this.http.get<ContractedService[]>(
        `${API_BASE_URL}/cotizaciones/tenant/servicios-contratados`,
        this.buildAuthRequestOptions(),
      ).subscribe({
        next: (rows) => {
          this.contractedServices = rows;
          this.isContractedServicesLoading = false;
          if (this.selectedContractedService) {
            const updated = rows.find((s) => s.id === this.selectedContractedService!.id);
            if (updated) this.selectedContractedService = updated;
          }
        },
        error: () => {
          this.contractedServices = [];
          this.isContractedServicesLoading = false;
        },
      });
      return;
    }

    const workshopId = this.currentWorkshopId;
    if (!workshopId) {
      this.resolveWorkshopContext(() => this.loadContractedServices());
      return;
    }
    this.isContractedServicesLoading = true;
    this.http.get<ContractedService[]>(
      `${API_BASE_URL}/cotizaciones/taller/${workshopId}/servicios-contratados`,
      this.buildAuthRequestOptions(),
    ).subscribe({
      next: (rows) => {
        this.contractedServices = rows;
        this.isContractedServicesLoading = false;
        if (this.selectedContractedService) {
          const updated = rows.find((s) => s.id === this.selectedContractedService!.id);
          if (updated) this.selectedContractedService = updated;
        }
      },
      error: () => {
        this.isContractedServicesLoading = false;
      },
    });
  }

  get contractedServiceAssignableTechnicians(): Technician[] {
    return this.technicians.filter((t) => t.status === 'disponible');
  }

  openContractedServiceDetail(service: ContractedService): void {
    this.selectedContractedService = service;
    this.contractedServicesView = 'detail';
    this.selectedContractedTechnicianId = null;
    this.contractedAssignmentFeedback = '';
    this.loadTechnicians();
  }

  closeContractedServiceDetail(): void {
    this.selectedContractedService = null;
    this.contractedServicesView = 'list';
    this.contractedAssignmentFeedback = '';
  }

  acceptContractedEmergency(): void {
    const svc = this.selectedContractedService;
    if (!svc?.emergency_id || this.isUpdatingContractedStatus) return;
    if (!this.currentWorkshopId) return;
    this.isUpdatingContractedStatus = true;
    this.contractedAssignmentFeedback = '';
    this.http
      .put<EmergencyReport>(
        `${this.emergenciesApiUrl}/${svc.emergency_id}/status`,
        { emergency_status: 'activo' },
        this.buildAuthRequestOptions({
          workshop_id: this.currentWorkshopId,
        }),
      )
      .subscribe({
        next: (report) => {
          this.isUpdatingContractedStatus = false;
          this.contractedAssignmentFeedback = 'Emergencia aceptada. Selecciona un técnico para asignar.';
          const updated = { ...svc, emergency_status: report.emergency_status ?? 'activo' };
          this.selectedContractedService = updated;
          this.contractedServices = this.contractedServices.map((s) => s.id === svc.id ? updated : s);
        },
        error: () => {
          this.isUpdatingContractedStatus = false;
          this.contractedAssignmentFeedback = 'No se pudo cambiar el estado de la emergencia.';
        },
      });
  }

  assignContractedTechnician(): void {
    const svc = this.selectedContractedService;
    if (!svc?.emergency_id || !this.selectedContractedTechnicianId || this.isAssigningContractedTechnician) return;
    if (!this.currentWorkshopId) return;
    this.isAssigningContractedTechnician = true;
    this.contractedAssignmentFeedback = '';
    this.http
      .put<EmergencyReport>(
        `${this.emergenciesApiUrl}/${svc.emergency_id}/technician-assignment`,
        { technician_id: this.selectedContractedTechnicianId },
        this.buildAuthRequestOptions({
          workshop_id: this.currentWorkshopId,
        }),
      )
      .subscribe({
        next: (report) => {
          this.isAssigningContractedTechnician = false;
          const techName = report.assigned_technician_name ?? 'Técnico';
          this.contractedAssignmentFeedback = `✓ Técnico "${techName}" asignado correctamente.`;
          const updated = {
            ...svc,
            emergency_status: report.emergency_status ?? svc.emergency_status,
          };
          this.selectedContractedService = updated;
          this.contractedServices = this.contractedServices.map((s) => s.id === svc.id ? updated : s);
          this.loadTechnicians();
        },
        error: (err) => {
          this.isAssigningContractedTechnician = false;
          const detail: string = err?.error?.detail ?? '';
          this.contractedAssignmentFeedback = detail
            ? `No se pudo asignar: ${detail}`
            : 'No se pudo asignar el técnico. Verifica que esté disponible.';
          this.loadTechnicians();
        },
      });
  }

  contractedServiceEmergencyStatusLabel(status: string | null): string {
    const labels: Record<string, string> = {
      solicitud_recibida: 'Solicitud recibida',
      en_revision: 'En revisión',
      auxilio_asignado: 'Auxilio asignado',
      auxilio_en_camino: 'En camino',
      tecnico_en_sitio: 'Técnico en sitio',
      servicio_en_proceso: 'En atención',
      servicio_finalizado: 'Finalizado',
      solicitud_cancelada: 'Cancelada',
      rechazado: 'Rechazada',
    };
    return status ? (labels[status] ?? status) : '—';
  }

  openQuotationDetail(req: QuotationRequest): void {
    const workshopId = this.currentWorkshopId;
    this.selectedQuotationRequest = req;
    this.selectedWorkshopOffer = null;
    this.selectedQuotationOffers = [];
    this.quotationView = 'detail';
    this.selectedQuotationEmergency = null;
    this.quotationEmergencyPhotoUrls = [];
    this.quotationEmergencyAudioUrl = null;
    this.quotationEmergencyMapEmbedUrl = null;
    this.quotationEmergencyMapExternalUrl = null;

    if (req.emergency_id) {
      this.isQuotationEmergencyLoading = true;
      this.http.get<EmergencyReport>(
        `${API_BASE_URL}/emergencias/${req.emergency_id}`,
        this.buildAuthRequestOptions(),
      ).subscribe({
        next: (report) => {
          this.selectedQuotationEmergency = report;
          this.quotationEmergencyPhotoUrls = this.getEmergencyPhotoUrls(report);
          this.quotationEmergencyAudioUrl = this.normalizeBackendAssetUrl(report.audio_url);
          this.quotationEmergencyMapEmbedUrl = this.buildEmergencyMapEmbedUrl(report.latitude, report.longitude);
          this.quotationEmergencyMapExternalUrl = this.buildEmergencyMapExternalUrl(report.latitude, report.longitude);
          this.isQuotationEmergencyLoading = false;
        },
        error: () => {
          this.isQuotationEmergencyLoading = false;
        },
      });
    }

    if (this.isTenantQuotationSession || workshopId) {
      this.http.get<QuotationOffer[]>(
        `${API_BASE_URL}/cotizaciones/${req.id}/propuestas`,
        this.buildAuthRequestOptions(),
      ).subscribe({
        next: (offers) => {
          this.selectedQuotationOffers = offers;
          this.selectedWorkshopOffer = offers.find((offer) => offer.workshop_id === workshopId) ?? null;
        },
        error: () => {
          this.selectedQuotationOffers = [];
          this.selectedWorkshopOffer = null;
        },
      });
    }
  }

  get maxValidityDays(): number {
    const expiresAt = this.selectedQuotationRequest?.expires_at;
    if (!expiresAt) return 365;
    const remaining = Math.floor((new Date(expiresAt).getTime() - Date.now()) / 86_400_000);
    return Math.max(1, remaining);
  }

  openQuotationOfferForm(): void {
    this.quotationOfferForm = this.selectedWorkshopOffer
      ? this.createQuotationOfferFormFromOffer(this.selectedWorkshopOffer)
      : this.createEmptyQuotationOfferForm();
    const max = this.maxValidityDays;
    if ((this.quotationOfferForm.validity_days ?? 3) > max) {
      this.quotationOfferForm.validity_days = max;
    }
    this.quotationOfferFeedback = '';
    this.quotationView = 'offer_form';
  }

  submitQuotationOffer(): void {
    const req = this.selectedQuotationRequest;
    const workshopId = this.currentWorkshopId;
    if (!req || !workshopId) return;

    const price = this.quotationOfferForm.price;
    if (price === null || price === undefined || price < 0) {
      this.quotationOfferFeedback = 'El precio es requerido y debe ser mayor o igual a 0.';
      return;
    }

    const desc = this.quotationOfferForm.service_description.trim();
    if (desc.length < 3) {
      this.quotationOfferFeedback = 'La descripción del servicio es requerida (mínimo 3 caracteres).';
      return;
    }

    this.isSubmittingOffer = true;
    this.quotationOfferFeedback = '';

    const payload = {
      workshop_id: workshopId,
      price,
      service_description: desc,
      spare_parts: this.quotationOfferForm.spare_parts.trim() || null,
      labor_detail: this.quotationOfferForm.labor_detail.trim() || null,
      labor_cost: this.quotationOfferForm.labor_cost,
      spare_parts_cost: this.quotationOfferForm.spare_parts_cost,
      estimated_service_time: this.quotationOfferForm.estimated_service_time.trim() || null,
      estimated_arrival_time: this.quotationOfferForm.estimated_arrival_time.trim() || null,
      warranty: this.quotationOfferForm.warranty.trim() || null,
      validity_days: this.quotationOfferForm.validity_days ?? 3,
      observations: this.quotationOfferForm.observations.trim() || null,
      condiciones_servicio: this.quotationOfferForm.condiciones_servicio.trim() || null,
    };

    const request$ = this.selectedWorkshopOffer
      ? this.http.put<QuotationOffer>(
          `${API_BASE_URL}/cotizaciones/${req.id}/propuestas/${this.selectedWorkshopOffer.id}`,
          payload,
          this.buildAuthRequestOptions(),
        )
      : this.http.post<QuotationOffer>(
          `${API_BASE_URL}/cotizaciones/${req.id}/propuestas`,
          payload,
          this.buildAuthRequestOptions(),
        );

    request$.subscribe({
      next: (offer) => {
        this.lastSubmittedOffer = offer;
        this.selectedWorkshopOffer = offer;
        this.isSubmittingOffer = false;
        this.quotationView = 'confirmation';
        this.loadQuotationRequests();
        this.loadQuotationHistory();
      },
      error: (err: { error?: { detail?: unknown } }) => {
        this.isSubmittingOffer = false;
        const detail = err?.error?.detail;
        this.quotationOfferFeedback = typeof detail === 'string' ? detail : 'Error al enviar la cotización. Intente nuevamente.';
      },
    });
  }

  resetQuotationView(): void {
    this.quotationView = 'list';
    this.selectedQuotationRequest = null;
    this.selectedQuotationEmergency = null;
    this.quotationEmergencyPhotoUrls = [];
    this.quotationEmergencyAudioUrl = null;
    this.quotationEmergencyMapEmbedUrl = null;
    this.quotationEmergencyMapExternalUrl = null;
    this.lastSubmittedOffer = null;
    this.selectedWorkshopOffer = null;
    this.selectedQuotationOffers = [];
    this.quotationOfferFeedback = '';
  }

  private createEmptyQuotationOfferForm(): QuotationOfferFormModel {
    return {
      price: null,
      service_description: '',
      spare_parts: '',
      labor_detail: '',
      labor_cost: null,
      spare_parts_cost: null,
      estimated_service_time: '',
      estimated_arrival_time: '',
      warranty: '',
      validity_days: 3,
      observations: '',
      condiciones_servicio: '',
    };
  }

  private createQuotationOfferFormFromOffer(offer: QuotationOffer): QuotationOfferFormModel {
    return {
      price: offer.price ?? null,
      service_description: offer.service_description ?? '',
      spare_parts: offer.spare_parts ?? '',
      labor_detail: offer.labor_detail ?? '',
      labor_cost: offer.labor_cost ?? null,
      spare_parts_cost: offer.spare_parts_cost ?? null,
      estimated_service_time: offer.estimated_service_time ?? '',
      estimated_arrival_time: offer.estimated_arrival_time ?? '',
      warranty: offer.warranty ?? '',
      validity_days: offer.validity_days ?? 3,
      observations: offer.observations ?? '',
      condiciones_servicio: offer.condiciones_servicio ?? '',
    };
  }

  quotationRequestStateLabel(req: QuotationRequest): string {
    if (req.status === 'expirado') return 'Cotización vencida';
    if (req.status === 'seleccionado') return 'Cotización aceptada';
    return 'Cotización solicitada';
  }

  quotationInvitationStateLabel(req: QuotationRequest): string {
    if (req.workshop_invitation_status === 'respondido') return 'Cotización enviada';
    return 'Pendiente de respuesta';
  }

  quotationOfferStateLabel(offer: QuotationOffer): string {
    if (offer.status === 'enviada') return 'Cotización enviada';
    if (offer.status === 'actualizada') return 'Cotización actualizada';
    if (offer.status === 'aceptada') return 'Cotización aceptada';
    if (offer.status === 'rechazada') return 'Cotización rechazada';
    if (offer.status === 'expirado') return 'Cotización vencida';
    return offer.status;
  }

  // ── SUCURSALES ────────────────────────────────────────────────────────────

  loadSucursales(): void {
    this.isSucursalesLoading = true;
    this.sucursalesFeedback = '';
    this.http
      .get<SucursalRecord[]>(`${API_BASE_URL}/sucursales`, { headers: this.tenantAuthHeaders })
      .subscribe({
        next: (data) => {
          this.sucursales = data;
          this.isSucursalesLoading = false;
          this.refreshSucursalesOverviewMap();
        },
        error: (err: { error?: { detail?: unknown } }) => {
          this.isSucursalesLoading = false;
          this.refreshSucursalesOverviewMap();
          const detail = err?.error?.detail;
          this.sucursalesFeedback = typeof detail === 'string' ? detail : 'Error al cargar sucursales.';
        },
      });
  }

  openNuevaSucursal(): void {
    if (!this.isSuperadminTenant) {
      return;
    }
    this.destroySucursalMap();
    this.editingSucursalId = null;
    this.sucursalForm = this.createEmptySucursalForm();
    this.sucursalesFeedback = '';
    this.resetSucursalLocationState();
    this.showSucursalForm = true;
  }

  editSucursal(suc: SucursalRecord): void {
    if (!this.isSuperadminTenant) {
      return;
    }
    this.destroySucursalMap();
    this.editingSucursalId = suc.id;
    this.sucursalForm = {
      nombre: suc.nombre,
      direccion: suc.direccion ?? '',
      zona: this.normalizeSucursalZoneValue(suc.zona),
      ciudad: suc.ciudad,
      latitud: suc.latitud ?? SANTA_CRUZ_DEFAULT_COORDINATES.latitud,
      longitud: suc.longitud ?? SANTA_CRUZ_DEFAULT_COORDINATES.longitud,
      telefono: suc.telefono ?? '',
      responsable: suc.responsable ?? '',
      especialidades: [...(suc.especialidades?.length ? suc.especialidades : suc.workshop_specialty ? [suc.workshop_specialty] : [])],
    };
    this.sucursalesFeedback = '';
    this.resetSucursalLocationState();
    this.sucursalDetectedAddress = this.sucursalForm.direccion.trim();
    this.sucursalLastAutofilledAddress = this.sucursalForm.direccion.trim();
    this.showSucursalForm = true;
  }

  cancelSucursalForm(): void {
    this.destroySucursalMap();
    this.showSucursalForm = false;
    this.editingSucursalId = null;
    this.sucursalesFeedback = '';
    this.resetSucursalLocationState();
  }

  handleSucursalAddressManualInput(): void {
    const currentValue = this.sucursalForm.direccion.trim();
    this.sucursalAddressTouchedManually =
      currentValue.length > 0 && currentValue !== this.sucursalLastAutofilledAddress;
  }

  get canApplySucursalDetectedAddress(): boolean {
    return (
      !!this.sucursalDetectedAddress &&
      this.sucursalAddressTouchedManually &&
      this.sucursalForm.direccion.trim() !== this.sucursalDetectedAddress
    );
  }

  applySucursalDetectedAddress(): void {
    if (!this.sucursalDetectedAddress) {
      return;
    }

    this.sucursalForm = {
      ...this.sucursalForm,
      direccion: this.sucursalDetectedAddress,
    };
    this.sucursalLastAutofilledAddress = this.sucursalDetectedAddress;
    this.sucursalAddressTouchedManually = false;
    this.sucursalLocationMessage = '';
  }

  locateSucursalCurrentPosition(): void {
    this.sucursalLocationMessage = '';

    if (!this.isSecureContext) {
      this.sucursalLocationMessage =
        'La ubicación automática del navegador solo funciona en HTTPS o en localhost. Usa el mapa manualmente o abre el sitio con HTTPS.';
      return;
    }

    if (!navigator.geolocation) {
      this.sucursalLocationMessage = 'Tu navegador no soporta geolocalización.';
      return;
    }

    this.isSucursalLocationLocating = true;

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;
        this.updateSucursalSelectedLocation(latitude, longitude);
        this.renderSucursalMap(true);
        this.isSucursalLocationLocating = false;
      },
      () => {
        this.isSucursalLocationLocating = false;
        this.sucursalLocationMessage =
          'No se pudo obtener tu ubicación actual. Revisa los permisos del navegador.';
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      },
    );
  }

  saveSucursal(): void {
    if (!this.isSuperadminTenant) {
      return;
    }
    if (!this.sucursalForm.nombre.trim()) {
      this.sucursalesFeedback = 'El nombre de la sucursal es obligatorio.';
      return;
    }
    if (!this.sucursalForm.zona.trim()) {
      this.sucursalesFeedback = 'Debes seleccionar una zona.';
      return;
    }
    if (!this.sucursalForm.especialidades.length) {
      this.sucursalesFeedback = 'Selecciona al menos una especialidad.';
      return;
    }
    const body = {
      nombre: this.sucursalForm.nombre.trim(),
      direccion: this.sucursalForm.direccion.trim() || null,
      zona: this.sucursalForm.zona.trim(),
      ciudad: this.sucursalForm.ciudad.trim() || 'Santa Cruz',
      latitud: this.sucursalForm.latitud,
      longitud: this.sucursalForm.longitud,
      telefono: this.sucursalForm.telefono.trim() || null,
      responsable: this.sucursalForm.responsable.trim() || null,
      especialidades: [...this.sucursalForm.especialidades],
    };
    const headers = this.tenantAuthHeaders;
    const req$ = this.editingSucursalId
      ? this.http.put<SucursalRecord>(`${API_BASE_URL}/sucursales/${this.editingSucursalId}`, body, { headers })
      : this.http.post<SucursalRecord>(`${API_BASE_URL}/sucursales`, body, { headers });

    req$.subscribe({
      next: () => {
        this.sucursalesFeedback = this.editingSucursalId ? 'Sucursal actualizada.' : 'Sucursal creada.';
        this.cancelSucursalForm();
        this.loadSucursales();
      },
      error: (err: { error?: { detail?: unknown } }) => {
        const detail = err?.error?.detail;
        this.sucursalesFeedback = typeof detail === 'string' ? detail : 'Error al guardar la sucursal.';
      },
    });
  }

  deleteSucursal(id: number): void {
    if (!this.isSuperadminTenant) return;
    if (!window.confirm('¿Eliminar esta sucursal? Esta acción no se puede deshacer.')) return;
    this.http
      .delete<void>(`${API_BASE_URL}/sucursales/${id}`, { headers: this.tenantAuthHeaders })
      .subscribe({
        next: () => this.loadSucursales(),
        error: (err: { error?: { detail?: unknown } }) => {
          const detail = err?.error?.detail;
          this.sucursalesFeedback = typeof detail === 'string' ? detail : 'Error al eliminar la sucursal.';
        },
      });
  }

  // ── USUARIOS DE LA EMPRESA ────────────────────────────────────────────────

  loadUsuariosEmpresa(): void {
    this.isUsuariosEmpresaLoading = true;
    this.usuariosEmpresaFeedback = '';
    this.http
      .get<UsuarioEmpresaRecord[]>(`${API_BASE_URL}/tenant/usuarios`, { headers: this.tenantAuthHeaders })
      .subscribe({
        next: (data) => {
          this.usuariosEmpresa = data;
          this.isUsuariosEmpresaLoading = false;
        },
        error: (err: { error?: { detail?: unknown } }) => {
          this.isUsuariosEmpresaLoading = false;
          const detail = err?.error?.detail;
          this.usuariosEmpresaFeedback = typeof detail === 'string' ? detail : 'Error al cargar usuarios.';
        },
      });
  }

  openNuevoUsuarioEmpresa(): void {
    if (!this.isSuperadminTenant) {
      return;
    }
    this.editingUsuarioEmpresaId = null;
    this.usuarioEmpresaForm = this.createEmptyUsuarioEmpresaForm();
    this.usuarioEmpresaNameTouchedManually = false;
    this.usuarioEmpresaEmailTouchedManually = false;
    this.usuariosEmpresaFeedback = '';
    this.showUsuarioEmpresaForm = true;
  }

  editUsuarioEmpresa(usr: UsuarioEmpresaRecord): void {
    if (!this.isSuperadminTenant) {
      return;
    }
    this.editingUsuarioEmpresaId = usr.id;
    this.usuarioEmpresaForm = {
      email: usr.email,
      full_name: usr.full_name,
      phone: usr.phone ?? '',
      password: '',
      role: usr.role,
      sucursal_id: usr.sucursal_id ?? null,
    };
    this.usuarioEmpresaNameTouchedManually = true;
    this.usuarioEmpresaEmailTouchedManually = true;
    this.usuariosEmpresaFeedback = '';
    this.showUsuarioEmpresaForm = true;
  }

  cancelUsuarioEmpresaForm(): void {
    this.showUsuarioEmpresaForm = false;
    this.editingUsuarioEmpresaId = null;
    this.usuarioEmpresaForm = this.createEmptyUsuarioEmpresaForm();
    this.usuarioEmpresaNameTouchedManually = false;
    this.usuarioEmpresaEmailTouchedManually = false;
    this.usuariosEmpresaFeedback = '';
  }

  handleUsuarioEmpresaNameInput(): void {
    this.usuarioEmpresaNameTouchedManually = true;
  }

  handleUsuarioEmpresaEmailInput(): void {
    this.usuarioEmpresaEmailTouchedManually = true;
  }

  handleUsuarioEmpresaRoleChange(): void {
    if (this.usuarioEmpresaForm.role !== 'ADMIN_SUCURSAL') {
      return;
    }
    this.applyUsuarioEmpresaSucursalSuggestions();
  }

  handleUsuarioEmpresaSucursalChange(): void {
    this.applyUsuarioEmpresaSucursalSuggestions();
  }

  usuarioEmpresaSucursalName(sucursalId: number | null): string {
    if (sucursalId === null) {
      return '—';
    }

    return this.sucursales.find((sucursal) => sucursal.id === sucursalId)?.nombre ?? `Sucursal #${sucursalId}`;
  }

  private applyUsuarioEmpresaSucursalSuggestions(): void {
    if (this.usuarioEmpresaForm.role !== 'ADMIN_SUCURSAL') {
      return;
    }

    const sucursal = this.sucursales.find((item) => item.id === this.usuarioEmpresaForm.sucursal_id);
    if (!sucursal) {
      return;
    }

    const suggestedName = (sucursal.responsable || '').trim();
    const suggestedEmail = this.buildUsuarioEmpresaSuggestedEmail(suggestedName);

    if (suggestedName && !this.usuarioEmpresaNameTouchedManually) {
      this.usuarioEmpresaForm = {
        ...this.usuarioEmpresaForm,
        full_name: suggestedName,
      };
    }

    if (suggestedEmail && !this.usuarioEmpresaEmailTouchedManually && !this.editingUsuarioEmpresaId) {
      this.usuarioEmpresaForm = {
        ...this.usuarioEmpresaForm,
        email: suggestedEmail,
      };
    }
  }

  private buildUsuarioEmpresaSuggestedEmail(fullName: string): string {
    const local = this.slugifyForEmail(fullName).replaceAll('.', ' ').trim().replace(/\s+/g, '.');
    if (!local) {
      return '';
    }

    const tenantSlug = this.slugifyForEmail(this.adminSession?.tenantSlug || '');
    const tenantDomain = tenantSlug.replaceAll('.', '');
    const domain = tenantDomain || 'empresa.com';

    return `${local}@${domain.includes('.') ? domain : `${domain}.com`}`;
  }

  private slugifyForEmail(value: string): string {
    return value
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/ñ/gi, 'n')
      .toLowerCase()
      .replace(/[^a-z0-9\s.-]/g, '')
      .replace(/\s+/g, '.')
      .replace(/\.+/g, '.')
      .replace(/^\.+|\.+$/g, '');
  }

  saveUsuarioEmpresa(): void {
    if (!this.isSuperadminTenant) {
      return;
    }
    if (!this.usuarioEmpresaForm.full_name.trim()) {
      this.usuariosEmpresaFeedback = 'El nombre completo es obligatorio.';
      return;
    }
    if (!this.editingUsuarioEmpresaId && !this.usuarioEmpresaForm.email.trim()) {
      this.usuariosEmpresaFeedback = 'El correo es obligatorio.';
      return;
    }
    if (this.editingUsuarioEmpresaId && !this.usuarioEmpresaForm.email.trim()) {
      this.usuariosEmpresaFeedback = 'El correo es obligatorio.';
      return;
    }
    if (!this.editingUsuarioEmpresaId && this.usuarioEmpresaForm.password.trim().length < 6) {
      this.usuariosEmpresaFeedback = 'La contraseña debe tener al menos 6 caracteres.';
      return;
    }
    if (this.usuarioEmpresaForm.role === 'ADMIN_SUCURSAL' && !this.usuarioEmpresaForm.sucursal_id) {
      this.usuariosEmpresaFeedback = 'Selecciona la sucursal que administrará este usuario.';
      return;
    }
    const headers = this.tenantAuthHeaders;
    const body: Record<string, unknown> = {
      full_name: this.usuarioEmpresaForm.full_name.trim(),
      phone: this.usuarioEmpresaForm.phone.trim(),
      role: this.usuarioEmpresaForm.role,
      sucursal_id: this.usuarioEmpresaForm.sucursal_id ?? null,
    };
    if (!this.editingUsuarioEmpresaId) {
      body['email'] = this.usuarioEmpresaForm.email.trim().toLowerCase();
      body['password'] = this.usuarioEmpresaForm.password;
    }

    const req$ = this.editingUsuarioEmpresaId
      ? this.http.put<UsuarioEmpresaRecord>(`${API_BASE_URL}/tenant/usuarios/${this.editingUsuarioEmpresaId}`, body, { headers })
      : this.http.post<UsuarioEmpresaRecord>(`${API_BASE_URL}/tenant/usuarios`, body, { headers });

    req$.subscribe({
      next: () => {
        this.usuariosEmpresaFeedback = this.editingUsuarioEmpresaId ? 'Usuario actualizado.' : 'Usuario creado.';
        this.cancelUsuarioEmpresaForm();
        this.loadUsuariosEmpresa();
      },
      error: (err: { error?: { detail?: unknown } }) => {
        const detail = err?.error?.detail;
        this.usuariosEmpresaFeedback = typeof detail === 'string' ? detail : 'Error al guardar el usuario.';
      },
    });
  }

  deleteUsuarioEmpresa(id: number): void {
    if (!this.isSuperadminTenant) return;
    if (!window.confirm('¿Eliminar este usuario? Esta acción no se puede deshacer.')) return;
    this.http
      .delete<void>(`${API_BASE_URL}/tenant/usuarios/${id}`, { headers: this.tenantAuthHeaders })
      .subscribe({
        next: () => this.loadUsuariosEmpresa(),
        error: (err: { error?: { detail?: unknown } }) => {
          const detail = err?.error?.detail;
          this.usuariosEmpresaFeedback = typeof detail === 'string' ? detail : 'Error al eliminar el usuario.';
        },
      });
  }

  private resolveWorkshopContext(onResolved?: () => void, force = false): void {
    if (!this.isWorkshopSession || (!this.adminSession?.email && !this.adminSession?.fullName)) {
      return;
    }

    if (this.isResolvingWorkshopContext) {
      return;
    }

    if (!force && this.resolvedWorkshopId != null) {
      onResolved?.();
      return;
    }

    this.isResolvingWorkshopContext = true;
    this.http.get<WorkshopRegistration[]>(this.workshopsApiUrl, this.buildAuthRequestOptions()).subscribe({
      next: (workshops) => {
        const normalizedEmail = this.adminSession?.email.trim().toLowerCase();
        const normalizedName = this.adminSession?.fullName.trim().toLowerCase();
        const matched = workshops.find(
          (workshop) =>
            workshop.email.trim().toLowerCase() === normalizedEmail ||
            workshop.workshop_name.trim().toLowerCase() === normalizedName,
        );
        this.resolvedWorkshopId = matched?.id ?? this.adminSession?.id ?? null;
        this.isResolvingWorkshopContext = false;
        onResolved?.();
      },
      error: () => {
        this.isResolvingWorkshopContext = false;
      },
    });
  }
}
