<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useResultsStore } from '@/stores/results'
import { REPO_URL } from '@/api/client'
import { CONFIDENCE_GLYPH } from '@/lib/confidence'

const results = useResultsStore()

const BRANCH = 'spec/model-v0.1'
const docUrl = (path: string) => `${REPO_URL}/blob/${BRANCH}/${path}`

const meta = computed(() => results.meta)
const flags = computed(() => Object.entries(meta.value?.data_flags ?? {}))
const runTime = computed(() => {
  const t = meta.value?.run_at
  if (!t) return '—'
  const d = new Date(t)
  return Number.isNaN(d.getTime()) ? t : d.toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC').replace(/Z$/, ' UTC')
})

/** The five layers of docs/model-spec.md, one sentence each. */
const LAYERS = [
  {
    name: 'Task exposure',
    spec: '§2',
    text: 'Each O*NET task is scored for whether software-only AI can ever do it, when it becomes feasible on the capability clock, and whether doing it pays at the occupation’s wage.',
  },
  {
    name: 'Capability & cost',
    spec: '§3',
    text: 'A global frontier clock, extrapolated from METR’s task-horizon series with a domain-transfer discount for non-software work, with prices falling over time; regions and actors see the frontier after their access lags.',
  },
  {
    name: 'Adoption',
    spec: '§4',
    text: 'Firms adopt when it pays, along a diffusion curve slowed by sector and small-firm friction, with intensity rising inside adopters and AI-native entrants arriving without integration cost.',
  },
  {
    name: 'Labor flows',
    spec: '§5',
    text: 'Automated task-hours become displacement; attrition and hiring freezes absorb it first and layoffs second, demand response and reinstatement offset it, and displaced workers are tracked into re-employment, retraining, unemployment or exit.',
  },
  {
    name: 'Macro',
    spec: '§6',
    text: 'Output, prices, real wages, the wage share and AI rents by value-chain stage follow from the task-level changes and the demand feedback; nothing clears in general equilibrium.',
  },
]

const READING = [
  'Everything is relative to a frozen-AI baseline: the same economy with no frontier AI after 2023. A value of −3% employment means 3% below that counterfactual, not below today.',
  'Bands are the 10th to 90th percentile across correlated parameter draws (spec §7.1), re-centred on the scenario’s lever values.',
  'The dashed line is the central parameter set: the scenario exactly as specified, with every parameter at its central value.',
  `Confidence glyphs (spec §7.3): ${CONFIDENCE_GLYPH.high} high when the sign holds in every mechanism cell and in at least 90% of draws and no single parameter flips it within its range; ${CONFIDENCE_GLYPH.medium} medium when the sign holds in all cells and at least 70% of draws; ${CONFIDENCE_GLYPH.low} low otherwise.`,
  'FIXTURE hatching on a map marks a region or state whose occupational composition is imputed rather than observed; the run’s fixtures are listed in the data flags below.',
  'Every parameter carries a provenance tag: S sourced, D derived from cited data by a stated transformation, E estimated by the authors. E-tagged parameters are estimates and are exposed as levers.',
]

const REAL_DATA = [
  'O*NET task statements with the Eloundou et al. “GPTs are GPTs” exposure labels (openai/GPTs-are-GPTs replication data, MIT).',
  'OEWS May 2021 national employment and wages (831 detailed occupations) and BLS Employment Projections 2020–30, mirrored in the same repository; the underlying BLS data are public domain.',
  'METR time horizons, as the trend of the capability clock; the series is software-specific, so non-software work carries a domain-transfer discount.',
  'Census BTOS AI-use shares, hyperscaler capex from SEC filings and the regulatory timeline, transcribed from the data inventory with secondary confirmation.',
  'Natural Earth admin-0 and admin-1 (public domain) for the maps, regional membership, population and GDP.',
]

