import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { APP_SESSION_STORAGE_KEY, clearStoredSession, parseStoredSession } from './session';

export const authGuard: CanActivateFn = () => {
  const router = inject(Router);
  const rawSession =
    window.localStorage.getItem(APP_SESSION_STORAGE_KEY) ||
    window.sessionStorage.getItem(APP_SESSION_STORAGE_KEY);

  const session = parseStoredSession(rawSession);

  if (session) {
    return true;
  }

  clearStoredSession();
  return router.createUrlTree(['/login']);
};
