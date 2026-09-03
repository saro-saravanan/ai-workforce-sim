<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  sankey as d3sankey,
  sankeyLinkHorizontal,
  sankeyJustify,
  type SankeyNode,
  type SankeyLink,
} from 'd3-sankey'
import type { FlowsSection } from '@/types/results'
import { useSize } from '@/composables/useSize'
import { useTooltip } from '@/composables/useTooltip'
import { fmtCompact, fmtShare } from '@/lib/format'
import { FLOW_DESTINATION_LABELS, flowDestinations } from '@/lib/metrics'
import { stackCategorical } from '@/lib/scales'
import { NEUTRAL, type Mode } from '@/lib/palette'
import ChartTooltip from '@/components/ChartTooltip.vue'

interface NodeExtra {
  id: string
  label: string
  side: 'origin' | 'destination'
  p50: number
  lo?: number
  hi?: number
  color: string
}
interface LinkExtra {
  lo?: number
  hi?: number
  color: string
}
type Node = SankeyNode<NodeExtra, LinkExtra>
type Link = SankeyLink<NodeExtra, LinkExtra>

const props = defineProps<{
  flows: FlowsSection
  q: number
  mode: Mode
  quarterLabel: string
}>()

const host = ref<HTMLElement | null>(null)
const { width, height } = useSize(host, { width: 900, height: 520 })
const { tip, show, move, hide } = useTooltip()
const m = { top: 12, right: 250, bottom: 24, left: 250 }
const hovered = ref<string | null>(null)

const originColor = computed(() =>
  stackCategorical(
    props.flows.origins.map((o) => o.major_group),
    props.mode,
  ),
)

/** The six v0.2 states plus `hours_cut_self` when the document carries it (Phase 6). */
const dests = computed(() => flowDestinations(props.flows))

/**
 * The contract publishes origin totals and destination totals (cumulative). Origin→destination
 * links are not published, so each link is origin × destination share (independence).
 */
const graph = computed(() => {
  const q = props.q
  const origins = props.flows.origins
  const destTotal = dests.value.reduce(
    (a, d) => a + (props.flows.destinations[d]?.p50[q] ?? 0),
    0,
  )
  const nodes: NodeExtra[] = [
    ...origins.map((o) => ({
      id: `o:${o.major_group}`,
      label: o.title,
      side: 'origin' as const,
      p50: o.jobs_lost_cum.p50[q] ?? 0,
      lo: o.jobs_lost_cum.p10?.[q],
      hi: o.jobs_lost_cum.p90?.[q],
      color: originColor.value(o.major_group),
    })),
    ...dests.value.map((d) => ({
      id: `d:${d}`,
      label: FLOW_DESTINATION_LABELS[d],
      side: 'destination' as const,
      p50: props.flows.destinations[d]?.p50[q] ?? 0,
      lo: props.flows.destinations[d]?.p10?.[q],
      hi: props.flows.destinations[d]?.p90?.[q],
      color: NEUTRAL[props.mode],
    })),
  ]
  const links: Array<{ source: string; target: string; value: number } & LinkExtra> = []
  for (const o of origins) {
    const ov = o.jobs_lost_cum.p50[q] ?? 0
    for (const d of dests.value) {
      const share = destTotal > 0 ? (props.flows.destinations[d]?.p50[q] ?? 0) / destTotal : 0
      const value = ov * share
      if (value <= 0) continue
      links.push({
        source: `o:${o.major_group}`,
        target: `d:${d}`,
        value,
        lo: o.jobs_lost_cum.p10 ? (o.jobs_lost_cum.p10[q] ?? 0) * share : undefined,
        hi: o.jobs_lost_cum.p90 ? (o.jobs_lost_cum.p90[q] ?? 0) * share : undefined,
        color: originColor.value(o.major_group),
      })
    }
  }
  return { nodes, links }
})

const layout = computed(() => {
  const w = Math.max(200, width.value - m.left - m.right)
  const h = Math.max(200, height.value - m.top - m.bottom)
  const gen = d3sankey<NodeExtra, LinkExtra>()
    .nodeId((d) => d.id)
    .nodeWidth(14)
    .nodePadding(14)
    .nodeAlign(sankeyJustify)
    .nodeSort(() => 0) // keep contract order (a stable comparator; the typings reject null)
    .extent([
      [m.left, m.top],
      [m.left + w, m.top + h],
    ])
  const empty = graph.value.links.length === 0
  if (empty) return { nodes: [] as Node[], links: [] as Link[] }
  const g = gen({
    nodes: graph.value.nodes.map((n) => ({ ...n })),
    links: graph.value.links.map((l) => ({ ...l })),
  })
  return { nodes: g.nodes as Node[], links: g.links as Link[] }
})
const linkPath = sankeyLinkHorizontal<NodeExtra, LinkExtra>()
const total = computed(() => graph.value.nodes.filter((n) => n.side === 'origin').reduce((a, n) => a + n.p50, 0))

