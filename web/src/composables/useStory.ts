import { computed, ref, shallowRef, watch } from 'vue'
import type { StoryDocument } from '@/types/story'
import * as api from '@/api/client'
import { useResultsStore } from '@/stores/results'
import { useRegionStore } from '@/stores/region'

/** The story document (contracts §26) for the current run and region, refetched when either changes. */
export function useStory() {
  const results = useResultsStore()
  const regionStore = useRegionStore()
  const story = shallowRef<StoryDocument | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  /** the region the story is asked for (World reads the U.S.) */
  const region = computed(() => api.storyRegion(regionStore.region))
  let seq = 0

  watch(
    () => [results.doc, region.value] as const,
    async ([doc, r]) => {
      const my = ++seq
      if (!doc) {
        story.value = null
        return
      }
      loading.value = true
      error.value = null
      try {
        const st = await api.fetchStory(doc, r)
        if (my === seq) story.value = st
      } catch (e) {
        if (my === seq) {
          story.value = null
          error.value = (e as Error).message
        }
      } finally {
        if (my === seq) loading.value = false
      }
    },
    { immediate: true },
  )

  return { story, loading, error, region }
}
