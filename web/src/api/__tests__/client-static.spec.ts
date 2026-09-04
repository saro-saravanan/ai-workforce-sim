/**
 * Static mode of the API client (contracts §18): every document comes from `${BASE_URL}static/`
 * as written by `python -m aiwsim_api.export_static`. `fetch` is replaced by a file table.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ResultsDocument, ScenarioDocument } from '@/types/results'
import resultsA from '@/mock/results.json'
import resultsB from '@/mock/results-b.json'
import scenarios from '@/mock/scenarios.json'
import storyJson from '@/mock/story.json'

type Api = typeof import('@/api/client')

const BASE = '/ai-workforce-sim/'
const HASH_A = 'sha256:aaaa'
const HASH_B = 'sha256:bbbb'

function withHash(src: unknown, id: string, hash: string): ResultsDocument {
  const d = structuredClone(src) as ResultsDocument
  d.meta.scenario_id = id
  d.meta.scenario_hash = hash
  d.meta.static = true
  return d
}
const docA = withHash(resultsA, 'baseline', HASH_A)
const docB = withHash(resultsB, 'eu-delay-deepseek-2027', HASH_B)

const manifest = {
  generated_at: '2026-09-02T00:00:00+00:00',
  spec_version: '0.2',
  data_version: 'test',
  draws: 200,
  runs: [
    { id: 'baseline', name: 'Consensus central', parent: null, description: 'the defaults', preset: false, hash: HASH_A, draws: 200, ensemble: 'all', file: 'runs/baseline.json' },
    { id: 'eu-delay-deepseek-2027', name: 'EU delay', parent: 'baseline', description: '', preset: false, hash: HASH_B, draws: 200, ensemble: 'all', file: 'runs/eu-delay-deepseek-2027.json' },
    { id: 'orphan', name: '', parent: 'baseline', description: '', preset: true, hash: 'sha256:cccc', draws: 1, ensemble: 'central', file: 'runs/orphan.json' },
  ],
  compares: [{ a: 'baseline', b: 'eu-delay-deepseek-2027', file: 'compare/baseline__eu-delay-deepseek-2027.json' }],
  levers: 'levers.json',
  scenarios: 'scenarios.json',
  regions: 'regions.json',
  actors: 'actors.json',
  geo: { us_states: 'geo/us-states.geojson', world: 'geo/world.geojson' },
  insights: {
    baseline: 'insights/baseline.json',
    'eu-delay-deepseek-2027__vs__baseline': 'insights/eu-delay-deepseek-2027__vs__baseline.json',
  },
  briefs: {
    baseline: { md: 'briefs/baseline.md', html: 'briefs/baseline.html' },
    'eu-delay-deepseek-2027': { md: 'briefs/eu-delay-deepseek-2027.md', html: 'briefs/eu-delay-deepseek-2027.html' },
  },
  story: { baseline: 'story/baseline.json' },
  story_regions: { baseline: { US: 'story/baseline.json', EU: 'story/baseline.EU.json' } },
  exec_briefs: { baseline: { md: 'briefs/baseline.exec.md', html: 'briefs/baseline.exec.html' } },
  policy_scenarios: ['policy-retraining'],
  future_scenarios: ['preset-seba-rethinkx'],
}

const insight = (key: string) => ({
  key,
  title: key,
  statement: '',
  mechanism: '',
  confidence: 'high',
  surprise: 0.5,
  evidence: {},
  metric: null,
  quarter: '2040Q4',
  region: 'US',
})
const compareFile = {
  diff: [{ path: 'levers.regulation.EU.ai_act', from: 'baseline', to: 'delayed_2y', mechanism: 'file' }],
  delta: { series: { employment_pct_vs_baseline: { p10: [0], p50: [0], p90: [0] } }, states: [], occupations: [] },
  confidence: {},
}

let files: Record<string, unknown>
let calls: string[]
let api: Api

function fakeResponse(url: string) {
  const key = url.startsWith(`${BASE}static/`) ? url.slice(`${BASE}static/`.length) : url
  if (!(key in files))
    return { ok: false, status: 404, statusText: 'Not Found', json: async () => ({}), text: async () => '' }
  const body = files[key]
  return {
    ok: true,
    status: 200,
    statusText: 'OK',
    json: async () => structuredClone(body),
    text: async () => (typeof body === 'string' ? body : JSON.stringify(body)),
  }
}

beforeEach(async () => {
  files = {
    'manifest.json': manifest,
    'runs/baseline.json': docA,
    'runs/eu-delay-deepseek-2027.json': docB,
    'scenarios.json': scenarios,
    'levers.json': [{ path: 'levers.capability.doubling_months', label: 'Doubling', group: 'capability', type: 'number' }],
    'regions.json': [{ region_id: 'US', name: 'United States' }],
    'actors.json': { actors: [{ actor_id: 'openai', name: 'OpenAI', region_id: 'US', role: 'lab', weights_posture: 'closed' }], releases: [] },
    'geo/us-states.geojson': { type: 'FeatureCollection', features: [] },
    'geo/world.geojson': { type: 'FeatureCollection', features: [] },
    'compare/baseline__eu-delay-deepseek-2027.json': compareFile,
    'insights/baseline.json': { scenario_hash: HASH_A, region: 'US', top: Array.from({ length: 10 }, (_, i) => insight(`k${i}`)), candidates: [], method: 'file' },
    'insights/eu-delay-deepseek-2027__vs__baseline.json': { scenario_hash: HASH_B, region: 'US', top: [insight('delta')], candidates: [], method: 'file-vs' },
    'briefs/baseline.md': '# baseline brief (file)',
    'briefs/eu-delay-deepseek-2027.md': '# B brief with compare (file)',
    'story/baseline.json': { ...storyJson, scenario_hash: HASH_A },
    'story/baseline.EU.json': { ...storyJson, scenario_hash: HASH_A, region: 'EU', region_name: 'European Union (EU-27)' },
  }
  calls = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string | URL | Request) => {
      const url = String(input)
      calls.push(url)
      return fakeResponse(url)
    }),
  )
  vi.stubEnv('VITE_STATIC', '1')
  vi.stubEnv('VITE_USE_MOCK', '')
  vi.stubEnv('BASE_URL', BASE)
  vi.resetModules()
  api = await import('@/api/client')
  api.resetStaticCache()
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('static mode flags', () => {
  it('is on with VITE_STATIC=1 and builds URLs under the base path', () => {
    expect(api.USE_STATIC).toBe(true)
    expect(api.USE_MOCK).toBe(false)
    expect(api.staticUrl('runs/baseline.json')).toBe('/ai-workforce-sim/static/runs/baseline.json')
    expect(api.staticUrl('/manifest.json')).toBe('/ai-workforce-sim/static/manifest.json')
  })
})

describe('manifest → scenarios', () => {
  it('lists the runs as scenario summaries with their hashes, fetching the manifest once', async () => {
    const list = await api.fetchScenarios()
    expect(list.map((s) => s.id)).toEqual(['baseline', 'eu-delay-deepseek-2027', 'orphan'])
    expect(list[0]).toMatchObject({ name: 'Consensus central', parent: null, preset: false, user: false, hash: HASH_A })
    expect(list[2]).toMatchObject({ name: 'orphan', preset: true })
    await api.fetchScenarios()
    expect(calls.filter((u) => u.endsWith('manifest.json'))).toHaveLength(1)
    expect(calls[0]).toBe('/ai-workforce-sim/static/manifest.json')
  })

  it('resolves a scenario against its ancestors from scenarios.json', async () => {
    const child = await api.fetchScenario('eu-delay-deepseek-2027')
    const levers = child.levers as { regulation: { EU: { ai_act: string } }; capability: { doubling_months: number } }
    expect(levers.regulation.EU.ai_act).toBe('delayed_2y')
    expect(levers.capability.doubling_months).toBe(5) // inherited from baseline
    expect(child.shocks?.map((s) => s.id)).toEqual(['deepseek-open-2027'])
    expect(calls.filter((u) => u.endsWith('scenarios.json'))).toHaveLength(1)
  })

  it('builds a scenario from the manifest entry when scenarios.json does not carry it', async () => {
    const orphan = await api.fetchScenario('orphan')
    expect(orphan.id).toBe('orphan')
    expect(orphan.parent).toBe('baseline')
    expect((orphan.levers as { labor: { reinstatement_ratio: number } }).labor.reinstatement_ratio).toBe(0.4)
    await expect(api.fetchScenario('nope')).rejects.toThrow(/unknown scenario nope/)
  })
})

describe('runs', () => {
  it('loads a run by scenario id', async () => {
    const doc = await api.runScenario('baseline')
    expect(doc.meta.scenario_hash).toBe(HASH_A)
    expect(calls).toContain('/ai-workforce-sim/static/runs/baseline.json')
  })

  it('loads a run by result hash (compare= in the URL)', async () => {
    const doc = await api.runScenario(HASH_B)
    expect(doc.meta.scenario_id).toBe('eu-delay-deepseek-2027')
    expect(calls).toContain('/ai-workforce-sim/static/runs/eu-delay-deepseek-2027.json')
  })

  it('rejects an unknown id with the demo message', async () => {
    await expect(api.runScenario('preset-x')).rejects.toThrow(/Static demo: no precomputed run for "preset-x"/)
  })

  it('refuses to run or save a new scenario', async () => {
    const child: ScenarioDocument = { schema_version: '0.2', id: 'c', name: 'c', parent: 'baseline', levers: {} }
    await expect(api.runScenarioDoc(child)).rejects.toThrow(
      'Static demo: running a new scenario needs the local API (make demo). Pick a precomputed scenario instead.',
    )
    await expect(api.saveScenario(child)).rejects.toThrow(/^Static demo: saving a scenario needs the local API/)
    expect(calls.filter((u) => u.includes('/api/'))).toHaveLength(0)
  })
})

describe('compare', () => {
  it('uses the exporter file for the listed pair in that order', async () => {
    const c = await api.compareRuns(docA, docB, 'US')
    expect(c.diff[0]?.mechanism).toBe('file')
    expect(calls).toContain('/ai-workforce-sim/static/compare/baseline__eu-delay-deepseek-2027.json')
  })

  it('falls back to the client-side paired difference when reversed, for another region, or when the file is missing', async () => {
    const reversed = await api.compareRuns(docB, docA, 'US')
    expect(reversed.diff[0]?.mechanism).not.toBe('file')
    expect(reversed.delta.series.employment_pct_vs_baseline?.p50).toHaveLength(docA.meta.quarters.length)
    const eu = await api.compareRuns(docA, docB, 'EU')
    expect(eu.diff[0]?.mechanism).not.toBe('file')
    expect(calls.filter((u) => u.includes('/compare/'))).toHaveLength(0)

    delete files['compare/baseline__eu-delay-deepseek-2027.json']
    const missing = await api.compareRuns(docA, docB, 'US')
    expect(missing.delta.series.employment_pct_vs_baseline?.p50).toHaveLength(docA.meta.quarters.length)
  })
})

describe('insights', () => {
  it('reads the run file and trims to n', async () => {
    const res = await api.fetchInsights(HASH_A, 'US', 3, docA)
    expect(res.method).toBe('file')
    expect(res.top).toHaveLength(3)
  })

  it('reads the __vs__ file when a compare hash is passed and it exists', async () => {
    const res = await api.fetchInsights(HASH_B, 'US', 3, docB, HASH_A)
    expect(res.method).toBe('file-vs')
    expect(res.top[0]?.key).toBe('delta')
  })

  it('falls back to the client-side port without a file, and for other regions', async () => {
    const noFile = await api.fetchInsights(HASH_B, 'US', 3, docB) // no plain file for B
    expect(noFile.method).toMatch(/client-side/)
    expect(noFile.scenario_hash).toBe(HASH_B)
    expect(noFile.top.length).toBeGreaterThan(0)
    const eu = await api.fetchInsights(HASH_A, 'EU', 3, docA)
    expect(eu.method).toMatch(/client-side/)
    expect(eu.region).toBe('EU')
    expect(calls.filter((u) => u.includes('/insights/'))).toHaveLength(0)
  })
})

describe('briefs', () => {
  it('points briefUrl at the exporter files once the manifest is known', async () => {
    await api.fetchScenarios()
    expect(api.briefUrl(HASH_A, 'html', 'US')).toBe('/ai-workforce-sim/static/briefs/baseline.html')
    expect(api.briefUrl('orphan', 'md')).toBe('/ai-workforce-sim/static/briefs/orphan.md')
  })

  it('matches a precomputed brief only for the request it was built for', async () => {
    expect(await api.staticBriefFile(HASH_A, 'md', 'US')).toBe('/ai-workforce-sim/static/briefs/baseline.md')
    expect(await api.staticBriefFile(HASH_A, 'md', 'US', HASH_B)).toBeNull() // baseline was not paired
    expect(await api.staticBriefFile(HASH_B, 'md', 'US', HASH_A)).toBe(
      '/ai-workforce-sim/static/briefs/eu-delay-deepseek-2027.md',
    )
    expect(await api.staticBriefFile(HASH_B, 'md', 'US')).toBeNull() // the file carries the compare
    expect(await api.staticBriefFile(HASH_A, 'md', 'EU')).toBeNull()
  })

  it('serves the file when it matches and builds the brief client-side otherwise', async () => {
    expect(await api.fetchBriefMarkdown(HASH_A, 'US', null, docA)).toBe('# baseline brief (file)')
    const built = await api.fetchBriefMarkdown(HASH_A, 'EU', null, docA)
    expect(built).toMatch(/^# baseline — AI workforce brief/)
    expect(built).toMatch(/Region: \*\*EU\*\*/)
    const paired = await api.fetchBriefMarkdown(HASH_A, 'US', HASH_B, docA, docB)
    expect(paired).toMatch(/Paired comparison/)
  })
})

