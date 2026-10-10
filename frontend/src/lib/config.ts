// Centralised runtime configuration for backend connectivity.
//
// The REST API base defaults to the same origin (works in production behind a
// reverse proxy and in dev via the Vite proxy configured in vite.config.ts).
// Override with VITE_API_BASE_URL when the API is served from a different host.
//
// SECURITY: the browser must never hold the backend API token. Vite inlines any
// `VITE_`-prefixed variable into the client bundle, so a `VITE_API_TOKEN` would
// be public to every visitor. Instead the token is held only by a server-side
// component (the Vite dev-server proxy in development, a reverse proxy such as
// nginx in production) which injects the `X-API-Token` header when forwarding to
// the backend. Nothing here reads or forwards a token.

const RAW_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')

export const API_BASE_URL = RAW_BASE
export const API_V1 = `${API_BASE_URL}/api/v1`

/** Build a full URL for an API path such as "/security/status". */
export function apiUrl(path: string): string {
  const suffix = path.startsWith('/') ? path : `/${path}`
  return `${API_V1}${suffix}`
}

/** Build the WebSocket stream URL, honouring VITE_WS_URL when provided. */
export function wsUrl(path = '/api/v1/ws/stream'): string {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL
  }
  const base =
    API_BASE_URL ||
    `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
  return `${base.replace(/^http/, 'ws')}${path}`
}
