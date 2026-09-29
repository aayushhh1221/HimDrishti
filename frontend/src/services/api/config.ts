/**
 * frontend/src/services/api/config.ts
 * -------------------------------------
 * Central API configuration — reads base URL from Vite env variable.
 *
 * Development default: http://localhost:8000
 * Override:  VITE_API_BASE_URL in frontend/.env.local
 *
 * NEVER put credentials or secrets in VITE_* variables — they are
 * bundled into the frontend and visible to anyone.
 */

export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

/** Convenience for /api/v1/* prefix */
export const API_V1 = `${API_BASE_URL}/api/v1`
