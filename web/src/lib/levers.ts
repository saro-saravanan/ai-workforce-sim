/**
 * Levers form model: a flat map of dotted paths → values over a nested scenario document,
 * a diff against the parent scenario, and the id of a child scenario.
 * Pure functions so the What-if drawer is unit-testable without Vue.
 */
import type { DiffEntry, LeverDef, ScenarioDocument } from '@/types/results'

export type LeverValue = number | string | boolean
export type LeverValues = Record<string, LeverValue>

export const LEVER_GROUP_ORDER = [
  'capability',
  'cost',
  'regulation',
  'adoption',
  'labor',
  'policy',
  'applications',
  'baseline',
] as const

export const LEVER_GROUP_LABELS: Record<string, string> = {
  capability: 'Capability',
  cost: 'Cost & compute',
  regulation: 'Regulation',
  adoption: 'Adoption',
  labor: 'Labor market',
  policy: 'Policy (US)',
  applications: 'Applications (embodied)',
  baseline: 'Baseline construction',
}

/** A lever row in the drawer, or a compact grid of sibling enum levers (the ten approval regimes). */
export type LeverLayoutItem =
  | { kind: 'lever'; lever: LeverDef }
  | { kind: 'grid'; key: string; label: string; options: string[]; levers: LeverDef[] }

/** Human label for a compact grid from its parent path, e.g. "levers.applications.approval" → "Approval regime". */
const GRID_LABELS: Record<string, string> = {
  'levers.applications.approval': 'Approval regime by region',
  'levers.policy.US.financing': 'Financing rule by transfer',
}

/**
 * Groups `min` or more sibling enum levers with identical options (same parent path) into one
 * grid item, keeping the position of the first sibling; every other lever is passed through.
 */
export function layoutLevers(levers: LeverDef[], min = 4): LeverLayoutItem[] {
  const parentOf = (p: string) => p.slice(0, p.lastIndexOf('.'))
  const siblings = new Map<string, LeverDef[]>()
  for (const l of levers) {
    if (l.type !== 'enum' || !l.options?.length) continue
    const key = `${parentOf(l.path)}|${l.options.join(',')}`
    siblings.set(key, [...(siblings.get(key) ?? []), l])
  }
  const gridOf = new Map<string, string>()
  for (const [key, ls] of siblings) if (ls.length >= min) for (const l of ls) gridOf.set(l.path, key)
  const out: LeverLayoutItem[] = []
  const emitted = new Set<string>()
  for (const l of levers) {
    const key = gridOf.get(l.path)
    if (!key) {
      out.push({ kind: 'lever', lever: l })
      continue
    }
    if (emitted.has(key)) continue
    emitted.add(key)
    const ls = siblings.get(key)!
    const parent = parentOf(l.path)
    const leaf = parent.slice(parent.lastIndexOf('.') + 1)
    out.push({
      kind: 'grid',
      key,
      label: GRID_LABELS[parent] ?? leaf.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase()),
      options: l.options ?? [],
      levers: ls,
    })
  }
  return out
}

/** The short name of a lever inside a compact grid: the last path segment ("US", "RoA", "wage insurance"). */
export function leverLeaf(l: LeverDef): string {
  return l.path.slice(l.path.lastIndexOf('.') + 1).replace(/_/g, ' ')
}

export function getPath(obj: unknown, path: string): unknown {
  let cur: unknown = obj
  for (const k of path.split('.')) {
    if (cur == null || typeof cur !== 'object') return undefined
    cur = (cur as Record<string, unknown>)[k]
  }
  return cur
}

/** Sets a dotted path, creating intermediate objects; mutates and returns `obj`. */
export function setPath<T extends Record<string, unknown>>(obj: T, path: string, value: unknown): T {
  const keys = path.split('.')
  let cur: Record<string, unknown> = obj
  for (let i = 0; i < keys.length - 1; i++) {
    const k = keys[i]!
    const next = cur[k]
    if (next == null || typeof next !== 'object') cur[k] = {}
    cur = cur[k] as Record<string, unknown>
  }
  cur[keys[keys.length - 1]!] = value
  return obj
}

/** Deep-merges child scalars/objects over parent (schema §8.1 inheritance for `levers`). */
export function deepMerge<T>(parent: T, child: unknown): T {
  if (child == null) return parent
  if (typeof parent !== 'object' || parent == null || Array.isArray(parent)) return child as T
  if (typeof child !== 'object' || Array.isArray(child)) return child as T
  const out: Record<string, unknown> = { ...(parent as Record<string, unknown>) }
  for (const [k, v] of Object.entries(child as Record<string, unknown>)) {
    out[k] = k in out ? deepMerge(out[k], v) : v
  }
  return out as T
}

/**
 * Resolves a scenario against its ancestors (levers deep-merge; shocks keyed by id;
 * remove_shocks drops; overrides merge by id). `byId` must contain every ancestor.
 */
