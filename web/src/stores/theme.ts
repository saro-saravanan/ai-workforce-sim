import { defineStore } from 'pinia'
import { computed, ref, watchEffect } from 'vue'
import type { Mode } from '@/lib/palette'

export type ThemePref = 'system' | 'light' | 'dark'
const KEY = 'aiwsim.theme'

function readPref(): ThemePref {
  try {
    const v = localStorage.getItem(KEY)
    if (v === 'light' || v === 'dark' || v === 'system') return v
  } catch {
    /* storage unavailable */
  }
  return 'system'
}

export const useThemeStore = defineStore('theme', () => {
  const pref = ref<ThemePref>(readPref())
  const systemDark = ref(false)

  if (typeof window !== 'undefined' && 'matchMedia' in window) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    systemDark.value = mq.matches
    mq.addEventListener?.('change', (e) => (systemDark.value = e.matches))
  }

  /** Resolved mode used by charts (they cannot read CSS media queries cheaply). */
  const mode = computed<Mode>(() =>
    pref.value === 'system' ? (systemDark.value ? 'dark' : 'light') : pref.value,
  )

  function setPref(p: ThemePref) {
    pref.value = p
    try {
      localStorage.setItem(KEY, p)
    } catch {
      /* ignore */
    }
  }

  function cycle() {
    const order: ThemePref[] = ['system', 'light', 'dark']
    setPref(order[(order.indexOf(pref.value) + 1) % order.length] ?? 'system')
  }

  watchEffect(() => {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    if (pref.value === 'system') root.removeAttribute('data-theme')
    else root.setAttribute('data-theme', pref.value)
  })

  return { pref, mode, setPref, cycle }
})
