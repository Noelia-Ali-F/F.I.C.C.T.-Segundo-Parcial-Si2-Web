export const APP_SESSION_STORAGE_KEY = 'acb_session';

export type AppSession = {
  id: number;
  email: string;
  fullName: string;
  phone: string;
  role: 'admin' | 'workshop';
  status: string;
  accessToken: string | null;
  tokenType: string | null;
};

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
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
      !isNonEmptyString(parsed.fullName) ||
      !isNonEmptyString(parsed.phone) ||
      (parsed.role !== 'admin' && parsed.role !== 'workshop') ||
      !isNonEmptyString(parsed.status)
    ) {
      return null;
    }

    return {
      id: parsed.id,
      email: parsed.email,
      fullName: parsed.fullName,
      phone: parsed.phone,
      role: parsed.role,
      status: parsed.status,
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