export function resolveScenario(
  doc: ScenarioDocument,
  byId: Map<string, ScenarioDocument>,
  depth = 0,
): ScenarioDocument {
  if (!doc.parent || depth > 16) return { ...doc, levers: doc.levers ?? {} }
  const parentDoc = byId.get(doc.parent)
  if (!parentDoc) return { ...doc, levers: doc.levers ?? {} }
  const parent = resolveScenario(parentDoc, byId, depth + 1)
  const shocks = new Map((parent.shocks ?? []).map((s) => [s.id, s]))
  for (const id of doc.remove_shocks ?? []) shocks.delete(id)
  for (const s of doc.shocks ?? []) shocks.set(s.id, s)
  return {
    ...parent,
    ...doc,
    levers: deepMerge(parent.levers ?? {}, doc.levers ?? {}),
    shocks: [...shocks.values()],
    overrides: { ...parent.overrides, ...doc.overrides },
    ensemble: { ...parent.ensemble, ...doc.ensemble },
  }
}

/** Flat form values for the lever list, read from a resolved scenario (defaults fill gaps). */
export function leverValues(levers: LeverDef[], scenario: ScenarioDocument | null): LeverValues {
  const out: LeverValues = {}
  for (const l of levers) {
    const v = scenario ? getPath(scenario, l.path) : undefined
    out[l.path] = (v as LeverValue | undefined) ?? (l.default as LeverValue) ?? (l.type === 'boolean' ? false : l.type === 'enum' ? (l.options?.[0] ?? '') : (l.min ?? 0))
  }
  return out
}

const EPS = 1e-9
function same(a: LeverValue | undefined, b: LeverValue | undefined) {
  if (typeof a === 'number' && typeof b === 'number') return Math.abs(a - b) < EPS
  return a === b
}

/** The live "diff vs parent" list: one entry per lever whose value differs from the parent's. */
export function leverDiff(
  levers: LeverDef[],
  parentValues: LeverValues,
  values: LeverValues,
): DiffEntry[] {
  const out: DiffEntry[] = []
  for (const l of levers) {
    const from = parentValues[l.path]
    const to = values[l.path]
    if (!same(from, to)) out.push({ path: l.path, from, to, mechanism: l.mechanism ?? '' })
  }
  return out
}

/** Clamp a number lever to [min, max] and snap to step (so slider and input agree). */
export function clampLever(l: LeverDef, v: number): number {
  if (!Number.isFinite(v)) return typeof l.default === 'number' ? l.default : (l.min ?? 0)
  const min = l.min ?? Number.NEGATIVE_INFINITY
  const max = l.max ?? Number.POSITIVE_INFINITY
  let x = Math.min(max, Math.max(min, v))
  if (l.step && Number.isFinite(l.step) && l.step > 0 && Number.isFinite(min)) {
    x = min + Math.round((x - min) / l.step) * l.step
    x = Math.min(max, Number(x.toFixed(6)))
  }
  return x
}

/** Only the changed levers, as a nested `levers` object for a child scenario. */
export function leversPatch(diff: DiffEntry[]): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const d of diff) setPath(out, d.path, d.to)
  return (out.levers as Record<string, unknown>) ?? {}
}

/** FNV-1a 32-bit, hex. Stable across runs, no crypto needed. */
export function shortHash(input: string, len = 6): string {
  let h = 0x811c9dc5
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i)
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h.toString(16).padStart(8, '0').slice(0, len)
}

export function slugify(s: string): string {
  return (
    s
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .replace(/^[^a-z0-9]/, '')
      .slice(0, 48) || 'scenario'
  )
}

/** Child id: `<slug>-<hash of parent + diff>`; matches schema `^[a-z0-9][a-z0-9-]{1,63}$`. */
export function childScenarioId(name: string, parent: string, diff: DiffEntry[]): string {
  const key = JSON.stringify([parent, diff.map((d) => [d.path, d.to])])
  return `${slugify(name)}-${shortHash(key)}`
}

/** Builds the child scenario document for POST /api/run or POST /api/scenarios. */
export function buildChildScenario(
  name: string,
  parent: ScenarioDocument,
  diff: DiffEntry[],
): ScenarioDocument {
  const id = childScenarioId(name, parent.id, diff)
  return {
    schema_version: '0.2',
    id,
    name,
    description: diff.length
      ? `What-if from ${parent.name}: ${diff.map((d) => d.path.replace(/^levers\./, '')).join(', ')}`
      : `Copy of ${parent.name}`,
    parent: parent.id,
    created: new Date().toISOString(),
    levers: leversPatch(diff),
    ensemble: { mechanisms: parent.ensemble?.mechanisms ?? 'all' },
    user: true,
  }
}

/** Human form of a lever value for the diff list. */
export function fmtLeverValue(v: unknown): string {
  if (v == null) return '—'
  if (typeof v === 'boolean') return v ? 'on' : 'off'
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : String(Number(v.toFixed(4)))
  if (Array.isArray(v)) return v.map(fmtLeverValue).join(', ')
  if (typeof v === 'object')
    return Object.entries(v as Record<string, unknown>)
      .map(([k, x]) => `${k}: ${fmtLeverValue(x)}`)
      .join(', ')
  return String(v).replace(/_/g, ' ')
}
