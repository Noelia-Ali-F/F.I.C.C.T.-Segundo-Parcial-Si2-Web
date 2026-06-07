export const APP_SESSION_STORAGE_KEY = 'acb_session';

// Roles legacy (backward compat)
export type LegacyRole = 'admin' | 'workshop';
export type GlobalAdminRole = 'SUPERADMIN_GLOBAL';

// Nuevos roles Database-Per-Tenant
export type TenantRole = 'SUPERADMIN_TENANT' | 'ADMIN_SUCURSAL' | 'TECNICO' | 'CLIENTE';

export type AppRole = LegacyRole | GlobalAdminRole | TenantRole | string;

export const TENANT_ROLES: TenantRole[] = [
  'SUPERADMIN_TENANT',
  'ADMIN_SUCURSAL',
  'TECNICO',
  'CLIENTE',
];

export type AppSession = {
  id: number;
  email: string;
  fullName: string;
  phone: string;
  role: AppRole;
  status: string;
  tenantId: number | null;
  tenantSlug: string | null;
  sucursalId: number | null;
  accessToken: string | null;
  tokenType: string | null;
};

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

export function normalizeRole(role: unknown): AppRole {
  const value = typeof role === 'string' ? role.trim() : '';
  if (!value) {
    return '';
  }

  if (value === 'admin') {
    return 'SUPERADMIN_GLOBAL';
  }

  const knownRoles: AppRole[] = ['workshop', 'SUPERADMIN_GLOBAL', ...TENANT_ROLES];
  return knownRoles.includes(value as AppRole) ? (value as AppRole) : value;
}

export function parseStoredSession(raw: string | null): AppSession | null {
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<AppSession>;

    if (
      typeof parsed.id !== 'number' ||
      !isNonEmptyString(parsed.email) ||
      !isNonEmptyString(parsed.status)
    ) {
      return null;
    }

    const resolvedRole = normalizeRole(parsed.role);

    return {
      id: parsed.id,
      email: parsed.email,
      fullName: parsed.fullName ?? '',
      phone: parsed.phone ?? '',
      role: resolvedRole,
      status: parsed.status,
      tenantId: typeof parsed.tenantId === 'number' ? parsed.tenantId : null,
      tenantSlug: typeof parsed.tenantSlug === 'string' && parsed.tenantSlug ? parsed.tenantSlug : null,
      sucursalId: typeof parsed.sucursalId === 'number' ? parsed.sucursalId : null,
      accessToken: parsed.accessToken ?? null,
      tokenType: parsed.tokenType ?? null,
    };
  } catch {
    return null;
  }
}

export function clearStoredSession(): void {
  window.localStorage.removeItem(APP_SESSION_STORAGE_KEY);
  window.sessionStorage.removeItem(APP_SESSION_STORAGE_KEY);
}

/** Helpers para verificar roles */
export function isTenantRole(role: AppRole): boolean {
  return TENANT_ROLES.includes(normalizeRole(role) as TenantRole);
}

export function isGlobalAdmin(role: AppRole): boolean {
  return normalizeRole(role) === 'SUPERADMIN_GLOBAL';
}

export function isTenantSuperadmin(role: AppRole): boolean {
  return normalizeRole(role) === 'SUPERADMIN_TENANT';
}

export function isSucursalAdmin(role: AppRole): boolean {
  return normalizeRole(role) === 'ADMIN_SUCURSAL';
}

export function isTechnicianRole(role: AppRole): boolean {
  return normalizeRole(role) === 'TECNICO';
}

export function isLegacyWorkshopRole(role: AppRole): boolean {
  return normalizeRole(role) === 'workshop';
}
