<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { BacktestRow, BacktestSummary } from '@/types/results'
import { useResultsStore } from '@/stores/results'
import { useThemeStore } from '@/stores/theme'
import { fetchBacktest } from '@/api/client'
import { fmtCompact, quarterLabel, quarterYear } from '@/lib/format'
import { pyFixed, pySigned } from '@/lib/plain'
import BacktestChart from '@/components/story/BacktestChart.vue'

/**
 * The backtest (contracts §29): the model's central run against what has been observed since
 * 2024, one card per series with the error summary and a chart, then every observation as a
 * table. Rows that set a parameter are marked as calibration targets: their fit is not evidence.
 */
const results = useResultsStore()
const theme = useThemeStore()

const backtest = computed(() => fetchBacktest(results.doc))
const horizon = computed(() => {
  const h = backtest.value?.horizon
  return h
    ? `${quarterYear(h[0])} to ${h[1].endsWith('Q2') ? 'mid-' : ''}${quarterYear(h[1])}`
    : '2024 to mid-2026'
})

interface SeriesCard {
  id: string
  summary: BacktestSummary
  rows: BacktestRow[]
  unit: string
  tracked: boolean
}
const cards = computed<SeriesCard[]>(() => {
  const bt = backtest.value
  if (!bt) return []
  const summary = bt.summary ?? {}
  const rowsBy = new Map<string, BacktestRow[]>()
  for (const r of bt.rows) {
    const list = rowsBy.get(r.series_id) ?? []
    list.push(r)
    rowsBy.set(r.series_id, list)
  }
  // every series in the summary, in its order; series with rows but no summary come after
  const ids = [...Object.keys(summary), ...[...rowsBy.keys()].filter((id) => !(id in summary))]
  return ids.map((id) => {
    const rows = rowsBy.get(id) ?? []
    const sm: BacktestSummary = summary[id] ?? {
      label: rows[0]?.label ?? id,
      n: rows.filter((r) => r.error_pct != null).length,
      mape_pct: null,
      bias_pct: null,
      used_in_fit: rows.some((r) => isFit(r)),
    }
    return { id, summary: sm, rows, unit: rows[0]?.unit ?? '', tracked: sm.n > 0 }
  })
})
const allRows = computed(() =>
  [...(backtest.value?.rows ?? [])].sort(
    (a, b) => a.series_id.localeCompare(b.series_id) || a.quarter.localeCompare(b.quarter),
  ),
)

const MAPE_TITLE = 'mean absolute percentage error of the central run over the scored quarters'
const BIAS_TITLE = 'mean signed error: positive when the model runs above the observations'
const isFit = (r: BacktestRow) => r.used_in_fit === 1 || r.used_in_fit === true
/** counts of people in compact form, everything else with one decimal */
const fmtValue = (v: number | null | undefined) =>
  v == null || !Number.isFinite(v) ? '—' : Math.abs(v) >= 10_000 ? fmtCompact(v) : pyFixed(v, 1)
/** tick labels: no trailing ".0" */
const fmtAxis = (v: number) =>
  Math.abs(v) >= 10_000 ? fmtCompact(v) : String(Number(v.toFixed(1)))
const fmtErr = (v: number | null | undefined) =>
  v == null || !Number.isFinite(v) ? '—' : `${pySigned(v, 0)}%`
/** "off by 12% on average; runs 8% above the observations" */
function summaryLine(sm: BacktestSummary): string {
  if (!sm.n || sm.mape_pct == null) return sm.note ?? 'not tracked by the model'
  const bias =
    sm.bias_pct == null
      ? ''
      : `; runs ${pyFixed(Math.abs(sm.bias_pct), 0)}% ${sm.bias_pct > 0 ? 'above' : 'below'} the observations`
  return `off by ${pyFixed(sm.mape_pct, 0)}% on average over ${sm.n} observation${sm.n === 1 ? '' : 's'}${bias}`
}
</script>

