<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTourStore } from '@/stores/tour'
import { useResultsStore } from '@/stores/results'

/**
 * The guided tour (stores/tour.ts): a spotlight on one element per step with a card beside it,
 * or a centred card for the steps without a target, plus the first-visit invitation.
 */
const tour = useTourStore()
const results = useResultsStore()
const route = useRoute()
const router = useRouter()

interface Box {
  top: number
  left: number
  width: number
  height: number
}
const box = ref<Box | null>(null)
const cardEl = ref<HTMLElement | null>(null)
const NARROW = 720
const narrow = ref(typeof window !== 'undefined' && window.innerWidth < NARROW)
let direction: 1 | -1 = 1
let raf = 0

function measure(): Box | null {
  const s = tour.step
  if (!s?.target) return null
  const el = document.querySelector<HTMLElement>(s.target)
  if (!el) return null
  const r = el.getBoundingClientRect()
  if (r.width < 4 || r.height < 4) return null
  return { top: r.top, left: r.left, width: r.width, height: r.height }
}

/** the spotlight follows the target; a target that is not on screen skips the step */
async function place() {
  const s = tour.step
  if (!s) {
    box.value = null
    return
  }
  if (s.route && route.path !== s.route) {
    await router.push({ path: s.route, query: route.query })
    await nextTick()
    await new Promise((r) => setTimeout(r, 250))
  }
  await nextTick()
  const b = s.target ? measure() : null
  if (s.target && !b) {
    tour.skipStep(direction)
    return
  }
  box.value = b
  if (b) {
    const el = document.querySelector<HTMLElement>(s.target!)
    el?.scrollIntoView?.({ block: 'nearest', inline: 'nearest' })
    box.value = measure()
  }
  await nextTick()
  cardEl.value?.focus()
}

function onNext() {
  direction = 1
  tour.next()
}
function onBack() {
  direction = -1
  tour.back()
}
function relayout() {
  cancelAnimationFrame(raf)
  raf = requestAnimationFrame(() => {
    narrow.value = window.innerWidth < NARROW
    if (tour.active && tour.step?.target) box.value = measure()
  })
}
function onKey(e: KeyboardEvent) {
  if (!tour.active) return
  if (e.key === 'Escape') tour.finish()
  else if (e.key === 'ArrowRight' || e.key === 'Enter') onNext()
  else if (e.key === 'ArrowLeft') onBack()
  else return
  e.preventDefault()
}

watch(
  () => [tour.active, tour.index] as const,
  () => void place(),
)
onMounted(() => {
  window.addEventListener('resize', relayout)
  window.addEventListener('scroll', relayout, true)
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', relayout)
  window.removeEventListener('scroll', relayout, true)
  window.removeEventListener('keydown', onKey)
  cancelAnimationFrame(raf)
})
/** invite once the first run is on screen */
watch(
  () => !!results.doc,
  (ready) => {
    if (ready) setTimeout(() => tour.maybeWelcome(), 900)
  },
  { immediate: true },
)

const PAD = 6
const spot = computed(() =>
  box.value
    ? {
        top: `${box.value.top - PAD}px`,
        left: `${box.value.left - PAD}px`,
        width: `${box.value.width + 2 * PAD}px`,
        height: `${box.value.height + 2 * PAD}px`,
      }
    : null,
)
/** the card sits below the spotlight when there is room, else above; on narrow screens it docks at the bottom */
const cardStyle = computed(() => {
  if (!box.value || narrow.value) return null
  const vw = window.innerWidth
  const vh = window.innerHeight
  const W = 340
  const below = box.value.top + box.value.height + PAD + 12
  const above = vh - box.value.top + PAD + 12
  const left = Math.max(12, Math.min(box.value.left, vw - W - 12))
  if (below + 200 < vh) return { top: `${below}px`, left: `${left}px`, width: `${W}px` }
  return { bottom: `${above}px`, left: `${left}px`, width: `${W}px` }
})
/** on narrow screens the card docks at the bottom, or at the top when the target sits in the lower half */
const position = computed(() => {
  if (!box.value) return 'centred'
  if (!narrow.value) return 'anchored'
  return box.value.top + box.value.height / 2 > window.innerHeight / 2 ? 'docked docked-top' : 'docked'
})
</script>

