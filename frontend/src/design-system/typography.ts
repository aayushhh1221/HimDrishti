/**
 * HimDrishti Typography System
 * SIH 2026 · PS 26059
 *
 * Type scale from design.md §7.
 * Primary font: Noto Sans (self-hosted via @fontsource/noto-sans).
 */

// ── Font families ─────────────────────────────────────────────────
export const fontFamily = {
  /**
   * Primary: Noto Sans — design.md §7
   * Fallback chain as specified in design.md.
   * Self-hosted via @fontsource/noto-sans (imported in main.tsx).
   */
  primary:
    '"Noto Sans", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
} as const;

// ── Type scale — design.md §7 ─────────────────────────────────────
export const fontSize = {
  display: '2rem',       // 32px / 40px line-height
  h1: '1.625rem',        // 26px / 34px
  h2: '1.3125rem',       // 21px / 28px
  h3: '1.0625rem',       // 17px / 24px
  body: '0.9375rem',     // 15px / 22px
  small: '0.8125rem',    // 13px / 18px
  micro: '0.6875rem',    // 11px / 16px
} as const;

export const lineHeight = {
  display: '2.5rem',
  h1: '2.125rem',
  h2: '1.75rem',
  h3: '1.5rem',
  body: '1.375rem',
  small: '1.125rem',
  micro: '1rem',
} as const;

export const fontWeight = {
  regular: '400',
  medium: '500',
  semibold: '600',
  bold: '700',
} as const;
