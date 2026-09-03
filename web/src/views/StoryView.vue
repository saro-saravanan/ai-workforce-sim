<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { BarsChart, StoryBeat as Beat } from '@/types/story'
import { useResultsStore } from '@/stores/results'
import { useThemeStore } from '@/stores/theme'
import { useStory } from '@/composables/useStory'
import { useBriefs } from '@/composables/useBriefs'
import { regionName, structuralSpreadLine } from '@/lib/story'
import { pyFixed } from '@/lib/plain'
import { fmtCompact, quarterYear } from '@/lib/format'
import StoryBeat from '@/components/story/StoryBeat.vue'
import StoryFan from '@/components/story/StoryFan.vue'
import StoryBars from '@/components/story/StoryBars.vue'
import StoryTimeline from '@/components/story/StoryTimeline.vue'
import StoryRegions from '@/components/story/StoryRegions.vue'
import StoryFutures from '@/components/story/StoryFutures.vue'
import PolicyCards from '@/components/story/PolicyCards.vue'
import ForecastTable from '@/components/story/ForecastTable.vue'
import StoryInvestment from '@/components/story/StoryInvestment.vue'

const results = useResultsStore()
const theme = useThemeStore()
const { story, loading, error, region } = useStory()
const briefs = useBriefs()

const horizon = computed(() => {
  const h = story.value?.horizon
  return h ? `${quarterYear(h[0])}–${quarterYear(h[1])}` : ''
})
/** the static export stories the U.S.; say so when another region is selected */
const regionNote = computed(() =>
  story.value && story.value.region !== region.value
    ? `This story is for ${regionName(story.value.region)}; the ${regionName(region.value)} totals are on the other views.`
    : '',
)
/** bar values: counts of people (no unit) in compact form, everything else one decimal */
function barsFormat(chart: BarsChart) {
  return chart.unit ? (v: number) => pyFixed(v, 1) : (v: number) => fmtCompact(v)
}
function barsTitle(beat: Beat, chart: BarsChart) {
  return chart.unit ?? (beat.id === 'hiring' ? 'people' : 'value')
}
const glossary = computed(() => Object.entries(story.value?.glossary ?? {}))
/** the spread of the mechanism cells alone, under the first beat's range (contracts §29) */
const spreadLine = computed(() => structuralSpreadLine(story.value?.structural_spread))
const backtestHorizon = computed(() => {
  const h = story.value?.backtest?.horizon
  return h ? `${quarterYear(h[0])} to ${h[1].endsWith('Q2') ? 'mid-' : ''}${quarterYear(h[1])}` : ''
})

function openScenario(id: string) {
  if (id && id !== results.scenarioId) results.scenarioId = id
}
</script>

