// Vite configuration for QShield Twin frontend
// Sets up React plugin and dev server on port 5173
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
})
