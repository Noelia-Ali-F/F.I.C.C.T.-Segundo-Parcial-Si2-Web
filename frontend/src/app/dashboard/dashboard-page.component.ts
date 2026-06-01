import { CommonModule, DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, ElementRef, OnDestroy, ViewChild, inject } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { APP_SESSION_STORAGE_KEY, AppSession, clearStoredSession, parseStoredSession } from '../auth/session';
import { API_BASE_URL, BACKEND_BASE_URL } from '../shared/api-base';

declare const L: any;

type DashboardSection =
  | 'dashboard'
  | 'workshops'
  | 'technicians'
  | 'clients'
  | 'maintenance'
  | 'emergencies'
  | 'reports'
  | 'audit'
  | 'sync';
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

const WORKSHOP_ZONE_OPTIONS = [
  'zona norte',
  'zona sur',
  'zona este',
  'zona oeste',
  'zona centro',
];

const WORKSHOP_SPECIALTY_OPTIONS = [
  'Batería',
  'Neumático',
  'Combustible',
  'Motor',
  'Sistema eléctrico',
  'Accidente',
  'Cerrajería / llaves',
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
  { status: 'servicio_en_proceso', label: 'Servicio en proceso', icon: '⚙' },
  { status: 'servicio_finalizado', label: 'Servicio finalizado', icon: '★' },
  { status: 'solicitud_cancelada', label: 'Cancelada', icon: '✕' },
];

const LEGACY_TO_TIMELINE_STATUS_MAP: Record<LegacyEmergencyStatus, EmergencyTimelineStatus> = {
  pendiente: 'solicitud_recibida',
  activo: 'auxilio_asignado',
  rechazado: 'solicitud_cancelada',
};

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
  scope: 'global' | 'workshop';
  workshop_id: number | null;
  workshop_name: string | null;
  generated_at: string;
  kpis: DashboardStat[];
  summary: DashboardOperationalSummaryItem[];
  status_breakdown: DashboardStatusBreakdownItem[];
  tenant_ranking: DashboardTenantRankingItem[];
  zone_breakdown: DashboardZoneBreakdownItem[];
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
  description: string | null;
  audio_transcript: string | null;
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
  full_name: string;
  phone: string;
  email: string;
  specialty: string;
  status: TechnicianStatus;
  created_at: string;
  updated_at: string;
};

