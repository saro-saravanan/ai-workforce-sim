/**
 * Chart palette — the dataviz reference instance (validated with scripts/validate_palette.js).
 * Light/dark are separately stepped; the app swaps them by theme.
 */
export type Mode = 'light' | 'dark'

/**
 * Slots 0–7 are the validated eight; slots 8–9 (teal, brown) were added for the Phase 7 channels
 * (output substitution, traded services) and only the stacked-channel chart reaches them.
 */
export const CATEGORICAL: Record<Mode, string[]> = {
  light: ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948', '#0e8f9f', '#8a6a3c'],
  dark: ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767', '#2fa9ba', '#b4915f'],
}

/** All-pairs forms (scatter, choropleth) validate only the first three slots. */
export const ALL_PAIRS_CAP = 3

export const NEUTRAL: Record<Mode, string> = { light: '#a8a69f', dark: '#6f6e68' }

/** Diverging: blue (positive) <-> neutral gray <-> red (negative), equal arms. */
export const DIVERGING: Record<Mode, { neg: string; mid: string; pos: string }> = {
  light: { neg: '#a62c2b', mid: '#f0efec', pos: '#104281' },
  dark: { neg: '#f08c8c', mid: '#383835', pos: '#86b6ef' },
}

/** Sequential one-hue ramps (light end recedes toward the surface). */
export const SEQUENTIAL: Record<Mode, { blue: [string, string]; red: [string, string] }> = {
  light: { blue: ['#cde2fb', '#0d366b'], red: ['#fbd9d8', '#8a2120'] },
  dark: { blue: ['#184f95', '#b7d3f6'], red: ['#6e1f1f', '#f5b3b3'] },
}

export const CHROME: Record<
  Mode,
  { surface: string; ink: string; ink2: string; muted: string; grid: string; axis: string }
> = {
  light: {
    surface: '#fcfcfb',
    ink: '#0b0b0b',
    ink2: '#52514e',
    muted: '#6f6d67',
    grid: '#e1e0d9',
    axis: '#c3c2b7',
  },
  dark: {
    surface: '#1a1a19',
    ink: '#ffffff',
    ink2: '#c3c2b7',
    muted: '#a09e97',
    grid: '#2c2c2a',
    axis: '#383835',
  },
}
