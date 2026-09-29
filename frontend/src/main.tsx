/**
 * HimDrishti — Application Entry Point
 * SIH 2026 · PS 26059
 */

// Self-hosted Noto Sans — design.md §7 (no external network dependency)
import '@fontsource/noto-sans/400.css'
import '@fontsource/noto-sans/500.css'
import '@fontsource/noto-sans/600.css'
import '@fontsource/noto-sans/700.css'

// MapLibre GL JS CSS — must be imported globally before map initialisation
import 'maplibre-gl/dist/maplibre-gl.css'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
