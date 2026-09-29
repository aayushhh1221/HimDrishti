/**
 * HimDrishti Design Tokens
 * SIH 2026 · PS 26059
 *
 * Single source of truth for all design values.
 * Values are derived from design.md §5 (Colour), §7 (Typography), §8 (Layout), §33 (Tokens).
 * Do NOT introduce colours, gradients, or neon effects not present here.
 */

// ── Colour palette ────────────────────────────────────────────────
export const colors = {
  // Base palette — design.md §5.1
  ink: '#102A43',
  navy: '#0B1F33',
  background: '#F7F8FA',
  surface: '#FFFFFF',
  border: '#D9E1E8',
  mutedText: '#52606D',
  secondaryText: '#334E68',

  // Operational accent — design.md §5.1
  teal: '#287D7A',
  tealSoft: '#D9F0EE',

  // Risk palette — design.md §5.1
  success: '#18794E',
  successSoft: '#E6F4ED',
  warning: '#B7791F',
  warningSoft: '#FEF3C7',
  danger: '#B42318',
  dangerSoft: '#FEE2E2',

  // Government utility bar — design.md §9.1
  utilityBarBg: '#100A2A',
  utilityBarText: '#FFFFFF',
  utilityBarSeparator: 'rgba(255,255,255,0.25)',

  // Navigation — derived from design.md §9.4
  navBg: '#0B1F33',
  navText: 'rgba(255,255,255,0.80)',
  navTextHover: '#FFFFFF',
  navActiveText: '#FFFFFF',
  navActiveBg: '#287D7A',

  // Status row — derived from reference-ui.png
  statusRowBg: '#F0F4F8',
  statusRowBorder: '#D9E1E8',

  // Prototype badge — design.md §9.3
  prototypeBadgeBg: 'transparent',
  prototypeBadgeBorder: '#287D7A',
  prototypeBadgeText: '#287D7A',
} as const;

// ── Spacing scale — design.md §8 ─────────────────────────────────
export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '12px',
  lg: '16px',
  xl: '24px',
  xxl: '32px',
} as const;

// ── Border radius — design.md §33 (keep modest) ──────────────────
export const radius = {
  sm: '4px',
  md: '6px',
  lg: '8px',
} as const;

// ── Shadow — design.md §6 (very subtle) ──────────────────────────
export const shadow = {
  sm: '0 1px 2px 0 rgba(0,0,0,0.05)',
  md: '0 2px 4px 0 rgba(0,0,0,0.08)',
} as const;

// ── Layout — design.md §8 ─────────────────────────────────────────
export const layout = {
  contentMaxWidth: '1440px',
  pagePadding: '24px',
  panelGap: '16px',
  sectionGap: '24px',
} as const;

// ── Component heights — from reference-ui.png measurements ───────
export const heights = {
  utilityBar: '36px',
  institutionalHeader: '88px',
  navigation: '48px',
  statusRow: '42px',
} as const;

// ── Motion — design.md §25 ────────────────────────────────────────
export const transition = {
  fast: '150ms ease',
  base: '250ms ease',
} as const;