describe('catalogues, geo and chat', () => {
  it('reads levers, regions, actors and geo from the manifest paths', async () => {
    expect((await api.fetchLevers())[0]?.path).toBe('levers.capability.doubling_months')
    expect((await api.fetchRegions())[0]?.region_id).toBe('US')
    expect((await api.fetchActors()).actors[0]?.actor_id).toBe('openai')
    expect((await api.fetchStatesGeo()).type).toBe('FeatureCollection')
    expect((await api.fetchWorldGeo()).type).toBe('FeatureCollection')
    expect(calls.slice(1)).toEqual([
      '/ai-workforce-sim/static/levers.json',
      '/ai-workforce-sim/static/regions.json',
      '/ai-workforce-sim/static/actors.json',
      '/ai-workforce-sim/static/geo/us-states.geojson',
      '/ai-workforce-sim/static/geo/world.geojson',
    ])
  })

  it('answers explain and sensitivity from the document', async () => {
    expect(await api.fetchSensitivity(docA)).toBe(docA.tornado)
    const ex = await api.fetchExplain(docA, 'employment_pct_vs_baseline', '2040Q4', 'US')
    expect(ex?.confidence.level).toBeDefined()
    expect(calls).toHaveLength(0)
  })

  it('reports the chat layer as unavailable and rejects sends', async () => {
    const status = await api.fetchChatStatus()
    expect(status).toEqual({
      available: false,
      model: 'none',
      reason: 'Static demo: the chat layer needs the local API server with ANTHROPIC_API_KEY set.',
    })
    await expect(
      api.sendChat({ messages: [], context: {}, confirmed_proposals: [], mode: 'chat' }),
    ).rejects.toThrow(/Static demo: the chat layer/)
  })
})

