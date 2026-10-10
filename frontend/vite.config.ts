// Vite configuration for QShield Twin frontend.
//
// The dev server proxies /api (including the /api/v1/ws/stream WebSocket) to the
// FastAPI backend so relative fetches work without CORS. Override the backend
// location with VITE_API_PROXY_TARGET.
//
// SECURITY: the backend API token is injected here, in the Node process that runs
// the dev server — never in the browser. `QSHIELD_API_TOKEN` is deliberately NOT
// prefixed with `VITE_`, so Vite never inlines it into the client bundle; the
// proxy adds the `X-API-Token` header when forwarding /api requests and the
// WebSocket upgrade. In production a reverse proxy (e.g. nginx) performs the
// same injection in front of the static bundle. See docs/ARCHITECTURE.md.
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

type ProxyRequest = { setHeader: (name: string, value: string) => void }

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target =
    process.env.VITE_API_PROXY_TARGET || env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

  // Server-side only. Read from the environment (Docker/compose) or the local
  // .env file. Never exposed to the browser because it is not VITE_-prefixed.
  const apiToken = process.env.QSHIELD_API_TOKEN || env.QSHIELD_API_TOKEN || ''
  const injectToken = (proxyReq: ProxyRequest): void => {
    if (apiToken) proxyReq.setHeader('X-API-Token', apiToken)
  }

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target,
          changeOrigin: true,
          ws: true,
          configure: (proxy) => {
            proxy.on('proxyReq', injectToken)
            proxy.on('proxyReqWs', injectToken)
          },
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
    },
  }
})
