<script setup lang="ts">
import type { StoryInvestment } from '@/types/story'
import type { Mode } from '@/lib/palette'
import StoryBars from '@/components/story/StoryBars.vue'
import { fmtBn } from '@/lib/format'

/** "Investment versus returns": the capex going in against what AI producers earn and what the economy gains. */
defineProps<{ investment: StoryInvestment; mode: Mode }>()
const bn = (v: number | null | undefined) => (v == null ? 'n/a' : fmtBn(v))
</script>

<template>
  <div class="investment">
    <p v-for="(p, i) in investment.paragraphs" :key="i" class="para">{{ p }}</p>
    <StoryBars
      :chart="investment.chart"
      :format="(v: number) => fmtBn(v)"
      :mode="mode"
      :title="investment.chart.title ?? 'Investment versus returns'"
      :axis-format="(v: number) => fmtBn(v)"
    />
    <div class="table-wrap">
      <table class="data">
        <thead>
          <tr>
            <th scope="col">Year</th>
            <th scope="col" class="num">Capex</th>
            <th scope="col" class="num">AI producers' revenue</th>
            <th scope="col" class="num">Productivity gain</th>
            <th scope="col" class="num">GDP effect</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in investment.rows" :key="r.year">
            <td>{{ r.year }}</td>
            <td class="num">
              {{ bn(r.capex_observed_bn ?? r.capex_model_bn)
              }}<span v-if="r.capex_observed_bn" class="muted"> reported</span>
            </td>
            <td class="num">{{ bn(r.producer_revenue_bn) }}</td>
            <td class="num">{{ bn(r.productivity_gain_bn) }}</td>
            <td class="num">{{ bn(r.gdp_gain_bn) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="definition muted">{{ investment.definition }}</p>
  </div>
</template>

<style scoped>
.investment {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.para {
  margin: 0;
  line-height: 1.5;
}
.table-wrap {
  overflow-x: auto;
}
.definition {
  font-size: 13px;
  margin: 0;
}
</style>