describe('story, outlook and executive brief (contracts §26–28)', () => {
  it('reads the story file listed in the manifest, by hash or by id', async () => {
    const st = await api.fetchStory(docA, 'US')
    expect(st.scenario_hash).toBe(HASH_A)
    expect(st.beats).toHaveLength(7)
    expect(st.policies.map((p) => p.scenario_id)).toContain('policy-retraining')
    expect(calls).toContain('/ai-workforce-sim/static/story/baseline.json')
    // World reads the U.S. story
    const world = await api.fetchStory(docA, 'world')
    expect(world.region).toBe('US')
  })

  it("reads a region's own story file and falls back to the U.S. one without it", async () => {
    const eu = await api.fetchStory(docA, 'EU')
    expect(eu.region).toBe('EU')
    expect(eu.region_name).toBe('European Union (EU-27)')
    expect(calls).toContain('/ai-workforce-sim/static/story/baseline.EU.json')
    const jp = await api.fetchStory(docA, 'JP')
    expect(jp.region).toBe('US')
    expect(calls.filter((u) => u.endsWith('/story/baseline.JP.json'))).toHaveLength(0)
  })

  it('rejects a run without an exported story', async () => {
    await expect(api.fetchStory(docB, 'US')).rejects.toThrow(/Static demo: no story for "eu-delay-deepseek-2027"/)
    expect(calls.filter((u) => u.includes('/story/'))).toHaveLength(0)
  })

  it('computes the outlook client-side, with the story beats when there is a story', async () => {
    const res = await api.fetchOutlook(docA, '53-3054', '16-24', 'US')
    expect(res.region).toBe('US')
    expect(res.beats.map((b) => b.id)).toEqual(['jobs', 'hiring', 'pay'])
    expect(res.occupation?.title).toBe('Taxi drivers and chauffeurs')
    expect(res.occupation?.sentence).toContain('task-hours')
    expect(res.age?.band).toBe('16-24')
    expect(calls.filter((u) => u.includes('/api/'))).toHaveLength(0)
    // no story file: the cards still work, without the beats
    const noStory = await api.fetchOutlook(docB, '53-3054', null, 'EU')
    expect(noStory.beats).toEqual([])
    expect(noStory.occupation?.occ_code).toBe('53-3054')
    expect(noStory.age).toBeUndefined()
    expect(noStory.note).toMatch(/U\.S\. detail/)
  })

  it('points the executive brief at the exporter page once the manifest is known', async () => {
    expect(api.execBriefUrl(docA)).toBeNull() // manifest not fetched yet
    await api.fetchScenarios()
    expect(api.execBriefUrl(docA)).toBe('/ai-workforce-sim/static/briefs/baseline.exec.html')
    expect(api.execBriefUrl(docB)).toBeNull()
  })
})
