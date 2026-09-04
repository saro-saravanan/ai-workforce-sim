/**
 * Client-side pieces of the story layer: the executive brief as Markdown (a port of
 * `executive_brief_md` in `api/aiwsim_api/story.py`, without the inline charts) for the modes
 * without a server or an exported brief, and small display helpers for the Story view.
 */
import type { StoryDocument, StoryFuture } from '@/types/story'
import { REGION_NAMES, isRegionId } from '@/types/results'
import { millions, pyFixed } from '@/lib/plain'

/** The label of every beat's range (contracts §29): the band is the model's own runs, not a forecast interval. */
export const RANGE_LABEL = "Range of the model's assumptions"
export const RANGE_TITLE =
  'the middle 80% of the model\'s runs across parameter draws and mechanism cells; not a forecast interval: it excludes model error'

/** "Mechanism cells alone: −9.1% to −2.3% (64 cells)" for the jobs beat, or "" without a spread. */
export function structuralSpreadLine(sp: StoryDocument['structural_spread']): string {
  if (!sp || !Number.isFinite(sp.min) || !Number.isFinite(sp.max)) return ''
  return `Mechanism cells alone: ${pct1(sp.min)} to ${pct1(sp.max)} (${sp.cells} cells${sp.agree_on_sign ? '' : '; they disagree on the sign'})`
}

export function regionName(id: string): string {
  return isRegionId(id) ? REGION_NAMES[id] : id
}

/** Executive brief (Markdown): the story's sentences, policies, scoreboard, caveats and glossary. */
export function execBriefMarkdown(st: StoryDocument): string {
  const n = st.numbers
  const yr = st.horizon[1].slice(0, 4)
  const L: string[] = [
    `# What AI does to work in ${st.region_name ?? regionName(st.region)}, in seven findings`,
    '',
    `Scenario: ${st.scenario_name ?? st.scenario_id ?? ''}. Everything below is a difference from a world in which AI stopped improving in 2023. Run \`${st.scenario_hash}\`.`,
    '',
    '## In five sentences',
    '',
    `By ${yr} there are about ${millions(n.jobs_gap)} fewer jobs than there would have been, out of the ${millions(n.jobs_2040_no_ai ?? n.jobs_base)} there would have been in ${yr}; most of them are jobs never created rather than jobs destroyed. ` +
      `Most of that is hiring that never happens rather than layoffs, so ${st.region === 'US' ? 'the young' : 'new entrants'} pay first. Real pay rises about ${pyFixed(n.real_wage_pct.p50)}% and the economy is about ${pyFixed(n.gdp_pct)}% larger, ` +
      `but workers' share of income falls ${pyFixed(Math.abs(n.wage_share_pp), 1)} points. Office work is reshaped now, robots come in the mid-2030s, AI-made content spreads category by category. ` +
      `Whether jobs end up down ${pyFixed(Math.abs(n.employment_pct.p10))}% or flat depends mostly on whether the gains are spent back into the economy.`,
    '',
  ]
  st.beats.forEach((b, i) => {
    L.push(`## ${i + 1}. ${b.title}`, '', b.sentence, '')
    L.push(`*Range of the model's assumptions:* ${b.range}  `)
    L.push(`*How sure:* ${b.sureness.label}.  `)
    L.push(`*What changes it:* ${b.what_changes_it}`, '')
  })
  L.push('## What could be done', '')
  if (st.policies.length) for (const pr of st.policies) L.push(`- ${pr.sentence}`)
  else
    L.push(
      '- Policy runs are not available for this document; the technical brief lists the levers.',
    )
  L.push('')
  if (st.forecasts?.length) {
    L.push('## How the model compares with named forecasts', '')
    L.push('| Who | Claim | Model (this run) | Verdict |', '|---|---|---|---|')
    for (const f of st.forecasts) {
      const mc = f.model_central
      L.push(
        `| ${f.short} | ${f.claimed} ${f.unit} by ${f.year} (${f.region}) | ${mc != null ? pyFixed(mc, 1) : 'n/a'} | ${f.verdict}${f.proxy ? ' (nearest model quantity)' : ''} |`,
      )
    }
    L.push(
      '',
      'A claim marked *nearest model quantity* is compared with the closest thing the model tracks, named in the technical brief; the verdict is about direction and size, not a one-to-one test.',
      '',
    )
  }
  L.push('## Read this with care', '')
  for (const c of st.caveats) L.push(`- ${c}`)
  L.push('', '## Words used', '')
  for (const [k, v] of Object.entries(st.glossary)) L.push(`- **${k}**: ${v}`)
  L.push('')
  return L.join('\n')
}

/** "about 8.6 million fewer jobs" / "about 22.9 million more jobs" */
export function futureJobs(f: StoryFuture): string {
  return `about ${millions(f.jobs)} ${f.jobs > 0 ? 'fewer' : 'more'} jobs`
}

/** A signed one-decimal percent with a Unicode minus, e.g. "−5.1%" */
export function pct1(v: number | null | undefined, digits = 1): string {
  if (v == null || !Number.isFinite(v)) return '—'
  const s = pyFixed(Math.abs(v), digits)
  return `${v < 0 && Number(s) !== 0 ? '−' : v > 0 && Number(s) !== 0 ? '+' : ''}${s}%`
}

/** A signed count in words: "+13.8 million", "−34,000", "no change" */
export function signedCount(v: number): string {
  if (Math.abs(v) < 500) return 'no change'
  return `${v < 0 ? '−' : '+'}${millions(v)}`
}
