/**
 * HimDrishti Accessibility Utilities
 * SIH 2026 · PS 26059
 *
 * Font-size control, reduced-motion, focus management.
 * Implements design.md §26 / GIGW 3.0 / WCAG 2.1 AA requirements.
 */

// ── Font size levels ──────────────────────────────────────────────
export type FontSizeLevel = 'small' | 'normal' | 'large';

const FONT_SIZE_MAP: Record<FontSizeLevel, string> = {
  small: '14px',   // A- level
  normal: '16px',  // A  level (default)
  large: '18px',   // A+ level
};

/**
 * Apply a root font-size level to the document.
 * All rem-based values scale proportionally.
 */
export function applyFontSize(level: FontSizeLevel): void {
  document.documentElement.style.fontSize = FONT_SIZE_MAP[level];
}

/**
 * Move keyboard focus to the main content region.
 * Used by "Skip to main content" link.
 */
export function skipToMainContent(): void {
  const main = document.getElementById('main-content');
  if (main) {
    main.setAttribute('tabindex', '-1');
    main.focus();
    main.addEventListener(
      'blur',
      () => main.removeAttribute('tabindex'),
      { once: true }
    );
  }
}

/**
 * Check if the user prefers reduced motion.
 */
export function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}
