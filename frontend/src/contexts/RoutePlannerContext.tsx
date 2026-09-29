/**
 * frontend/src/contexts/RoutePlannerContext.tsx
 * -----------------------------------------------
 * @deprecated — superseded by VoyageSessionContext (Phase 10).
 *
 * This file is kept as a compatibility shim.
 * All imports should be migrated to:
 *   import { useVoyageSession, VoyageSessionProvider } from './VoyageSessionContext'
 *
 * The re-exports below ensure any remaining direct imports continue to work
 * without runtime errors during the migration window.
 *
 * SIH 2026 · PS 26059
 */

export {
  VoyageSessionProvider as RoutePlannerProvider,
  useVoyageSession as useRoutePlanner,
} from './VoyageSessionContext'