const FIXTURES = [
  { name: 'State splits', text: 'population share proxy for employment share: every state has the national occupational mix scaled by its 2020 Census population, so the state map shows size, not geography.' },
  { name: 'Sector split', text: 'a single sector ALL; demand elasticity, labor cost share and friction are one number each until the OEWS occupation × industry matrix is ingested.' },
  { name: 'Non-U.S. occupation structure', text: 'the U.S. task mix tilted by income, with wages = U.S. wage × regional wage level; regional results are composition effects plus access lag, wage level, regulation and rent flows, not regional data.' },
  { name: 'Trade weights', text: 'import shares split by partner GDP; the trade linkage is inert until the sector fixture is replaced.' },
  { name: 'Cohort shares', text: 'U.S. age, education and income-decile shares applied to every region; the age marginals are approximate (CPS 2024, E).' },
]

const LIMITATIONS = [
  'No general equilibrium: prices fall with costs and wages adjust partially, but nothing clears; tail scenarios (more than 15% displacement in a decade) carry a validity warning.',
  'Regional occupation fixtures: everything outside the U.S. is the U.S. task mix tilted by income, so cross-region differences should be read as the model’s mechanism speaking.',
  'Single-country presets: the report-replication presets (Acemoglu 2024, Goldman Sachs 2023, IMF 2024) target U.S. headline numbers; their regional results inherit the fixtures above.',
  'Chat not exercised live: the Ask layer has been run only against a scripted fake client, never a live model; in the static demo it is switched off.',
]

const LINKS = [
  { label: 'Repository', href: REPO_URL, note: 'source, data provenance, scenarios' },
  { label: 'Methodology', href: docUrl('docs/methodology.md'), note: 'how the model is built and calibrated' },
  { label: 'Model specification', href: docUrl('docs/model-spec.md'), note: 'v0.2, with §16 implementation notes' },
  { label: 'Contracts', href: docUrl('docs/contracts.md'), note: 'results document, API and static export' },
]
</script>

