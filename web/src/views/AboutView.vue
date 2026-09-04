<script setup lang="ts">
import { computed, nextTick, onMounted, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useResultsStore } from '@/stores/results'
import { REPO_URL, USE_MOCK, USE_STATIC } from '@/api/client'
import type { ScenarioSummary } from '@/types/results'
import { CONFIDENCE_GLYPH } from '@/lib/confidence'

const results = useResultsStore()
const route = useRoute()

/** `#why`, `#author`, `#scenarios`, `#static-demo`: the main pane scrolls, not the window, so scroll the target into view here */
function scrollToHash() {
  const id = route.hash.replace(/^#/, '')
  if (!id) return
  void nextTick(() => document.getElementById(id)?.scrollIntoView({ block: 'start', behavior: 'smooth' }))
}
onMounted(scrollToHash)
watch(() => route.hash, scrollToHash)

const BRANCH = 'main'
const docUrl = (path: string) => `${REPO_URL}/blob/${BRANCH}/${path}`
/** the one-page current-model statement (Phase 9) */
const CURRENT_MODEL_URL = docUrl('docs/current-model.md')

const meta = computed(() => results.meta)

/** The scenario catalogue, grouped by what each scenario is for (ids follow `scenarios/*.json`). */
interface ScenarioGroup {
  label: string
  note: string
  items: ScenarioSummary[]
}
function groupOf(s: ScenarioSummary): string {
  if (s.user) return 'user'
  if (s.id === 'baseline') return 'baseline'
  if (s.id.startsWith('preset-seba')) return 'future'
  if (s.id.startsWith('preset-')) return 'preset'
  if (s.id.startsWith('policy-')) return 'policy'
  if (s.id.startsWith('variant-')) return 'variant'
  if (s.id.startsWith('config-')) return 'config'
  return 'whatif'
}
const GROUPS: Array<{ key: string; label: string; note: string }> = [
  { key: 'baseline', label: 'Baseline', note: 'Every lever at its central value, the structural ensemble on, no shocks. Everything else is read against it.' },
  {
    key: 'preset',
    label: 'Report replications',
    note: 'Published estimates rebuilt as lever settings (spec §8.4): the same engine with that report’s assumptions, so its headline can be compared with the baseline’s.',
  },
  {
    key: 'future',
    label: 'Named futures',
    note: 'Whole worldviews as scenarios; the Story view shows them beside the model’s own extremes, and each can be opened as a run.',
  },
  { key: 'policy', label: 'Policy runs', note: 'One policy each on top of the baseline; the Story view reads them as differences from it.' },
  { key: 'variant', label: 'Behavioural variants', note: 'The same AI with employers or wages behaving differently, at the edge of the fitted ranges.' },
  { key: 'config', label: 'Configurations', note: 'The same scenario with a layer switched off, for the regional decomposition.' },
  { key: 'whatif', label: 'What-ifs', note: 'Example children of the baseline: a few levers moved, sometimes a shock.' },
  { key: 'user', label: 'Saved by you', note: 'Scenarios saved through the levers panel (local API only).' },
]
const scenarioGroups = computed<ScenarioGroup[]>(() =>
  GROUPS.map((g) => ({ ...g, items: results.scenarios.filter((s) => groupOf(s) === g.key) })).filter((g) => g.items.length > 0),
)
function openScenario(id: string) {
  if (id !== results.scenarioId) results.scenarioId = id
}
const mode = computed(() => (USE_MOCK ? 'mock' : USE_STATIC ? 'static' : 'api'))

/** Why this exists: the questions the model is trying to answer, each with the view that speaks to it (docs/why.md). */
const QUESTIONS: Array<{ q: string; a: string; path: string; label: string }> = [
  {
    q: 'Will there be work for my children and grandchildren, and what kind?',
    a: 'Not "will jobs exist", which is too easy to answer with yes, but how many fewer than there would have been, in which occupations, and whether the work that remains is the kind a person can build a life on.',
    path: '/story',
    label: 'The first finding, and the Occupations view',
  },
  {
    q: 'Do the jobs disappear in a crash, or do they quietly stop being offered?',
    a: 'There is a world of difference between a layoff and a position that is never posted. The first hits someone with a mortgage; the second hits someone with a diploma and no first job. The model keeps those two ledgers apart on purpose.',
    path: '/flows',
    label: 'The second finding, and the Flows view',
  },
  {
    q: 'Who pays first: the people in jobs today, or the ones trying to get their first one?',
    a: 'This is the question I care about most. If employers cut through attrition rather than layoffs, the young carry the shortfall while their parents are largely protected. That changes what advice a parent should give.',
    path: '/cohorts',
    label: 'The third finding, and the Cohorts view',
  },
  {
    q: 'If AI makes everything cheaper, do we get richer, and who keeps the gains?',
    a: 'Prices fall, real pay can rise, and at the same time the worker’s share of national income can shrink. All three can be true at once, and the model shows how.',
    path: '/economy',
    label: 'The fourth finding, and the Economy view',
  },
  {
    q: 'When? Is this a 2027 story or a 2040 story?',
    a: 'Office and analytical work is being reshaped now. Robots and self-driving vehicles have to be manufactured, approved and paid for, which takes years. Getting the sequence right matters more than getting any single number right.',
    path: '/supply',
    label: 'The fifth finding, the AI Supply view and the time scrubber',
  },
  {
    q: 'Where does the money go, and which countries come out ahead?',
    a: 'Someone collects the revenue from all of this: the model makers, the data centres, the chip makers. The regions are not affected equally, and the map shows who gains and who loses.',
    path: '/map',
    label: 'The sixth finding, and the Map',
  },
  {
    q: 'Will the trillion dollars a year going into data centres ever pay back, and for whom?',
    a: 'The four largest cloud companies spent about $400 billion on data centres, chips and power in 2025 and have guided to over $700 billion for 2026; the model carries that path past a trillion a year. On its central assumptions the producers’ revenue never catches up with the capital by 2040, while the productivity gain to the economy repays it by the early 2030s and lands with the firms that adopt AI and, through lower prices, their customers, not with the builders. That is the railway, electricity and fibre pattern: society earns the return and the builders earn a normal or poor one. Faster adoption, or prices held well above token cost, changes the answer, and both are levers.',
    path: '/story',
    label: 'Investment versus returns, on the Story view',
  },
  {
    q: 'For an investor or an operator: which businesses get cheaper to run, and which get competed away?',
    a: 'It depends on which side of the work a company sits. A company that buys exposed work (a manufacturer with a large back office, a bank with floors of analysts, a hospital with claims and billing staff) sees its costs fall and its margins widen, at least until competitors catch up and prices follow. A company that sells exposed work (a call-centre outsourcer, a translation agency, a law firm billing hours for document review, an offshore IT-services firm) sees the price of its product fall faster than its costs. A third group, AI-native entrants with no legacy cost base, takes share from both. The model puts a number on each side: how much of each sector’s labour cost is exposed, how far its prices fall, and how much of the saving flows on to the sectors that buy from it. In diligence, the first question I now ask of any target is which of the three it is.',
    path: '/economy',
    label: 'The Economy and Occupations views, and the sector levers in What if',
  },
  {
    q: 'How much of this is a choice, and how much is coming regardless?',
    a: 'The single biggest swing in the model is whether the productivity gains are spent back into the economy or pocketed. That is partly policy, partly corporate behaviour, and partly what each of us decides to pay for.',
    path: '/story',
    label: 'The seventh finding, and the named futures',
  },
  {
    q: 'What could a government actually do that helps, and what would it cost?',
    a: 'Retraining subsidies, wage insurance, a basic income, a shorter working week: each is a scenario you can run against the baseline, with its price tag and its financing.',
    path: '/story',
    label: 'The policy runs on the Story view, and the What if panel',
  },
  {
    q: 'What should I tell a seventeen-year-old choosing what to study?',
    a: 'The honest answer is that the deciles are stable and the individual ranks are not: which broad kinds of work are exposed is fairly robust across data sources, which exact occupation ranks where is not.',
    path: '/outlook',
    label: 'Your outlook, one occupation and one age at a time',
  },
  {
    q: 'Can any of this be trusted, and how would we know when it is wrong?',
    a: 'A model that cannot be wrong is worthless. This one is scored every quarter against what has already happened: firm adoption, announced AI-cited job cuts, AI industry revenue, data-centre spending. Where it misses, the page says so.',
    path: '/backtest',
    label: 'The Backtest view, and the ranges and confidence marks on every finding',
  },
  {
    q: 'What would change my mind?',
    a: 'Every finding lists what would move it. If you think the model is wrong, the levers are there: change the assumption and see what follows. That is the whole point.',
    path: '/story',
    label: 'What changes it, under every finding',
  },
]

/** the author (the profile page is the canonical source of this text) */
const AUTHOR = {
  name: 'Saro Saravanan',
  profile: 'https://saro-saravanan.github.io',
  linkedin: 'https://www.linkedin.com/in/saro-saravanan-a0978/',
  github: 'https://github.com/saro-saravanan',
}
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
  'O*NET task statements with the Eloundou et al. “GPTs are GPTs” exposure labels (openai/GPTs-are-GPTs replication data, MIT), classified into software, robot, vehicle and fixed-machine channels by task wording (rules v3, audited on a 120-statement sample).',
  'BLS OEWS May 2025: national employment and wages for 831 detailed occupations, the occupation × industry matrix (20 NAICS sectors) and the occupation × state file; BLS Employment Projections for the no-AI growth path.',
  'BEA 2024 summary input-output use table (through the BEA API): labour’s share of each sector’s gross output and value added, consumption shares, and the 20 × 20 direct-requirements matrix that propagates cost savings between sectors.',
  'METR time horizons, as the trend of the capability clock; the series is software-specific, so non-software work carries a domain-transfer discount.',
  'Census BTOS AI-use shares, Challenger, Gray & Christmas AI-cited job cuts, AI industry revenue and hyperscaler capex, as the backtest rows; two of them set a parameter and are marked as calibration targets.',
  'Natural Earth admin-0 and admin-1 (public domain) for the maps, regional membership, population and GDP.',
]

