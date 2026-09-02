<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useResultsStore } from '@/stores/results'
import { STATIC_RUN_MESSAGE, STATIC_SAVE_MESSAGE } from '@/api/client'
import type { LeverDef, ScenarioDocument } from '@/types/results'
import {
  LEVER_GROUP_LABELS,
  LEVER_GROUP_ORDER,
  buildChildScenario,
  clampLever,
  deepMerge,
  fmtLeverValue,
  leverDiff,
  leverValues,
  type LeverValues,
} from '@/lib/levers'

const props = defineProps<{
  open: boolean
  /** a child scenario to pre-fill the form with (Phase 4: a chat proposal's Edit button) */
  preset?: ScenarioDocument | null
}>()
const emit = defineEmits<{ close: [] }>()
const results = useResultsStore()

const values = ref<LeverValues>({})
const name = ref('')
const busy = ref(false)
const openGroups = ref<Record<string, boolean>>({ capability: true })

const parentValues = computed(() => leverValues(results.levers, results.scenarioDoc))
const groups = computed(() => {
  const present = new Set(results.levers.map((l) => l.group))
  const ordered = [...LEVER_GROUP_ORDER.filter((g) => present.has(g)), ...[...present].filter((g) => !(LEVER_GROUP_ORDER as readonly string[]).includes(g))]
  return ordered.map((g) => ({ key: g, label: LEVER_GROUP_LABELS[g] ?? g, levers: results.levers.filter((l) => l.group === g) }))
})
const diff = computed(() => leverDiff(results.levers, parentValues.value, values.value))
const changedByGroup = computed(() => {
  const m = new Map<string, number>()
  for (const d of diff.value) {
    const g = results.levers.find((l) => l.path === d.path)?.group ?? ''
    m.set(g, (m.get(g) ?? 0) + 1)
  }
  return m
})
const parentName = computed(() => results.scenarioDoc?.name ?? results.scenarioName)

function reset() {
  const p = props.preset
  if (p) {
    // the preset's levers are a patch over its parent; lay them over the current scenario's values
    const base = results.scenarioDoc
    const merged: ScenarioDocument = base
      ? { ...base, levers: deepMerge(base.levers ?? {}, p.levers ?? {}) }
      : p
    values.value = leverValues(results.levers, merged)
    name.value = p.name
    return
  }
  values.value = { ...parentValues.value }
  name.value = `${parentName.value} · what-if`
}
watch(
  () => [props.open, results.scenarioDoc, results.levers, props.preset] as const,
  ([open]) => {
    if (open) results.loadLevers()
    reset()
  },
  { immediate: true },
)

function setNumber(l: LeverDef, raw: string) {
  values.value = { ...values.value, [l.path]: clampLever(l, Number(raw)) }
}
function setValue(l: LeverDef, v: string | boolean) {
  values.value = { ...values.value, [l.path]: v }
}
function revert(path: string) {
  values.value = { ...values.value, [path]: parentValues.value[path]! }
}
function child() {
  const parent = results.scenarioDoc
  if (!parent) return null
  return buildChildScenario(name.value.trim() || `${parent.name} · what-if`, parent, diff.value)
}
async function run() {
  const c = child()
  if (!c || results.isStatic) return
  busy.value = true
  await results.runChild(c)
  busy.value = false
  emit('close')
}
async function save() {
  const c = child()
  if (!c || results.isStatic) return
  busy.value = true
  await results.saveScenario(c)
  busy.value = false
}
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}
</script>