<template>
  <article class="about">
    <header>
      <h2>About this tool</h2>
      <p class="lede">
        AI Workforce Sim is an interactive, multi-region simulation of how AI reshapes work and the
        economy between 2024 and 2040. Ten regions run jointly through a shared capability clock,
        and every number the views show is the difference between a scenario and a frozen-AI
        counterfactual in which no frontier AI arrives after 2023. The levers change the scenario;
        a deterministic model produces the results, and the Ask layer only reads them.
      </p>
    </header>

    <section class="card">
      <h3>How the model works</h3>
      <ol class="layers">
        <li v-for="l in LAYERS" :key="l.name">
          <span class="term">{{ l.name }}</span> <span class="text">{{ l.text }}</span>
          <span class="muted spec">spec {{ l.spec }}</span>
        </li>
      </ol>
    </section>

    <section class="card">
      <h3>The story, your outlook and the scoreboard</h3>
      <p class="text-p">
        The <RouterLink :to="{ path: '/story', query: $route.query }">Story</RouterLink> view
        reads the current run as one reconciled set of numbers and seven findings in plain
        language, each with its likely range, how sure the model is of the direction, and what
        would change it; it ends with the policy runs read against the baseline and an executive
        brief without parameter codes. Named futures sit beside the model's own extremes: the
        Seba / RethinkX disruption preset is one of them and can be opened as a scenario.
        <RouterLink :to="{ path: '/outlook', query: $route.query }">Your outlook</RouterLink>
        narrows the same run to one occupation and one age band. The forecast scoreboard on the
        Story view puts named public claims (Goldman Sachs, IMF, Acemoglu, RethinkX and others)
        next to the run's central value and likely range and says whether the model lands within,
        below or above each claim; where the model tracks only a neighbouring quantity, the row
        says so.
      </p>
    </section>

    <section class="card">
      <h3>How to read the numbers</h3>
      <ul class="plain">
        <li v-for="(r, i) in READING" :key="i">{{ r }}</li>
      </ul>
    </section>

    <section class="card">
      <h3>Data</h3>
      <p class="muted small">Sources with a provenance record in <code>data/provenance/</code>.</p>
      <ul class="plain">
        <li v-for="(d, i) in REAL_DATA" :key="i">{{ d }}</li>
      </ul>
      <p class="muted small">
        Fixtures, labelled <span class="badge fixture">FIXTURE</span> and surfaced in
        <code>meta.data_flags</code>:
      </p>
      <ul class="plain">
        <li v-for="f in FIXTURES" :key="f.name">
          <span class="term">{{ f.name }}</span> <span class="text">{{ f.text }}</span>
        </li>
      </ul>
    </section>

    <section class="card">
      <h3>Run information</h3>
      <template v-if="meta">
        <dl class="meta">
          <dt>Scenario</dt>
          <dd>{{ results.scenarioName }} <span class="muted">({{ meta.scenario_id }})</span></dd>
          <dt>Spec version</dt>
          <dd class="mono">{{ meta.spec_version }} <span class="muted">· schema {{ meta.schema_version }}</span></dd>
          <dt>Data version</dt>
          <dd class="mono">{{ meta.data_version ?? '—' }}</dd>
          <dt>Draws</dt>
          <dd class="mono">
            {{ meta.draws }} <span class="muted">· seed {{ meta.seed }}</span>
          </dd>
          <dt>Ensemble</dt>
          <dd class="mono">
            {{ meta.ensemble }}
            <span v-if="meta.cells?.length" class="muted">· {{ meta.cells.length }} mechanism cells</span>
          </dd>
          <dt>Regions</dt>
          <dd class="mono">{{ meta.regions.join(', ') }}</dd>
          <dt>Hash</dt>
          <dd class="mono hash">{{ meta.scenario_hash }}</dd>
          <dt>Run time</dt>
          <dd class="mono">{{ runTime }}<span v-if="meta.static" class="muted"> · static export</span></dd>
          <dt>Baseline</dt>
          <dd class="mono">{{ meta.baseline }}</dd>
        </dl>
        <h4 class="sub">Data flags</h4>
        <table class="data flags">
          <thead>
            <tr>
              <th scope="col">Table</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="[k, v] in flags" :key="k">
              <td class="mono">{{ k }}</td>
              <td>
                <span v-if="v === 'FIXTURE'" class="badge fixture">FIXTURE</span>
                <span v-else>{{ v }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </template>
      <p v-else class="muted">No run loaded.</p>
    </section>

    <section class="card">
      <h3>Documents</h3>
      <ul class="plain links">
        <li v-for="l in LINKS" :key="l.href">
          <a :href="l.href" target="_blank" rel="noopener">{{ l.label }}</a>
          <span class="muted"> · {{ l.note }}</span>
        </li>
      </ul>
      <p class="muted small">Links open the <code>{{ BRANCH }}</code> branch on GitHub.</p>
    </section>

    <section class="card">
      <h3>Limitations</h3>
      <ul class="plain">
        <li v-for="(l, i) in LIMITATIONS" :key="i">{{ l }}</li>
      </ul>
    </section>
  </article>
</template>

<style scoped>
.about {
  max-width: 760px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-bottom: 24px;
  font-size: 15px;
  line-height: 1.5;
}
.about h2 {
  font-size: 22px;
  margin-bottom: 6px;
}
.about h3 {
  font-size: 16px;
  margin-bottom: 8px;
}
.about h4.sub {
  font-size: 14px;
  font-weight: 600;
  margin: 14px 0 6px;
  color: var(--ink-2);
}
.lede {
  margin: 0;
  color: var(--ink-2);
  font-size: 16px;
}
.card {
  padding: 14px 18px;
}
ol.layers,
ul.plain {
  margin: 0;
  padding-left: 22px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
ul.plain {
  padding-left: 20px;
}
.term {
  font-weight: 600;
}
.spec {
  font-weight: 400;
  font-size: 13px;
  margin-left: 4px;
}
.small {
  font-size: 14px;
  margin: 8px 0 4px;
}
code {
  font-size: 13px;
  background: var(--surface-2);
  padding: 1px 6px;
  border-radius: 4px;
}
dl.meta {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 4px 16px;
  margin: 0;
  font-size: 14px;
}
dl.meta dt {
  color: var(--muted);
}
dl.meta dd {
  margin: 0;
  min-width: 0;
}
.hash {
  overflow-wrap: anywhere;
  font-size: 13px;
}
table.flags {
  width: auto;
  min-width: 320px;
}
table.flags th {
  cursor: default;
  position: static;
}
.links a,
.text-p a {
  color: var(--accent-ink);
}
.text-p {
  margin: 0;
  line-height: 1.55;
}
</style>
