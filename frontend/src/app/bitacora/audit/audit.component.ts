import { CommonModule, DatePipe } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { APP_SESSION_STORAGE_KEY, parseStoredSession } from '../../auth/session';
import { AuditItem } from '../../emergencias/emergencies/emergencies.model';
import { AuditService } from './audit.service';

@Component({
  selector: 'app-audit',
  standalone: true,
  imports: [CommonModule, DatePipe],
  templateUrl: './audit.component.html',
  styleUrls: ['./audit.component.css', '../../shared/shared-pages.css'],
})
export class AuditComponent implements OnInit {
  auditItems: AuditItem[] = [];
  isLoading = false;

  constructor(private readonly auditService: AuditService) {}

  ngOnInit(): void {
    this.loadAuditItems();
  }

  get currentWorkshopId(): number | null {
    if (typeof window === 'undefined') {
      return null;
    }
    const raw = window.localStorage.getItem(APP_SESSION_STORAGE_KEY) || window.sessionStorage.getItem(APP_SESSION_STORAGE_KEY);
    const session = parseStoredSession(raw);
    return session?.role === 'workshop' ? session.id : null;
  }

  loadAuditItems(): void {
    this.isLoading = true;
    this.auditService.loadAuditItems(this.currentWorkshopId).subscribe({
      next: (items) => {
        this.auditItems = items;
        this.isLoading = false;
      },
      error: () => {
        this.auditItems = [];
        this.isLoading = false;
      },
    });
  }
}