const FIXTURES = [
  { name: 'Non-U.S. occupation structure', text: 'the U.S. task mix tilted by income, with wages = U.S. wage × regional wage level; regional results are composition effects plus access lag, wage level, regulation and rent flows, not regional data. This is why the Story outside the U.S. marks its cohort finding as U.S. detail.' },
  { name: 'Trade weights', text: 'import shares split by partner GDP.' },
  { name: 'Cohort shares', text: 'U.S. age, education and income-decile shares (CPS 2024, approximate), modelled for the United States only.' },
  { name: 'Robot, content and trade parameters', text: 'the authors’ estimates (tagged E in the registry), exposed as levers.' },
]

const LIMITATIONS = [
  'No general equilibrium: prices fall with costs and wages adjust partially, but nothing clears; tail scenarios (more than 15% displacement in a decade) carry a validity warning.',
  'Regional occupation fixtures: everything outside the U.S. is the U.S. task mix tilted by income, so cross-region differences should be read as the model’s mechanism speaking.',
  'Single-country presets: the report-replication presets (Acemoglu 2024, Goldman Sachs 2023, IMF 2024) target U.S. headline numbers; their regional results inherit the fixtures above.',
  'The Ask tab exists only when the API server has a model key (ANTHROPIC_API_KEY); the static demo and the mock have none, so the panel shows Explain alone. The chat layer has been exercised against a scripted client, not a live model.',
  'The 2026 hold-out: refitting the two fitted parameters to 2025 alone under-predicts the 2026 rows (AI revenue, announced cuts), so the model’s 2025-to-2026 growth is slower than the data’s.',
]

