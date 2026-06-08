import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { SessionRequestContext } from '../auth/session-context';
import { API_BASE_URL } from '../shared/api-base';
import {
  NotificationFilters,
  NotificationSummaryResponse,
  SystemNotificationListResponse,
  SystemNotificationRecord,
} from './notifications.model';

@Injectable({
  providedIn: 'root',
})
export class NotificationsService {
  private readonly http = inject(HttpClient);
  private readonly notificationsApiUrl = `${API_BASE_URL}/notificaciones`;

  listNotifications(
    context: SessionRequestContext,
    filters: NotificationFilters,
    page: number,
    pageSize: number,
  ): Observable<SystemNotificationListResponse> {
    let params = new HttpParams()
      .set('page', String(page))
      .set('page_size', String(pageSize));
    params = this.applyFilters(params, filters);
    return this.http.get<SystemNotificationListResponse>(this.notificationsApiUrl, {
      params,
      headers: context.headers,
    });
  }

  getSummary(
    context: SessionRequestContext,
    filters: NotificationFilters,
  ): Observable<NotificationSummaryResponse> {
    const params = this.applyFilters(new HttpParams(), filters);
    return this.http.get<NotificationSummaryResponse>(`${this.notificationsApiUrl}/resumen`, {
      params,
      headers: context.headers,
    });
  }

  getDetail(
    notificationId: number,
    context: SessionRequestContext,
  ): Observable<SystemNotificationRecord> {
    return this.http.get<SystemNotificationRecord>(`${this.notificationsApiUrl}/${notificationId}`, {
      headers: context.headers,
    });
  }

  markAsRead(
    notificationId: number,
    context: SessionRequestContext,
  ): Observable<SystemNotificationRecord> {
    return this.http.patch<SystemNotificationRecord>(`${this.notificationsApiUrl}/${notificationId}/read`, {}, {
      headers: context.headers,
    });
  }

  retryFailed(
    notificationId: number,
    context: SessionRequestContext,
  ): Observable<SystemNotificationRecord> {
    return this.http.post<SystemNotificationRecord>(`${this.notificationsApiUrl}/${notificationId}/reenviar`, {}, {
      headers: context.headers,
    });
  }

  private applyFilters(params: HttpParams, filters: NotificationFilters): HttpParams {
    return Object.entries(filters).reduce((acc, [key, value]) => {
      if (value === null || value === undefined || value === '') {
        return acc;
      }
      return acc.set(key, String(value));
    }, params);
  }
}
