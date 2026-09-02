import type { Confidence, ConfidenceLevel, ReferenceQuarter } from '@/types/results'

export const CONFIDENCE_GLYPH: Record<ConfidenceLevel, string> = {
  high: '●',
  medium: '◐',
  low: '○',
}

export const CONFIDENCE_LABEL: Record<ConfidenceLevel, string> = {
  high: 'high confidence',
  medium: 'medium confidence',
  low: 'low confidence',
}

/** Confidence is reported at reference quarters; pick the first at or after the scrubber quarter. */
export function referenceQuarter(
  quarters: string[],
  q: number,
  available: ReferenceQuarter[] = ['2030Q4', '2040Q4'],
): ReferenceQuarter {
  const current = quarters[q] ?? ''
  const sorted = [...available].sort()
  return sorted.find((r) => r >= current) ?? sorted[sorted.length - 1] ?? '2040Q4'
}

/** One-line tooltip text for a confidence glyph. */
export function confidenceTitle(c: Confidence | undefined, at: string): string {
  if (!c) return 'No confidence classification for this metric.'
  const parts = [
    `${CONFIDENCE_LABEL[c.level]} at ${at.replace(/Q/, ' Q')}`,
    `sign holds in ${Math.round(c.sign_share * 100)}% of draws`,
    c.cells_agree ? 'all 8 mechanism cells agree on the sign' : 'mechanism cells disagree on the sign',
    c.flip_params.length
      ? `flipped within range by ${c.flip_params.join(', ')}`
      : 'no single parameter flips the sign',
  ]
  return parts.join(' · ')
}