const LINKS = [
  { label: 'Why I built this', href: docUrl('docs/why.md'), note: 'the questions behind the model, as a document' },
  { label: 'Repository', href: REPO_URL, note: 'source, data provenance, scenarios; collaborators welcome (MIT License)' },
  { label: 'Terms of use', href: docUrl('docs/terms.md'), note: 'no warranty, no liability, no advice; also on the /terms page' },
  { label: 'Methodology', href: docUrl('docs/methodology.md'), note: 'how the model is built and calibrated' },
  { label: 'Model specification', href: docUrl('docs/model-spec.md'), note: 'v0.3, with §16 implementation notes' },
  { label: 'Scenario files', href: `${REPO_URL}/tree/${BRANCH}/scenarios`, note: 'every scenario and preset as JSON, with its description and levers' },
  { label: 'Findings', href: docUrl('docs/findings-phase9b.md'), note: 'what the latest phase changed and why the headline moved' },
  { label: 'Contracts', href: docUrl('docs/contracts.md'), note: 'results document, API and static export' },
  { label: 'Current model', href: CURRENT_MODEL_URL, note: 'one page: fitted parameters and their targets (main branch)' },
]
</script>

<template>
  <article class="about">
    <header>
      <h2>About this tool</h2>
      <p class="lede">
        AI Workforce Sim is a structured scenario model of how AI reshapes work and the economy
        between 2024 and 2040, not a forecast: it is interactive and multi-region (model
        specification v0.3). Ten regions run jointly through a shared capability clock,
        and every number the views show is the difference between a scenario and a frozen-AI
        counterfactual in which no frontier AI arrives after 2023. The levers change the scenario;
        a deterministic model produces the results, and the Ask layer only reads them.
      </p>
    </header>

    <section class="card why" id="why">
      <h3>Why I built this</h3>
      <p class="text-p">
        Like most people, I have spent a good deal of the last few years fretting about what
        accelerating AI means for my children, my grandchildren, and the society they will live
        in. I have spent my career building software, and I know what it looks like when a
        technology stops being a demo and starts changing who gets hired. This time the
        technology is aimed at the kind of work I do, and the kind of work I hoped they would do.
      </p>
      <p class="text-p">
        The public conversation did not help. One week the headline said half of all jobs would
        vanish; the next said AI would make everyone richer. Every number came from somewhere I
        could not see, with assumptions I could not change, and none of them agreed with each
        other. I found I could not answer the simple questions my family asked me at dinner. And in
        my day job, technology due diligence for private-equity and venture investors, the same
        questions arrived in a suit: will the capital pouring into AI earn a return, and which of
        the companies we are looking at will be on the right side of it?
      </p>
      <p class="text-p">
        So I built a model. Not to predict the future, which nobody can, but to make the
        assumptions visible, so that when we disagree we disagree about the right things. Every
        number it produces is a difference between a world where AI keeps improving and a world
        where it stopped in 2023. Every parameter has a source, a range and a lever. When the
        model is wrong, and it will be, you can see where.
      </p>
      <p class="text-p">
        It does not make one prediction. It produces projections under different
        <strong>scenarios</strong> and <strong>presets</strong>, and shows the range between them.
        A scenario changes the world the model runs in: the baseline with every assumption at its
        central value; a what-if in which the EU AI Act is delayed two years and an open-weights
        frontier model arrives from China in 2027; policy runs that add a retraining subsidy, a
        $500-a-month basic income paid for by an income-tax surcharge, wage insurance, or a
        36-hour week; variants in which employers cut through layoffs rather than attrition, or
        wages fall to clear the market. A preset rebuilds someone else's published estimate with
        the same engine, so you can see how much of the disagreement between reports is the data
        and how much is the assumptions: Acemoglu's 2024 paper, Goldman Sachs 2023, the IMF's 2024
        study, and Tony Seba's RethinkX disruption thesis, which the model carries as a named
        future rather than a forecast. Pick any of them from the scenario menu at the top; the
        catalogue below describes each one. These are the questions I have been trying to answer.
      </p>
      <ol class="questions">
        <li v-for="(x, i) in QUESTIONS" :key="i">
          <p class="q">{{ x.q }}</p>
          <p class="a">
            {{ x.a }}
            <RouterLink class="where" :to="{ path: x.path, query: $route.query }">{{ x.label }}</RouterLink>
          </p>
        </li>
      </ol>
      <p class="text-p">
        I do not have the answers. I have a set of mechanisms, stated in the open, that anyone can
        inspect, argue with and improve. If this helps one family have a calmer and
        better-informed conversation about the future, or one policymaker ask a sharper question,
        it has done its job. If you can make it better, the
        <a :href="REPO_URL" target="_blank" rel="noopener">repository</a> is open and I would be
        glad of the help. <span class="muted">Saro Saravanan, September 2026.</span>
      </p>
    </section>

    <section class="card author" id="author">
      <h3>About the author</h3>
      <p class="text-p">
        <a :href="AUTHOR.profile" target="_blank" rel="noopener author"><strong>{{ AUTHOR.name }}</strong></a>
        is a CTO, builder and AI-native engineering leader with decades of experience building,
        scaling and operating software: founder-CTO of Emplanet, a 401(k) SaaS platform that raised
        $36M and exited at a $100M valuation; Chief Architect at Fidelity Investments for
        NetBenefits (10M+ users), Plan Sponsor WebStation and twenty other flagship products;
        engineering leader and inventor behind TSA PreCheck and TSA CAT at IDEMIA; holder of seven
        U.S. patents in identity, biometrics and web application architecture; co-author of two
        books on operating system internals. Today he practises technology due diligence at
        Crosslake Technologies, increasingly on AI disruption risk and AI readiness, and runs
        Verby, LLC, an AI product studio that has shipped five products since 2024. This
        simulation is one of those builds.
      </p>
      <p class="text-p">
        <strong>Fractional CTO and advisory.</strong> Saro is open to fractional CTO engagements,
        board and technical advisory roles, and technology due diligence: AI-readiness reviews
        across infrastructure, architecture, organisation and operations, disruption-risk
        assessment for software businesses, and hands-on help building real AI capability rather
        than an AI veneer. If the questions this model raises are ones your company is facing, that
        is the conversation to have.
      </p>
      <ul class="plain links">
        <li><a :href="AUTHOR.profile" target="_blank" rel="noopener">Profile page</a><span class="muted"> · experience, builds, patents and publications</span></li>
        <li><a :href="AUTHOR.linkedin" target="_blank" rel="noopener">LinkedIn</a><span class="muted"> · connect or send a message</span></li>
        <li><a :href="AUTHOR.github" target="_blank" rel="noopener">GitHub</a><span class="muted"> · code, including this repository</span></li>
      </ul>
    </section>

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
      <h3>What kind of model this is</h3>
      <p class="text-p">
        The model is a structured scenario model: a set of mechanisms with stated parameters,
        run across parameter draws and mechanism cells, whose bands are the range of its own
        assumptions rather than a forecast interval. Three tools keep it honest. The
        <RouterLink :to="{ path: '/backtest', query: $route.query }">Backtest</RouterLink> view
        scores the central run against what has been observed since 2024 (firm adoption, AI-cited
        job cuts, AI industry revenue, hyperscaler capex) and marks the rows that were used to set
        a parameter as calibration targets rather than evidence; a convergence test reports how
        the 10th, 50th and 90th percentiles move with the draw count and the seed; and a regional
        decomposition runs the United States alone (the <code>config-us-closed</code> scenario)
        beside the ten-region configuration to show how much of the headline comes from the
        regional layer. The structural ensemble has a closure axis, <code>demand</code> versus
        <code>no_demand_feedback</code>, so the named futures on the Story view are the medians of
        the cells under each closure, and the jobs beat reports the spread of the mechanism cells
        alone. The one-page
        <a :href="CURRENT_MODEL_URL" target="_blank" rel="noopener">current-model statement</a>
        lists the fitted parameters and their targets.
      </p>
    </section>

    <section class="card">
      <h3>The story, your outlook and the scoreboard</h3>
      <p class="text-p">
        The <RouterLink :to="{ path: '/story', query: $route.query }">Story</RouterLink> view
        reads the current run as one reconciled set of numbers and seven findings in plain
        language, each with the range of the model's assumptions, how sure the model is of the
        direction, and what
        would change it; it ends with the policy runs read against the baseline and an executive
        brief without parameter codes. Named futures sit beside the model's own extremes: the
        Seba / RethinkX disruption preset is one of them and can be opened as a scenario.
        <RouterLink :to="{ path: '/outlook', query: $route.query }">Your outlook</RouterLink>
        narrows the same run to one occupation and one age band. The forecast scoreboard on the
        Story view puts named public claims (Goldman Sachs, IMF, Acemoglu, RethinkX and others)
        next to the run's central value and the range of its assumptions and says whether the model
        lands within, below or above each claim; where the model tracks only a neighbouring
        quantity, the row says so, and claims that were used to set a parameter are marked as
        calibration targets and counted separately.
      </p>
    </section>

    <section class="card" id="scenarios">
      <h3>Scenarios and presets</h3>
      <p class="text-p">
        The scenario picker in the top bar lists these runs. A scenario is a JSON file of lever
        values and shocks on top of a parent; the baseline is the parent of nearly all of them, so
        every other run reads as “the baseline with these things changed”. The What if panel opens
        any of them as a starting point.
      </p>
      <p v-if="!scenarioGroups.length" class="muted small">No scenarios loaded yet.</p>
      <div v-for="g in scenarioGroups" :key="g.label" class="group">
        <h4 class="sub">{{ g.label }}</h4>
        <p class="muted small note">{{ g.note }}</p>
        <ul class="plain scen">
          <li v-for="s in g.items" :key="s.id">
            <div class="scen-name">
              <button
                class="linkish"
                :class="{ current: s.id === results.scenarioId }"
                :title="s.id === results.scenarioId ? 'The current run' : `Open ${s.name}`"
                @click="openScenario(s.id)"
              >
                {{ s.name }}
              </button>
              <span v-if="s.id === results.scenarioId" class="muted small">current run</span>
              <span v-if="s.parent && s.parent !== 'baseline'" class="muted small">on {{ s.parent }}</span>
            </div>
            <div v-if="s.description" class="text small">{{ s.description }}</div>
          </li>
        </ul>
      </div>
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

    <section class="card" id="static-demo">
      <h3>Static demo, mock and the local API</h3>
      <p class="text-p">
        <template v-if="mode === 'static'">
          This page is the <strong>static demo</strong>: the runs were computed once by a GitHub
          Actions workflow and exported as files, and the app reads them with no server behind it.
          Switching scenario, region and quarter, the compare view, the story and both briefs all
          work from those files. Three things need the local API and are switched off here: running
          new lever values from the What if panel, saving a scenario, and the Ask tab.
        </template>
        <template v-else-if="mode === 'mock'">
          This page runs on <strong>mock data</strong>: synthetic S-curves from the web build, not
          a model run. It exists to develop the views without the engine.
        </template>
        <template v-else>
          This page is served by the <strong>local API</strong>: scenarios run on demand (cached by
          their hash), lever changes and saved scenarios work, and the Ask tab appears when the
          server has a model key.
        </template>
        To run the model yourself, clone the repository and run
        <code>make demo</code>; the README explains the data build, the API and the web app. The
        public page is rebuilt from <code>main</code> on every push.
      </p>
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
.group + .group {
  margin-top: 8px;
}
ol.questions {
  margin: 12px 0;
  padding-left: 22px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
ol.questions .q {
  margin: 0 0 2px;
  font-weight: 600;
}
ol.questions .a {
  margin: 0;
  color: var(--ink-2);
}
ol.questions .where {
  color: var(--accent-ink);
  font-size: 14px;
  white-space: nowrap;
}
.text-p + .text-p {
  margin-top: 10px;
}
.note {
  margin: 0 0 4px;
}
ul.scen li {
  line-height: 1.45;
  margin-bottom: 4px;
}
.scen-name {
  display: flex;
  gap: 8px;
  align-items: baseline;
  flex-wrap: wrap;
}
ul.scen .text.small {
  font-size: 14px;
  color: var(--ink-2);
  margin: 0;
}
.linkish {
  border: 0;
  background: none;
  padding: 0;
  font: inherit;
  font-weight: 600;
  color: var(--accent-ink);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.linkish.current {
  color: var(--ink);
  text-decoration: none;
  cursor: default;
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