<template>
  <Teleport to="body">
    <div v-if="tour.welcome" class="tour-scrim" @click.self="tour.dismissWelcome()">
      <div class="tour-card welcome" role="dialog" aria-modal="true" aria-labelledby="tour-welcome-title" tabindex="-1">
        <h2 id="tour-welcome-title">New here?</h2>
        <p>
          A two-minute tour shows what the scenarios, regions, views and levers do, and how to
          read the ranges. You can restart it any time from the band at the top.
        </p>
        <div class="row">
          <button class="btn primary" type="button" autofocus @click="tour.start()">Take the tour</button>
          <button class="btn" type="button" @click="tour.dismissWelcome()">Not now</button>
        </div>
      </div>
    </div>

    <template v-if="tour.active && tour.step">
      <div class="tour-mask" :class="{ 'has-spot': !!spot }" aria-hidden="true">
        <div v-if="spot" class="spot" :style="spot"></div>
      </div>
      <div
        ref="cardEl"
        class="tour-card step"
        :class="position"
        :style="cardStyle ?? undefined"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="`tour-title-${tour.step.id}`"
        tabindex="-1"
      >
        <p class="muted count">{{ tour.index + 1 }} of {{ tour.count }}</p>
        <h2 :id="`tour-title-${tour.step.id}`">{{ tour.step.title }}</h2>
        <p>{{ tour.step.body }}</p>
        <div class="row">
          <button class="btn" type="button" :disabled="tour.index === 0" @click="onBack">Back</button>
          <button class="btn primary" type="button" @click="onNext">
            {{ tour.isLast ? 'Done' : 'Next' }}
          </button>
          <span class="spacer"></span>
          <button class="btn link" type="button" @click="tour.finish()">Skip</button>
        </div>
      </div>
    </template>
  </Teleport>
</template>

<style scoped>
.tour-scrim {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(0, 0, 0, 0.45);
  display: grid;
  place-items: center;
  padding: 16px;
}
.tour-mask {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(0, 0, 0, 0.45);
}
.tour-mask.has-spot {
  background: transparent;
}
.spot {
  position: fixed;
  border-radius: 8px;
  box-shadow:
    0 0 0 2px var(--accent),
    0 0 0 9999px rgba(0, 0, 0, 0.45);
  transition:
    top var(--t),
    left var(--t),
    width var(--t),
    height var(--t);
}
.tour-card {
  z-index: 201;
  background: var(--surface);
  color: var(--ink);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 14px 16px;
  font-size: 14px;
  line-height: 1.5;
  max-width: 360px;
  outline: none;
}
.tour-card.step {
  position: fixed;
}
.tour-card.step.centred {
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: min(360px, calc(100vw - 32px));
}
.tour-card.step.docked {
  left: 12px;
  right: 12px;
  bottom: 12px;
  max-width: none;
}
.tour-card.step.docked-top {
  bottom: auto;
  top: 12px;
}
.tour-card h2 {
  font-size: 16px;
  margin: 0 0 6px;
}
.tour-card p {
  margin: 0 0 10px;
}
.count {
  font-size: 12px;
  margin-bottom: 2px;
}
.row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.spacer {
  flex: 1;
}
.btn {
  font: inherit;
  font-size: 13px;
  padding: 5px 12px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--ink);
  cursor: pointer;
}
.btn.primary {
  background: var(--ink);
  color: var(--surface);
  border-color: var(--ink);
}
.btn.link {
  border: 0;
  background: none;
  color: var(--muted);
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