<template>
  <article class="backtest">
    <header class="head">
      <h2>How the model has done against what has happened so far ({{ horizon }})</h2>
      <p class="lede">
        Every row is an observation and the central run's value at the same quarter. Rows marked
        <span class="chip target">calibration target</span> were used to set a parameter and are not
        evidence.
        <RouterLink :to="{ path: '/story', query: $route.query }">Back to the story</RouterLink>
      </p>
    </header>

    <p v-if="!backtest" class="muted empty">
      No backtest section in this run<span v-if="results.meta"> ({{ results.scenarioName }})</span>.
      Runs made with the Phase 9 engine carry one.
    </p>
    <template v-else>
      <div class="cards">
        <section
          v-for="c in cards"
          :key="c.id"
          class="card series"
          :class="{ context: !c.tracked }"
          :data-series="c.id"
        >
          <header class="series-head">
            <h3>{{ c.summary.label }}</h3>
            <span
              v-if="c.summary.used_in_fit"
              class="chip target"
              title="This series was used to set a parameter, so the model's agreement with it is not evidence"
              >calibration target</span
            >
          </header>
          <dl v-if="c.tracked" class="stats">
            <div>
              <dt :title="MAPE_TITLE">MAPE</dt>
              <dd class="mono">{{ pyFixed(c.summary.mape_pct ?? 0, 1) }}%</dd>
            </div>
            <div>
              <dt :title="BIAS_TITLE">Bias</dt>
              <dd class="mono">{{ fmtErr(c.summary.bias_pct) }}</dd>
            </div>
            <div>
              <dt>Observations</dt>
              <dd class="mono">{{ c.summary.n }}</dd>
            </div>
          </dl>
          <p class="summary" :class="{ muted: !c.tracked }">{{ summaryLine(c.summary) }}</p>
          <BacktestChart
            :rows="c.rows"
            :mode="theme.mode"
            :format="fmtValue"
            :axis-format="fmtAxis"
            :unit="c.unit"
          />
        </section>
      </div>

      <section class="card block" aria-labelledby="rows-h">
        <h3 id="rows-h">Every observation</h3>
        <div class="table-wrap">
          <table class="data rows">
            <thead>
              <tr>
                <th scope="col">Series</th>
                <th scope="col">Quarter</th>
                <th scope="col" class="num">Observed</th>
                <th scope="col" class="num">Model</th>
                <th scope="col" class="num">Error</th>
                <th scope="col">Source</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in allRows" :key="r.series_id + r.quarter" :class="{ fit: isFit(r) }">
                <td class="label">
                  {{ r.label
                  }}<span
                    v-if="isFit(r)"
                    class="chip target"
                    title="This observation was used to set a parameter, so the model's agreement with it is not evidence"
                    >target</span
                  >
                </td>
                <td class="mono">{{ quarterLabel(r.quarter) }}</td>
                <td class="num mono">
                  {{ fmtValue(r.value) }} <span class="muted unit">{{ r.unit }}</span>
                </td>
                <td class="num mono" :title="r.note || undefined">
                  {{ fmtValue(r.model_central) }}<span v-if="r.note" class="star">*</span>
                </td>
                <td class="num mono">{{ fmtErr(r.error_pct) }}</td>
                <td class="source" :title="r.source_tag">{{ r.source }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="muted note">
          * the model value carries a note (hover it); hover a source for how it was verified.
        </p>
      </section>

      <section v-if="backtest.notes?.length" class="card block" aria-labelledby="notes-h">
        <h3 id="notes-h">Read this with care</h3>
        <ul class="plain">
          <li v-for="(n, i) in backtest.notes" :key="i">{{ n }}</li>
        </ul>
      </section>
    </template>
  </article>
</template>

<style scoped>
.backtest {
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-bottom: 24px;
  min-width: 0;
}
.head h2 {
  font-size: 20px;
  margin-bottom: 4px;
}
.lede {
  margin: 0;
  color: var(--ink-2);
  font-size: 15px;
  max-width: 82ch;
}
.lede a {
  color: var(--accent-ink);
  margin-left: 6px;
}
.empty {
  padding: 40px;
  text-align: center;
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 12px;
}
.series {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.series.context {
  background: var(--surface-2);
}
.series-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}
.series h3 {
  font-size: 15px;
  margin: 0;
}
.stats {
  margin: 0;
  display: flex;
  gap: 18px;
  font-size: 14px;
}
.stats dt {
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  cursor: help;
}
.stats dd {
  margin: 0;
  font-weight: 600;
}
.summary {
  margin: 0;
  font-size: 14px;
  color: var(--ink-2);
}
.chip {
  display: inline-block;
  border-radius: 999px;
  border: 1px dashed var(--border);
  padding: 0 7px;
  font-size: 11px;
  font-weight: 500;
  color: var(--muted);
  vertical-align: 1px;
  cursor: help;
}
td .chip {
  margin-left: 6px;
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
.table-wrap {
  overflow-x: auto;
  max-width: 100%;
}
table.rows th {
  cursor: default;
  position: static;
}
table.rows td.label {
  white-space: normal;
  min-width: 200px;
  max-width: 320px;
}
table.rows td.source {
  white-space: normal;
  min-width: 220px;
  max-width: 360px;
  font-size: 13px;
  color: var(--ink-2);
  cursor: help;
}
tr.fit td {
  color: var(--ink-2);
}
.unit {
  font-size: 12px;
}
.star {
  color: var(--accent-ink);
  margin-left: 2px;
}
.note {
  margin: 0;
  font-size: 13px;
}
ul.plain {
  margin: 0;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  line-height: 1.5;
}
</style>