function pos(e: PointerEvent) {
  const r = host.value?.getBoundingClientRect()
  return [e.clientX - (r?.left ?? 0), e.clientY - (r?.top ?? 0)] as const
}
function bandText(lo?: number, hi?: number) {
  return lo != null && hi != null ? `${fmtCompact(lo)} to ${fmtCompact(hi)}` : '—'
}
function onNode(e: PointerEvent, n: Node) {
  hovered.value = n.id
  const [x, y] = pos(e)
  show(x, y, n.label, [
    { label: n.side === 'origin' ? 'Jobs lost (cumulative)' : 'Workers (cumulative)', value: fmtCompact(n.p50), swatch: n.color, kind: 'rect' },
    { label: '10–90 band', value: bandText(n.lo, n.hi) },
    { label: 'Share of all displaced', value: total.value > 0 ? fmtShare(n.p50 / total.value, 1) : '—' },
  ])
}
function onLink(e: PointerEvent, l: Link) {
  const s = l.source as Node
  const t = l.target as Node
  hovered.value = `${s.id}>${t.id}`
  const [x, y] = pos(e)
  show(x, y, `${s.label} → ${t.label}`, [
    { label: 'Workers (cumulative)', value: fmtCompact(l.value), swatch: l.color, kind: 'rect' },
    { label: '10–90 band', value: bandText(l.lo, l.hi) },
    { label: 'Share of origin', value: s.p50 > 0 ? fmtShare(l.value / s.p50, 0) : '—' },
  ])
}
function onMove(e: PointerEvent) {
  const [x, y] = pos(e)
  move(x, y)
}
function onLeave() {
  hovered.value = null
  hide()
}
/** Long node labels ("Hours cut (self-employed and platform)", "Transportation & material moving") wrap onto two lines. */
function labelLines(label: string): string[] {
  if (label.length <= 24) return [label]
  const paren = label.indexOf(' (')
  const at = paren > 0 ? paren : label.lastIndexOf(' ', Math.ceil(label.length / 2) + 4)
  return at > 0 ? [label.slice(0, at), label.slice(at + 1)] : [label]
}
function isDim(id: string) {
  if (!hovered.value) return false
  if (hovered.value.includes('>')) return !hovered.value.split('>').includes(id)
  return hovered.value !== id
}
function linkDim(l: Link) {
  if (!hovered.value) return false
  const s = (l.source as Node).id
  const t = (l.target as Node).id
  if (hovered.value.includes('>')) return hovered.value !== `${s}>${t}`
  return hovered.value !== s && hovered.value !== t
}
</script>

<template>
  <div ref="host" class="sankey-host">
    <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" preserveAspectRatio="xMinYMin meet" class="rsvg" role="img" :aria-label="`Where displaced workers went, cumulative to ${quarterLabel}`">
      <g class="links">
        <path
          v-for="(l, i) in layout.links"
          :key="i"
          :d="linkPath(l) ?? ''"
          fill="none"
          :stroke="l.color"
          :stroke-width="Math.max(1, l.width ?? 1)"
          :stroke-opacity="linkDim(l) ? 0.12 : 0.42"
          class="link"
          @pointerenter="onLink($event, l)"
          @pointermove="onMove"
          @pointerleave="onLeave"
        />
      </g>
      <g class="nodes">
        <g
          v-for="n in layout.nodes"
          :key="n.id"
          :class="{ dim: isDim(n.id) }"
          @pointerenter="onNode($event, n)"
          @pointermove="onMove"
          @pointerleave="onLeave"
        >
          <rect
            :x="n.x0"
            :y="n.y0"
            :width="(n.x1 ?? 0) - (n.x0 ?? 0)"
            :height="Math.max(1, (n.y1 ?? 0) - (n.y0 ?? 0))"
            :fill="n.color"
            rx="2"
          />
          <text
            :x="n.side === 'origin' ? (n.x0 ?? 0) - 8 : (n.x1 ?? 0) + 8"
            :y="((n.y0 ?? 0) + (n.y1 ?? 0)) / 2 - (labelLines(n.label).length - 1) * 8"
            :text-anchor="n.side === 'origin' ? 'end' : 'start'"
            dominant-baseline="middle"
            class="node-label"
          >
            <template v-for="(line, li) in labelLines(n.label)" :key="li">
              <tspan
                :x="n.side === 'origin' ? (n.x0 ?? 0) - 8 : (n.x1 ?? 0) + 8"
                :dy="li === 0 ? 0 : 16"
                :class="{ sub: li > 0 }"
                >{{ line }}</tspan
              >
              <tspan v-if="li === 0" class="val">&#160;{{ fmtCompact(n.p50) }}</tspan>
            </template>
          </text>
        </g>
      </g>
      <text v-if="layout.nodes.length === 0" :x="m.left" :y="height - 2" class="axis-title" text-anchor="start">
        No displacement yet at {{ quarterLabel }}.
      </text>
    </svg>
    <ChartTooltip :tip="tip" :width="width" />
  </div>
</template>

<style scoped>
.sankey-host {
  position: relative;
  min-width: 0;
  overflow: hidden;
  width: 100%;
  height: 100%;
  min-height: 420px;
}
svg {
  display: block;
}
.link {
  transition: stroke-opacity var(--t);
  cursor: pointer;
}
.nodes g {
  transition: opacity var(--t);
  cursor: pointer;
}
.nodes g.dim {
  opacity: 0.45;
}
.node-label {
  fill: var(--ink);
  font-size: 14px;
}
.val {
  fill: var(--ink-2);
  font-variant-numeric: tabular-nums;
}
.sub {
  fill: var(--ink-2);
  font-size: 13px;
}
.rsvg {
  max-width: 100%;
  height: auto;
  display: block;
}
</style>
