// KaizenIQ portal — Vite configuration.
// The /api proxy forwards calls to the FastAPI backend during development,
// so frontend code can use relative URLs in every environment.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
