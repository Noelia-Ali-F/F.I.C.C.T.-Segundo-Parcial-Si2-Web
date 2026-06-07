import {
  APP_SESSION_STORAGE_KEY,
  AppSession,
  isLegacyWorkshopRole,
  isTenantRole,
  isTechnicianRole,
  isTenantSuperadmin,
  normalizeRole,
  parseStoredSession,
} from './session';

export type SessionRequestContext = {
  session: AppSession | null;
  role: string | null;
  workshopId: number | null;
  tenantId: number | null;
  sucursalId: number | null;
  isWorkshopSession: boolean;
  isTenantSession: boolean;
  isSuperadminTenant: boolean;
  isTecnicoSession: boolean;
  headers: Record<string, string>;
};

export function readStoredAppSession(): AppSession | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const raw =
    window.localStorage.getItem(APP_SESSION_STORAGE_KEY) ||
    window.sessionStorage.getItem(APP_SESSION_STORAGE_KEY);

  return parseStoredSession(raw);
}

export function getSessionRequestContext(): SessionRequestContext {
  const session = readStoredAppSession();
  const role = session?.role ? normalizeRole(session.role) : null;
  const isWorkshopSession = role ? isLegacyWorkshopRole(role) : false;
  const isTenantSession = role ? isTenantRole(role) : false;
  const token = session?.accessToken;

  return {
    session,
    role,
    workshopId: isWorkshopSession ? session?.id ?? null : null,
    tenantId: session?.tenantId ?? null,
    sucursalId: session?.sucursalId ?? null,
    isWorkshopSession,
    isTenantSession,
    isSuperadminTenant: role ? isTenantSuperadmin(role) : false,
    isTecnicoSession: role ? isTechnicianRole(role) : false,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  };
}
