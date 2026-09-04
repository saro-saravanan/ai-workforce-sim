import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

/** One stop of the guided tour: a spotlight on `target` (a CSS selector), or a centred card without one. */
export interface TourStep {
  id: string
  title: string
  body: string
  /** CSS selector of the element to spotlight; a step without one is a centred card */
  target?: string
  /** route to be on before the step shows */
  route?: string
}

/** The beginner's tour, in order. Steps whose target is not on screen (narrow layouts) are skipped. */
export const TOUR_STEPS: TourStep[] = [
  {
    id: 'welcome',
    title: 'What this is',
    body: 'AI Workforce Sim is a scenario model of what AI does to jobs, pay and the economy from 2024 to 2040 across ten regions. Every number is a difference from a world in which AI stopped improving in 2023. It is not a forecast of how many jobs there will be, and it is not advice. The About page says why it was built and which questions it tries to answer.',
  },
  {
    id: 'scenario',
    title: 'Pick a scenario',
    body: 'Baseline is the central case. Presets rebuild published reports with the same engine, policy runs add one policy each, and named futures are whole worldviews. The About page describes every one.',
    target: '[data-tour="scenario"]',
  },
  {
    id: 'region',
    title: 'Pick a region',
    body: 'World combines the ten regions; each region has its own story, charts and briefs. Outside the United States the occupation and age detail is still U.S. data, and the page says so.',
    target: '[data-tour="region"]',
  },
  {
    id: 'tabs',
    title: 'The views',
    body: 'Story is the plain-language summary. Your outlook narrows it to one occupation and age. Backtest checks the model against what has already happened. Map, Flows, Occupations, Cohorts, Economy and AI Supply are the detail behind the story.',
    target: '[data-tour="tabs"]',
  },
  {
    id: 'story',
    title: 'One set of numbers',
    body: 'The Story keeps two ledgers apart: positions that exist (jobs) and people whose job was affected. Each finding shows the range of the model’s assumptions, how sure the model is of the direction, and what would change it.',
    target: '[data-tour="story"]',
    route: '/story',
  },
  {
    id: 'scrubber',
    title: 'Move through time',
    body: 'Drag the slider or press play to step through the quarters; every view follows. The arrow keys and the space bar work too.',
    target: '[data-tour="scrubber"]',
  },
  {
    id: 'explain',
    title: 'Explain',
    body: 'Opens the panel that says which mechanisms drove the numbers on screen, generated from the model’s own trace with no free text from a language model. An Ask tab appears when a model is configured on the server.',
    target: '[data-tour="explain"]',
  },
  {
    id: 'whatif',
    title: 'What if',
    body: 'Move the levers (capability pace, adoption friction, layoff pace, policies and more) and run your own scenario. The public page serves precomputed runs; new lever values need the local API, which the About page explains.',
    target: '[data-tour="whatif"]',
  },
  {
    id: 'compare',
    title: 'Compare',
    body: 'Puts two scenarios side by side on the same draws, so the difference bands exclude the noise the runs share.',
    target: '[data-tour="compare"]',
  },
  {
    id: 'export',
    title: 'Export',
    body: 'The technical brief as a page or as Markdown. The executive brief, without parameter codes, is on the Story view.',
    target: '[data-tour="export"]',
  },
  {
    id: 'finish',
    title: 'Read it with care',
    body: 'Ranges are the model’s own assumptions, not forecast intervals, and nothing here is advice. The About page lists the data, the fixtures and the limits. The model is open source: bugs, data and ideas are welcome in the repository.',
  },
]

const SEEN_KEY = 'aiwsim.tour'

function markSeen() {
  try {
    localStorage.setItem(SEEN_KEY, '1')
  } catch {
    /* private mode or storage blocked: the welcome shows again next time */
  }
}

/** The guided tour for first-time readers (the band's "Take the tour" restarts it). */
export const useTourStore = defineStore('tour', () => {
  const active = ref(false)
  const index = ref(0)
  /** the first-visit invitation card */
  const welcome = ref(false)

  const step = computed<TourStep | null>(() => (active.value ? (TOUR_STEPS[index.value] ?? null) : null))
  const count = computed(() => TOUR_STEPS.length)
  const isLast = computed(() => index.value >= TOUR_STEPS.length - 1)

  function start() {
    welcome.value = false
    index.value = 0
    active.value = true
  }
  function next() {
    if (isLast.value) finish()
    else index.value += 1
  }
  function back() {
    if (index.value > 0) index.value -= 1
  }
  /** jump over a step whose target is not on screen, in the direction of travel */
  function skipStep(direction: 1 | -1) {
    if (direction > 0) next()
    else if (index.value > 0) back()
    else next()
  }
  function finish() {
    active.value = false
    markSeen()
  }
  /** show the invitation once per browser */
  function maybeWelcome() {
    try {
      if (localStorage.getItem(SEEN_KEY)) return false
    } catch {
      /* no storage: still invite */
    }
    welcome.value = true
    return true
  }
  function dismissWelcome() {
    welcome.value = false
    markSeen()
  }

  return { active, index, welcome, step, count, isLast, start, next, back, skipStep, finish, maybeWelcome, dismissWelcome }
})
