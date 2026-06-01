const apiHost = window.location.hostname;
const apiProtocol = window.location.protocol;

export const BACKEND_BASE_URL = `${apiProtocol}//${apiHost}:8787`;
export const API_BASE_URL = `${BACKEND_BASE_URL}/api`;
