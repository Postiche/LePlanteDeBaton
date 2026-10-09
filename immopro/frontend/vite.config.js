import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'

// VITE_PREVIEW=1 : aperçu autonome (données fictives précalculées, sans serveur)
const PREVIEW = process.env.VITE_PREVIEW === '1'
const fixtures = fileURLToPath(new URL(PREVIEW ? './src/preview/fixtures.json' : './src/preview/stub.js', import.meta.url))

// En développement, l'API FastAPI (port 8000) est servie via le proxy Vite :
// le navigateur reste sur une seule origine (cookies SameSite=Strict).
export default defineConfig({
  plugins: [react()],
  base: PREVIEW ? './' : '/',
  resolve: { alias: { 'preview-fixtures': fixtures } },
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false } },
  },
  build: { outDir: PREVIEW ? 'dist-preview' : 'dist', assetsInlineLimit: PREVIEW ? 100000000 : 4096, sourcemap: false, chunkSizeWarningLimit: 900 },
  test: { environment: 'node' },
})
