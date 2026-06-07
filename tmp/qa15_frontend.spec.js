const { test, expect } = require('@playwright/test');

const FRONTEND_URL = 'http://127.0.0.1:5656';

async function loginAsTenant(page, email, password) {
  await page.goto(`${FRONTEND_URL}/login`);
  await page.getByRole('button', { name: 'Mi Empresa' }).click();
  await page.locator('input[name="email"]').fill(email);
  await page.locator('input[name="password"]').fill(password);
  await page.getByRole('button', { name: /Ingresar/i }).click();
  await page.waitForURL('**/dashboard');
}

test('route protection, login, realtime and logout', async ({ page }) => {
  const consoleMessages = [];
  page.on('console', (msg) => consoleMessages.push(msg.text()));

  await page.goto(`${FRONTEND_URL}/dashboard`);
  await expect(page).toHaveURL(/\/login$/);

  await loginAsTenant(page, 'superadmin@auxilionorte.com', 'AuxilioNorte#2026');

  await expect(page.getByRole('button', { name: /Cerrar sesion/i })).toBeVisible();
  await expect(page.getByText('Panel operativo', { exact: false })).toBeVisible({ timeout: 15000 });
  await expect(page.getByRole('button', { name: 'Actualizar' }).first()).toBeVisible();

  await page.waitForTimeout(3000);
  const hasConnectedLog = consoleMessages.some((text) => text.includes('[realtime] connectionState connected'));
  const hasWsConnectedEvent = consoleMessages.some((text) => text.includes('[realtime]') && text.includes('ws_connected'));
  expect(hasConnectedLog || hasWsConnectedEvent).toBeTruthy();

  await page.getByRole('button', { name: /Cerrar sesion/i }).click();
  await expect(page).toHaveURL(/\/login$/);

  await page.goto(`${FRONTEND_URL}/dashboard`);
  await expect(page).toHaveURL(/\/login$/);
});

test('dashboard keeps working with websocket failure via fallback polling', async ({ browser }) => {
  const page = await browser.newPage();
  const consoleMessages = [];
  page.on('console', (msg) => consoleMessages.push(msg.text()));

  await page.addInitScript(() => {
    class FailingWebSocket {
      static CONNECTING = 0;
      static OPEN = 1;
      static CLOSING = 2;
      static CLOSED = 3;
      constructor(url) {
        this.url = url;
        this.readyState = FailingWebSocket.CONNECTING;
        setTimeout(() => {
          if (typeof this.onerror === 'function') this.onerror(new Event('error'));
          this.readyState = FailingWebSocket.CLOSED;
          if (typeof this.onclose === 'function') this.onclose(new CloseEvent('close'));
        }, 50);
      }
      send() {}
      close() {
        this.readyState = FailingWebSocket.CLOSED;
        if (typeof this.onclose === 'function') this.onclose(new CloseEvent('close'));
      }
    }
    window.WebSocket = FailingWebSocket;
  });

  await loginAsTenant(page, 'superadmin@auxilionorte.com', 'AuxilioNorte#2026');
  await expect(page.getByText('Panel operativo', { exact: false })).toBeVisible({ timeout: 15000 });
  await expect(page.getByRole('button', { name: 'Actualizar' }).first()).toBeVisible();

  await page.getByRole('button', { name: 'Actualizar' }).first().click();
  await page.waitForTimeout(2500);

  const sawDisconnected = consoleMessages.some((text) => text.includes('[realtime] connectionState disconnected'));
  const sawReconnecting = consoleMessages.some((text) => text.includes('[realtime] connectionState reconnecting'));
  expect(sawDisconnected || sawReconnecting).toBeTruthy();
});
