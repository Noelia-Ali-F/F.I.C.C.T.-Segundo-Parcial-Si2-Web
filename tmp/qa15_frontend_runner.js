const { chromium } = require('playwright');

const FRONTEND_URL = 'http://127.0.0.1:5656';

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function loginAsTenant(page, email, password) {
  await page.goto(`${FRONTEND_URL}/login`);
  await page.getByRole('button', { name: 'Mi Empresa' }).click();
  await page.locator('input[name="email"]').fill(email);
  await page.locator('input[name="password"]').fill(password);
  await page.getByRole('button', { name: /Ingresar/i }).click();
  await page.waitForURL('**/dashboard');
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const results = {};

  const page = await browser.newPage();
  const consoleMessages = [];
  page.on('console', (msg) => consoleMessages.push(msg.text()));

  await page.goto(`${FRONTEND_URL}/dashboard`);
  results.routeProtectionRedirect = page.url().endsWith('/login');

  await loginAsTenant(page, 'superadmin@auxilionorte.com', 'AuxilioNorte#2026');
  await page.getByRole('button', { name: /Cerrar sesion/i }).waitFor();
  await page.getByText('Panel operativo', { exact: false }).waitFor();
  await page.getByRole('button', { name: 'Actualizar' }).first().waitFor();
  await page.waitForTimeout(3000);

  results.loginDashboard = page.url().includes('/dashboard');
  results.logoutButtonVisible = await page.getByRole('button', { name: /Cerrar sesion/i }).isVisible();
  results.refreshButtonVisible = await page.getByRole('button', { name: 'Actualizar' }).first().isVisible();
  results.realtimeConnected =
    consoleMessages.some((text) => text.includes('[realtime] connectionState connected')) ||
    consoleMessages.some((text) => text.includes('[realtime]') && text.includes('ws_connected'));

  await page.getByRole('button', { name: /Cerrar sesion/i }).click();
  await page.waitForURL('**/login');
  await page.goto(`${FRONTEND_URL}/dashboard`);
  results.logoutRedirectsToLogin = page.url().endsWith('/login');

  const fallbackPage = await browser.newPage();
  const fallbackConsole = [];
  fallbackPage.on('console', (msg) => fallbackConsole.push(msg.text()));
  await fallbackPage.addInitScript(() => {
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

  await loginAsTenant(fallbackPage, 'superadmin@auxilionorte.com', 'AuxilioNorte#2026');
  await fallbackPage.getByText('Panel operativo', { exact: false }).waitFor();
  await fallbackPage.getByRole('button', { name: 'Actualizar' }).first().click();
  await fallbackPage.waitForTimeout(2500);
  results.fallbackDashboardLoads = fallbackPage.url().includes('/dashboard');
  results.fallbackRefreshVisible = await fallbackPage.getByRole('button', { name: 'Actualizar' }).first().isVisible();
  results.fallbackSawRealtimeDisconnect =
    fallbackConsole.some((text) => text.includes('[realtime] connectionState disconnected')) ||
    fallbackConsole.some((text) => text.includes('[realtime] connectionState reconnecting'));

  await browser.close();

  assert(results.routeProtectionRedirect, 'dashboard should redirect unauthenticated users to login');
  assert(results.loginDashboard, 'login should navigate to dashboard');
  assert(results.logoutButtonVisible, 'logout button should be visible');
  assert(results.refreshButtonVisible, 'refresh button should be visible');
  assert(results.realtimeConnected, 'realtime should connect in normal scenario');
  assert(results.logoutRedirectsToLogin, 'logout should clear session and protect dashboard again');
  assert(results.fallbackDashboardLoads, 'dashboard should still load when websocket fails');
  assert(results.fallbackRefreshVisible, 'refresh button should still be visible in fallback scenario');
  assert(results.fallbackSawRealtimeDisconnect, 'fallback scenario should observe realtime disconnect/reconnect logs');

  console.log(JSON.stringify(results, null, 2));
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