type TechnicianFormModel = {
  full_name: string;
  phone: string;
  email: string;
  specialty: string;
  status: TechnicianStatus;
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
              <span>Taller</span>
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
                <span>Solicitudes</span>
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
        </nav>

        <section class="dashboard-sidebar-card">
          <span>Turno activo</span>
          <strong>Administración general</strong>
          <p>Supervisión de afiliaciones, validación de talleres y control del panel comercial.</p>
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
                <p class="dashboard-panel-kicker">{{ isWorkshopSession ? 'Tenant operativo' : 'Control multitenant' }}</p>
                <h2>{{ isWorkshopSession ? 'Operación del Taller' : 'Vista Global del Sistema' }}</h2>
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
                <p class="dashboard-panel-kicker">Estados del proceso</p>
                <h2>{{ isWorkshopSession ? 'Pipeline del Taller' : 'Distribución Global' }}</h2>
              </div>
            </div>

            <div class="operational-breakdown-list" *ngIf="operationalOverview?.status_breakdown?.length; else noStatusBreakdown">
              <article class="operational-breakdown-item" *ngFor="let item of operationalOverview?.status_breakdown">
                <div>
                  <strong>{{ item.label }}</strong>
                  <p>{{ item.count }} solicitudes registradas en este estado.</p>
                </div>
                <span class="maintenance-request-status" [attr.data-status]="statusFilterGroup(item.status)">
                  {{ item.count }}
                </span>
              </article>
            </div>
            <ng-template #noStatusBreakdown>
              <p class="dashboard-empty">Todavía no hay estados operativos para mostrar.</p>
            </ng-template>
          </article>

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'dashboard' && !isWorkshopSession">
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

          <article class="dashboard-panel" *ngIf="selectedSection === 'dashboard' && !isWorkshopSession">
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

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'dashboard'">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Seguimiento operativo</p>
                <h2>{{ isWorkshopSession ? 'Solicitudes Recientes del Taller' : 'Últimas Emergencias del Sistema' }}</h2>
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
            <p class="dashboard-empty" *ngIf="!isEmergenciesLoading && !maintenanceRequests.length">
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
                <span>Socio / taller</span>
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

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'workshops'">
            <div class="dashboard-panel-head">
              <div>
                <p class="dashboard-panel-kicker">Registros recibidos</p>
                <h2>Registra tu taller mecánico</h2>
              </div>
              <div class="dashboard-toolbar">
                <span class="dashboard-toolbar-note">{{ workshops.length }} registros cargados</span>
                <button class="dashboard-refresh-button" type="button" (click)="loadWorkshops()">
                  Actualizar
                </button>
              </div>
            </div>

            <p class="dashboard-loading" *ngIf="isLoading">Cargando talleres registrados...</p>
            <p class="dashboard-empty" *ngIf="!isLoading && !workshops.length">
              Aún no hay talleres registrados.
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

          <article class="dashboard-panel dashboard-panel-wide" *ngIf="selectedSection === 'technicians'">
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

                  <label class="technician-field technician-field-wide">
                    <span>Estado del tecnico</span>
                    <select name="status" [(ngModel)]="technicianForm.status" required>
                      <option value="disponible">Disponible</option>
                      <option value="ocupado">Ocupado</option>
                      <option value="fuera_de_servicio">Fuera de servicio</option>
                    </select>
                  </label>

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
        </section>
      </section>

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
  readonly isSecureContext = typeof window !== 'undefined' ? window.isSecureContext : false;
  private readonly http = inject(HttpClient);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly router = inject(Router);
  private readonly workshopsApiUrl = `${API_BASE_URL}/workshops`;
  private readonly techniciansApiUrl = `${API_BASE_URL}/technicians`;
  private readonly clientsApiUrl = `${API_BASE_URL}/clientes`;
  private readonly emergenciesApiUrl = `${API_BASE_URL}/emergencias`;
  private readonly dashboardOverviewApiUrl = `${API_BASE_URL}/dashboard/operational-overview`;
  private readonly backendBaseUrl = BACKEND_BASE_URL;
  private readonly appSessionStorageKey = APP_SESSION_STORAGE_KEY;
  private readonly dashboardSidebarStorageKey = 'dashboard.sidebar.collapsed';
  private readonly emergencyRefreshMs = 15000;
  private emergencyRefreshTimer: number | undefined;

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
  operationalOverview: DashboardOperationalOverview | null = null;
  isLoading = true;
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
  clientPendingDelete: Client | null = null;
  showEmergencyModal = false;
  private emergencyMap?: any;
  private emergencyMapMarkersLayer?: any;
  private emergencyMapResizeTimer?: number;
  private workshopEditMap?: any;
  private workshopEditMapMarker?: any;
  private workshopEditMapResizeTimer?: number;
  private workshopEditMapHost?: HTMLDivElement;
  isWorkshopLocationLocating = false;
  workshopLocationMessage = '';
  selectedSyncRecordId: number | null = null;
  syncTab: SyncTab = 'errors';
  selectedSyncErrorRecordId: number | null = null;

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

  technicianForm: TechnicianFormModel = this.createEmptyTechnicianForm();
  workshopForm: WorkshopFormModel = this.createEmptyWorkshopForm();
  clientForm: ClientFormModel = this.createEmptyClientForm();

  stats: DashboardStat[] = [
    {
      label: 'Solicitudes hoy',
      value: '18',
      detail: 'Auxilios y consultas registradas durante la jornada.',
      trend: '+12%',
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

    if (this.isWorkshopSession) {
      this.selectedSection = 'dashboard';
      this.maintenanceFilter = 'pendiente';
    }

    this.loadOperationalOverview();
    this.loadWorkshops();
    this.loadTechnicians();
    this.loadClients();
    this.loadEmergencies();
    this.startEmergencyRefresh();
  }

  ngOnDestroy(): void {
    if (typeof window !== 'undefined' && this.emergencyRefreshTimer !== undefined) {
      window.clearInterval(this.emergencyRefreshTimer);
    }

    if (typeof window !== 'undefined' && this.emergencyMapResizeTimer !== undefined) {
      window.clearTimeout(this.emergencyMapResizeTimer);
    }

    if (typeof window !== 'undefined' && this.workshopEditMapResizeTimer !== undefined) {
      window.clearTimeout(this.workshopEditMapResizeTimer);
    }

    if (this.emergencyMap) {
      this.emergencyMap.remove();
      this.emergencyMap = undefined;
      this.emergencyMapMarkersLayer = undefined;
    }

    this.destroyWorkshopEditMap();
  }

  get sectionTitle(): string {
    if (this.selectedSection === 'technicians') {
      return 'Gestion de Tecnicos';
    }

    if (this.selectedSection === 'clients') {
      return 'Gestion de Clientes';
    }

    if (this.selectedSection === 'workshops') {
      return 'Gestion de Solicitudes';
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

    return 'Resumen general';
  }

  get userDisplayName(): string {
    return this.adminSession?.fullName?.trim() || 'Administrador';
  }

  get isWorkshopSession(): boolean {
    return this.adminSession?.role === 'workshop';
  }

  get currentWorkshopId(): number | null {
    return this.isWorkshopSession ? this.adminSession?.id ?? null : null;
  }

  canAccessSection(section: DashboardSection): boolean {
    if (!this.isWorkshopSession) {
      return true;
    }

    return section === 'dashboard' || section === 'technicians' || section === 'emergencies' || section === 'reports' || section === 'sync';
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
        {
          params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
        },
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
        { params: { workshop_id: this.currentWorkshopId } },
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
      .delete(`${this.emergenciesApiUrl}/${selected.id}`, {
        params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
      })
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
    this.isEmergenciesLoading = true;

    const params: Record<string, string> = {};

    if (this.currentWorkshopId) {
      params['nearest_workshop_id'] = String(this.currentWorkshopId);
    }

    this.http.get<EmergencyReport[]>(this.emergenciesApiUrl, { params }).subscribe({
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
      error: () => {
        this.maintenanceRequests = [];
        this.selectedMaintenanceRequestId = null;
        this.isEmergenciesLoading = false;
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
      .get<EmergencyTimelineResponse>(`${this.emergenciesApiUrl}/${selected.id}/timeline`, {
        params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
      })
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
      .get<EmergencyTrackingResponse>(`${this.emergenciesApiUrl}/${selected.id}/tracking`, {
        params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
      })
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
          params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
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
          params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
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
    if (typeof window === 'undefined') {
      return;
    }

    this.emergencyRefreshTimer = window.setInterval(() => {
      this.loadOperationalOverview();
      this.loadEmergencies({
        refreshSelectedTimeline: this.showEmergencyModal,
        silentTimelineRefresh: this.showEmergencyModal,
      });
    }, this.emergencyRefreshMs);
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
      typeof longitude === 'number' &&
      Number.isFinite(latitude) &&
      Number.isFinite(longitude)
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

  get filteredTechnicians(): Technician[] {
    if (this.technicianFilter === 'todos') {
      return this.technicians;
    }

    if (this.technicianFilter === 'historial') {
      return this.technicians.filter((technician) => technician.status === 'fuera_de_servicio');
    }

    return this.technicians.filter((technician) => technician.status !== 'fuera_de_servicio');
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

  selectSection(section: DashboardSection): void {
    if (!this.canAccessSection(section)) {
      this.selectedSection = this.isWorkshopSession ? 'dashboard' : 'emergencies';
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
      window.localStorage.removeItem(this.appSessionStorageKey);
      window.sessionStorage.removeItem(this.appSessionStorageKey);
    }

    void this.router.navigate(['/login']);
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
      ? 'workshop'
      : normalizedRole === 'admin'
        ? 'admin'
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

    if (this.editingTechnicianId) {
      this.http
        .put<Technician>(`${this.techniciansApiUrl}/${this.editingTechnicianId}`, payload, {
          params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
        })
        .subscribe({
          next: () => {
            this.isSavingTechnician = false;
            this.technicianFeedback = 'Tecnico actualizado correctamente.';
            this.resetTechnicianForm();
            this.showTechnicianForm = false;
            this.loadTechnicians();
          },
          error: () => {
            this.isSavingTechnician = false;
            this.technicianFeedback = 'No se pudo actualizar el tecnico.';
          },
        });
      return;
    }

    this.http
      .post<Technician>(this.techniciansApiUrl, payload, {
        params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
      })
      .subscribe({
        next: () => {
          this.isSavingTechnician = false;
          this.technicianFeedback = 'Tecnico registrado correctamente.';
          this.resetTechnicianForm();
          this.showTechnicianForm = false;
          this.loadTechnicians();
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
      .delete(`${this.techniciansApiUrl}/${technician.id}`, {
        params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
      })
      .subscribe({
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

    this.http
      .put<Technician>(`${this.techniciansApiUrl}/${technician.id}`, {
        workshop_id: technician.workshop_id ?? this.currentWorkshopId,
        full_name: technician.full_name,
        phone: technician.phone,
        email: technician.email,
        specialty: technician.specialty,
        status: nextStatus,
      }, {
        params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
      })
      .subscribe({
        next: () => {
          this.loadTechnicians();
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
      })
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

    this.http.delete(`${this.workshopsApiUrl}/${workshop.id}`).subscribe({
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

    this.http.put<WorkshopRegistration>(`${this.workshopsApiUrl}/${this.editingWorkshopId}`, payload).subscribe({
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

  loadWorkshops(): void {
    if (this.isWorkshopSession) {
      this.workshops = [];
      this.workshopsPage = 1;
      this.isLoading = false;
      this.refreshStats();
      return;
    }

    this.isLoading = true;

    this.http.get<WorkshopRegistration[]>(this.workshopsApiUrl).subscribe({
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
    this.isTechniciansLoading = true;

    this.http
      .get<Technician[]>(this.techniciansApiUrl, {
        params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
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

    this.http.get<Client[]>(this.clientsApiUrl).subscribe({
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
        params: this.currentWorkshopId ? { workshop_id: this.currentWorkshopId } : {},
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
      })
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

    this.http.put<Client>(`${this.clientsApiUrl}/${this.editingClientId}`, payload).subscribe({
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

    this.http.delete(`${this.clientsApiUrl}/${this.clientPendingDelete.id}`).subscribe({
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
          value: String(this.techniciansByStatus('disponible')),
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
}