<template>
  <transition name="drawer">
    <div v-if="open" class="drawer-wrap" @keydown="onKey">
      <div class="scrim" @click="$emit('close')"></div>
      <aside class="drawer card" role="dialog" aria-label="What if: scenario levers">
        <div class="head">
          <div>
            <h2>What if</h2>
            <p class="muted small">
              Levers of <strong>{{ parentName }}</strong>. Changed values run as a child scenario.
            </p>
          </div>
          <button class="btn" aria-label="Close" @click="$emit('close')">✕</button>
        </div>

        <label class="name">
          <span class="muted">Name</span>
          <input v-model="name" type="text" class="input" maxlength="120" />
        </label>

        <div class="groups">
          <p v-if="!results.levers.length" class="muted">Loading levers…</p>
          <details
            v-for="g in groups"
            :key="g.key"
            class="group"
            :open="openGroups[g.key] ?? false"
            @toggle="(e) => (openGroups[g.key] = (e.target as HTMLDetailsElement).open)"
          >
            <summary>
              <span>{{ g.label }}</span>
              <span v-if="changedByGroup.get(g.key)" class="badge changed"
                >{{ changedByGroup.get(g.key) }} changed</span
              >
              <span class="muted count">{{ g.levers.length }}</span>
            </summary>
            <div v-for="l in g.levers" :key="l.path" class="lever" :class="{ changed: diff.some((d) => d.path === l.path) }">
              <div class="lever-head">
                <label :for="'lv-' + l.path" class="lever-label">{{ l.label }}</label>
                <span v-if="l.param" class="muted param" :title="l.mechanism">{{ l.param }}</span>
              </div>
              <div v-if="l.type === 'number'" class="num-row">
                <input
                  :id="'lv-' + l.path"
                  type="range"
                  :min="l.min"
                  :max="l.max"
                  :step="l.step"
                  :value="values[l.path]"
                  :aria-label="l.label"
                  @input="setNumber(l, ($event.target as HTMLInputElement).value)"
                />
                <input
                  type="number"
                  class="input num"
                  :min="l.min"
                  :max="l.max"
                  :step="l.step"
                  :value="values[l.path]"
                  :aria-label="`${l.label} value`"
                  @change="setNumber(l, ($event.target as HTMLInputElement).value)"
                />
                <span class="unit muted">{{ l.unit }}</span>
              </div>
              <select
                v-else-if="l.type === 'enum'"
                :id="'lv-' + l.path"
                class="select"
                :value="values[l.path]"
                @change="setValue(l, ($event.target as HTMLSelectElement).value)"
              >
                <option v-for="o in l.options" :key="o" :value="o">{{ fmtLeverValue(o) }}</option>
              </select>
              <label v-else class="check">
                <input
                  :id="'lv-' + l.path"
                  type="checkbox"
                  :checked="values[l.path] === true"
                  @change="setValue(l, ($event.target as HTMLInputElement).checked)"
                />
                <span>{{ values[l.path] === true ? 'on' : 'off' }}</span>
              </label>
              <p v-if="l.mechanism" class="mech muted">{{ l.mechanism }}</p>
            </div>
          </details>
        </div>

        <div class="diff">
          <h3>Diff vs {{ parentName }} <span class="muted">({{ diff.length }})</span></h3>
          <p v-if="!diff.length" class="muted small">No changes yet. Move a lever to see it here.</p>
          <ul v-else>
            <li v-for="d in diff" :key="d.path">
              <code>{{ d.path.replace(/^levers\./, '') }}</code>
              <span class="mono">{{ fmtLeverValue(d.from) }} → <strong>{{ fmtLeverValue(d.to) }}</strong></span>
              <button class="btn tiny" :aria-label="`Revert ${d.path}`" @click="revert(d.path)">↺</button>
            </li>
          </ul>
        </div>

        <div class="actions">
          <button
            class="btn primary"
            :disabled="busy || !results.scenarioDoc || results.isStatic"
            :title="results.isStatic ? STATIC_RUN_MESSAGE : undefined"
            @click="run"
          >
            {{ busy ? 'Running…' : 'Run' }}
          </button>
          <button
            class="btn"
            :disabled="busy || !results.scenarioDoc || !diff.length || results.isStatic"
            :title="results.isStatic ? STATIC_SAVE_MESSAGE : undefined"
            @click="save"
          >
            Save
          </button>
          <button class="btn" :disabled="busy" @click="reset">Reset</button>
          <span v-if="results.isMock" class="muted small">mock: Run re-uses the parent's results</span>
          <p v-else-if="results.isStatic" class="muted small static-note" role="note">
            {{ STATIC_RUN_MESSAGE }}
          </p>
        </div>
      </aside>
    </div>
  </transition>
</template>

<style scoped>
.drawer-wrap {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: flex;
  justify-content: flex-end;
}
.scrim {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.25);
}
.drawer {
  position: relative;
  width: min(520px, 100vw);
  height: 100%;
  border-radius: 0;
  border-width: 0 0 0 1px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  overflow: auto;
  box-shadow: var(--shadow);
}
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity var(--t);
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.small {
  font-size: 14px;
  margin: 2px 0 0;
}
.name {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}
.name .input {
  flex: 1;
}
.input {
  border: 1px solid var(--border);
  background: var(--surface);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 14px;
  min-width: 0;
}
.input.num {
  width: 92px;
  font-variant-numeric: tabular-nums;
}
.groups {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.group {
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 0 10px;
}
.group summary {
  cursor: pointer;
  padding: 8px 0;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}
.group summary .count {
  margin-left: auto;
  font-weight: 400;
}
.badge.changed {
  background: var(--warn-bg);
  color: var(--warn-ink);
}
.lever {
  padding: 8px 0 10px;
  border-top: 1px solid var(--grid);
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
}
.lever.changed {
  box-shadow: inset 3px 0 0 var(--accent);
  padding-left: 8px;
}
.lever-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.lever-label {
  font-weight: 500;
}
.param {
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}
.num-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.num-row input[type='range'] {
  flex: 1;
  accent-color: var(--accent);
  margin: 0;
}
.unit {
  font-size: 13px;
  min-width: 40px;
}
.check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.mech {
  margin: 0;
  font-size: 13px;
}
.diff h3 {
  margin-bottom: 4px;
}
.diff ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
}
.diff li {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.diff code {
  font-size: 13px;
  background: var(--surface-2);
  padding: 1px 6px;
  border-radius: 4px;
}
.btn.tiny {
  padding: 2px 8px;
  margin-left: auto;
}
.actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 6px;
  border-top: 1px solid var(--border);
  position: sticky;
  bottom: 0;
  background: var(--surface);
  padding-bottom: 4px;
}
.btn.primary {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
.static-note {
  flex-basis: 100%;
  margin: 2px 0 0;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
