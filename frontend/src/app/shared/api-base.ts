const apiHost = window.location.hostname;
const apiProtocol = window.location.protocol;

export const BACKEND_BASE_URL = `${apiProtocol}//${apiHost}:8787`;
export const API_BASE_URL = `${BACKEND_BASE_URL}/api`;

export function buildRealtimeWebSocketUrl(token: string): string {
  const backendUrl = new URL(BACKEND_BASE_URL);
  backendUrl.protocol = backendUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  backendUrl.pathname = '/api/ws';
  backendUrl.search = '';
  backendUrl.searchParams.set('token', token);
  return backendUrl.toString();
}
