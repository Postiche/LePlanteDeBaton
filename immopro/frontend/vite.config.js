import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En développement, l'API FastAPI (port 8000) est servie via le proxy Vite :
// le navigateur reste sur une seule origine (cookies SameSite=Strict).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false } },
  },
  build: { outDir: 'dist', sourcemap: false, chunkSizeWarningLimit: 900 },
  test: { environment: 'node' },
})
