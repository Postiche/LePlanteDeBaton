import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import 'leaflet/dist/leaflet.css'
import './styles.css'
import App from './App.jsx'
import { AuthProvider } from './auth.jsx'
import { ToastProvider } from './components/ui.jsx'

const Router = import.meta.env.VITE_PREVIEW === '1' ? HashRouter : BrowserRouter

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Router>
      <ToastProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ToastProvider>
    </Router>
  </StrictMode>
)

if ('serviceWorker' in navigator && import.meta.env.PROD && import.meta.env.VITE_PREVIEW !== '1') {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => {}))
}
