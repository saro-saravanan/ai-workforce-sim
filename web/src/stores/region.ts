import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { REGION_IDS, REGION_NAMES, isRegionId, type RegionId } from '@/types/results'
import type { UrlQuery } from '@/stores/scrubber'

/** `region=` in the URL: `world` (default) or a region id (contracts §14). */
export type RegionSelection = 'world' | RegionId

export const REGION_OPTIONS: Array<{ id: RegionSelection; label: string }> = [
  { id: 'world', label: 'World' },
  ...REGION_IDS.map((id) => ({ id, label: REGION_NAMES[id] })),
]

/**
 * The region every view reads, plus the map drill member (`member=` iso3 for an EU member or a
 * single-country region's country). Router-agnostic like the scrubber store: `useUrlSync()` wires it.
 */
export const useRegionStore = defineStore('region', () => {
  const region = ref<RegionSelection>('world')
  const member = ref<string | null>(null)

  const isWorld = computed(() => region.value === 'world')
  const label = computed(() =>
    region.value === 'world' ? 'World' : REGION_NAMES[region.value as RegionId],
  )
  /** the key into `series` (null for world, which is aggregated client-side) */
  const seriesKey = computed<RegionId | null>(() => (isWorld.value ? null : (region.value as RegionId)))

  function setRegion(id: string | null | undefined) {
    const next: RegionSelection = id && isRegionId(id) ? id : 'world'
    if (next !== region.value) member.value = null
    region.value = next
  }

  function selectMember(iso3: string | null) {
    member.value = iso3 && /^[A-Z]{3}$/.test(iso3) ? iso3 : null
  }

  function toQuery(): UrlQuery {
    return {
      region: region.value !== 'world' ? region.value : undefined,
      member: member.value ?? undefined,
    }
  }

  function applyQuery(query: UrlQuery) {
    region.value = query.region && isRegionId(query.region) ? query.region : 'world'
    member.value = query.member && /^[A-Z]{3}$/.test(query.member) ? query.member : null
  }

  return { region, member, isWorld, label, seriesKey, setRegion, selectMember, toQuery, applyQuery }
})
