/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the backend API (e.g. http://localhost:8000). Empty = same origin. */
  readonly VITE_API_BASE_URL?: string
  /** Explicit WebSocket URL. When unset it is derived from the current origin. */
  readonly VITE_WS_URL?: string
  /** Dev-only proxy target for the Vite dev server. */
  readonly VITE_API_PROXY_TARGET?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
