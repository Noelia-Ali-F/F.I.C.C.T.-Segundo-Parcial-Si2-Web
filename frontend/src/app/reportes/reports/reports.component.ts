import { CommonModule, DatePipe } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { APP_SESSION_STORAGE_KEY, parseStoredSession } from '../../auth/session';
import { MaintenanceRequest } from '../../emergencias/emergencies/emergencies.model';
import { EmergenciesService } from '../../emergencias/emergencies/emergencies.service';
import { ReportsService } from './reports.service';

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [CommonModule, DatePipe],
  templateUrl: './reports.component.html',
  styleUrls: ['./reports.component.css', '../../shared/shared-pages.css'],
})
export class ReportsComponent implements OnInit {
  reportWorkRequests: MaintenanceRequest[] = [];
  isLoading = false;

  constructor(
    private readonly reportsService: ReportsService,
    private readonly emergenciesService: EmergenciesService,
  ) {}

  ngOnInit(): void {
    this.loadReports();
  }

  get currentWorkshopId(): number | null {
    if (typeof window === 'undefined') {
      return null;
    }
    const raw = window.localStorage.getItem(APP_SESSION_STORAGE_KEY) || window.sessionStorage.getItem(APP_SESSION_STORAGE_KEY);
    const session = parseStoredSession(raw);
    return session?.role === 'workshop' ? session.id : null;
  }

  get completedRequests(): MaintenanceRequest[] {
    return this.reportWorkRequests.filter((request) => request.status !== 'pendiente');
  }

  get totalGross(): number {
    return this.completedRequests.reduce((sum, request) => sum + (request.price ?? 0), 0);
  }

  get totalService(): number {
    return this.completedRequests.reduce(
      (sum, request) => sum + (this.emergenciesService.calculateReportServiceAmount(request.price) ?? 0),
      0,
    );
  }

  get totalNet(): number {
    return this.completedRequests.reduce(
      (sum, request) => sum + (this.emergenciesService.calculateReportNetAmount(request.price) ?? 0),
      0,
    );
  }

  loadReports(): void {
    this.isLoading = true;
    this.reportsService.loadReportRequests(this.currentWorkshopId).subscribe({
      next: (requests) => {
        this.reportWorkRequests = requests;
        this.isLoading = false;
      },
      error: () => {
        this.reportWorkRequests = [];
        this.isLoading = false;
      },
    });
  }

  formatPrice(price: number | null): string {
    return this.emergenciesService.formatReportPrice(price);
  }

  serviceAmount(price: number | null): string {
    return this.formatPrice(this.emergenciesService.calculateReportServiceAmount(price));
  }

  netAmount(price: number | null): string {
    return this.formatPrice(this.emergenciesService.calculateReportNetAmount(price));
  }
}
