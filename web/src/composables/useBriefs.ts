import { computed, ref } from 'vue'
import type { StoryDocument } from '@/types/story'
import * as api from '@/api/client'
import { briefHtml } from '@/lib/insights'
import { execBriefMarkdown } from '@/lib/story'
import { useResultsStore } from '@/stores/results'
import { useRegionStore } from '@/stores/region'
import { useToastStore } from '@/stores/toast'

function openBlob(html: string) {
  const url = URL.createObjectURL(new Blob([html], { type: 'text/html;charset=utf-8' }))
  window.open(url, '_blank')
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

/**
 * Opens the executive brief (contracts §26: the story as a page) and the technical brief
 * (contracts §16) in a new tab, from the server, the static export, or built client-side.
 */
export function useBriefs() {
  const results = useResultsStore()
  const regionStore = useRegionStore()
  const toast = useToastStore()
  const busy = ref(false)
  const region = computed(() => api.storyRegion(regionStore.region))
  const hash = computed(() => results.doc?.meta.scenario_hash ?? null)

  async function openExecutive(story: StoryDocument | null) {
    const doc = results.doc
    if (!doc) return
    const url = api.execBriefUrl(doc, region.value)
    if (url) {
      window.open(url, '_blank', 'noopener')
      return
    }
    if (!story) {
      toast.push('Executive brief: the story has not loaded yet.', 'warn')
      return
    }
    openBlob(briefHtml(execBriefMarkdown(story), `${results.scenarioName} — executive brief`))
  }

  async function openTechnical() {
    const h = hash.value
    if (!h) return
    const compareHash = results.docB?.meta.scenario_hash ?? null
    if (!api.USE_MOCK && !api.USE_STATIC) {
      window.open(api.briefUrl(h, 'html', region.value, compareHash), '_blank', 'noopener')
      return
    }
    busy.value = true
    try {
      const file = await api.staticBriefFile(h, 'html', region.value, compareHash)
      if (file) {
        window.open(file, '_blank', 'noopener')
        return
      }
      const md = await api.fetchBriefMarkdown(
        h,
        region.value,
        compareHash,
        results.doc,
        results.docB,
      )
      openBlob(briefHtml(md, `${results.scenarioName} — brief`))
    } catch (e) {
      toast.push(`Brief: ${(e as Error).message}`, 'warn')
    } finally {
      busy.value = false
    }
  }

  return { busy, region, openExecutive, openTechnical }
}
