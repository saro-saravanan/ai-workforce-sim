import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

/** Tracks the pixel size of an element via ResizeObserver. */
export function useSize(el: Ref<HTMLElement | null>, fallback = { width: 640, height: 360 }) {
  const width = ref(fallback.width)
  const height = ref(fallback.height)
  let ro: ResizeObserver | null = null

  onMounted(() => {
    if (!el.value) return
    const measure = () => {
      const r = el.value?.getBoundingClientRect()
      if (r && r.width > 0) {
        width.value = r.width
        height.value = r.height
      }
    }
    measure()
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(measure)
      ro.observe(el.value)
    }
  })
  onBeforeUnmount(() => ro?.disconnect())
  return { width, height }
}