<template>
  <article class="story">
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="!story" class="muted loading">
      {{ loading ? 'Reading the story…' : 'No story for this run.' }}
    </p>
    <template v-else>
      <header class="head">
        <div class="titles">
          <h2>
            {{ results.scenarioName }}: what AI does to work in {{ regionName(story.region) }}
          </h2>
          <p class="lede">
            {{ horizon }} · every number is a difference from a world in which AI stopped improving
            in 2023, not a forecast of the level of jobs.
            <span v-if="loading" class="muted">Updating…</span>
          </p>
          <p v-if="regionNote" class="chart-note">{{ regionNote }}</p>
        </div>
        <div class="actions">
          <button
            class="btn"
            :disabled="briefs.busy.value"
            title="The story as a self-contained page"
            @click="briefs.openExecutive(story)"
          >
            Executive brief
          </button>
          <button
            class="btn"
            :disabled="briefs.busy.value"
            title="The technical brief, with the parameters and percentiles"
            @click="briefs.openTechnical()"
          >
            Technical brief
          </button>
          <RouterLink class="btn link" :to="{ path: '/outlook', query: $route.query }"
            >Your outlook</RouterLink
          >
        </div>
      </header>

      <section class="callout card" aria-labelledby="one-set">
        <h3 id="one-set">One set of numbers</h3>
        <p>{{ story.numbers.reconciliation }}</p>
      </section>

      <StoryBeat
        v-for="(b, i) in story.beats"
        :key="b.id"
        :beat="b"
        :index="i + 1"
        :range-note="i === 0 ? spreadLine : undefined"
      >
        <StoryFan v-if="b.chart.type === 'fan'" :chart="b.chart" />
        <StoryBars
          v-else-if="b.chart.type === 'bars'"
          :chart="b.chart"
          :format="barsFormat(b.chart)"
          :mode="theme.mode"
          :title="barsTitle(b, b.chart)"
          :axis-format="b.chart.unit ? undefined : (v) => fmtCompact(v)"
          :reference-label="b.chart.reference ? 'share of all jobs' : undefined"
        />
        <template v-else-if="b.chart.type === 'timeline'">
          <StoryTimeline :chart="b.chart" :mode="theme.mode" />
          <div v-if="b.occupations" class="occ-lists">
            <div v-for="(list, key) in b.occupations" :key="key" class="occ-list">
              <h4>
                {{
                  key === 'hit_first'
                    ? 'Hit first (by 2030)'
                    : key === 'hit_most'
                      ? 'Hit most (by 2040)'
                      : 'Growing (by 2040)'
                }}
              </h4>
              <ul>
                <li v-for="[title, v] in list" :key="title">
                  <span>{{ title }}</span>
                  <span class="mono muted">{{ v > 0 ? '+' : '' }}{{ pyFixed(v) }}%</span>
                </li>
              </ul>
            </div>
          </div>
        </template>
        <StoryRegions v-else-if="b.chart.type === 'regions'" :chart="b.chart" :mode="theme.mode" />
        <StoryFutures
          v-else-if="b.chart.type === 'futures'"
          :items="b.chart.items"
          :current-id="results.scenarioId"
          @open="openScenario"
        />
        <template v-if="b.extra_chart" #extra>
          <StoryBars
            :chart="b.extra_chart"
            :format="(v) => fmtCompact(v)"
            :mode="theme.mode"
            :title="b.extra_chart.title ?? ''"
            :axis-format="(v) => fmtCompact(v)"
          />
        </template>
      </StoryBeat>

      <section class="card block" aria-labelledby="policies-h">
        <h3 id="policies-h">What could be done</h3>
        <PolicyCards
          :policies="story.policies"
          :against="story.policies_against"
          :current-id="results.scenarioId"
          @open="openScenario"
        />
      </section>

      <section v-if="story.investment" class="card block" aria-labelledby="investment-h">
        <h3 id="investment-h">Investment versus returns</h3>
        <StoryInvestment :investment="story.investment" :mode="theme.mode" />
      </section>

      <section v-if="story.backtest" class="card block" aria-labelledby="backtest-h">
        <h3 id="backtest-h">How the model has done so far<template v-if="backtestHorizon"> ({{ backtestHorizon }})</template></h3>
        <ul class="plain backtest-sentences">
          <li v-for="(sentence, i) in story.backtest.sentences" :key="i">{{ sentence }}</li>
        </ul>
        <p class="muted backtest-link">
          A calibration target set a parameter, so the model's agreement with it is not evidence.
          <RouterLink :to="{ path: '/backtest', query: $route.query }"
            >Open the backtest view</RouterLink
          >
        </p>
      </section>

      <section class="card block" aria-labelledby="forecasts-h">
        <h3 id="forecasts-h">How the model compares with named forecasts</h3>
        <ForecastTable
          :forecasts="story.forecasts ?? []"
          :current-id="results.scenarioId"
          @preset="openScenario"
        />
      </section>

      <section class="card block" aria-labelledby="caveats-h">
        <h3 id="caveats-h">Read this with care</h3>
        <ul class="plain">
          <li v-for="(c, i) in story.caveats" :key="i">{{ c }}</li>
        </ul>
      </section>

      <section class="card block" aria-labelledby="glossary-h">
        <h3 id="glossary-h">Words used</h3>
        <dl class="glossary">
          <template v-for="[term, meaning] in glossary" :key="term">
            <dt>{{ term }}</dt>
            <dd>{{ meaning }}</dd>
          </template>
        </dl>
      </section>
    </template>
  </article>
</template>

<style scoped>
.story {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-bottom: 24px;
  min-width: 0;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
  flex-wrap: wrap;
}
.titles {
  min-width: 0;
  flex: 1 1 420px;
}
.head h2 {
  font-size: 22px;
  margin-bottom: 4px;
}
.lede {
  margin: 0;
  color: var(--ink-2);
  font-size: 15px;
}
.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.btn.link {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.callout {
  padding: 14px 18px;
  border-left: 4px solid var(--accent);
  background: var(--surface-2);
}
.callout h3 {
  font-size: 15px;
  margin-bottom: 6px;
}
.callout p {
  margin: 0;
  line-height: 1.55;
  max-width: 82ch;
}
.block {
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}
.block h3 {
  font-size: 17px;
}
.occ-lists {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px 18px;
  margin-top: 8px;
  font-size: 14px;
}
.occ-list h4 {
  margin: 0 0 4px;
  font-size: 13px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.occ-list ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.occ-list li {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}
ul.plain {
  margin: 0;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  line-height: 1.5;
}
.backtest-link {
  margin: 0;
  font-size: 14px;
}
.backtest-link a {
  color: var(--accent-ink);
}
.glossary {
  margin: 0;
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 6px 16px;
  font-size: 14px;
}
.glossary dt {
  font-weight: 600;
}
.glossary dd {
  margin: 0;
  color: var(--ink-2);
}
@media (max-width: 640px) {
  .glossary {
    grid-template-columns: 1fr;
  }
}
.error {
  background: var(--warn-bg);
  color: var(--warn-ink);
  padding: 8px 12px;
  border-radius: 6px;
}
.loading {
  padding: 40px;
  text-align: center;
}
</style>
